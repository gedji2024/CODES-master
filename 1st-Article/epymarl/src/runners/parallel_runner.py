"""Multi-environment parallel runner for MARL training and evaluation.

Spawns batch_size_run (default 4) child processes, each running an independent
WSN routing environment. Each call to run() collects one episode from ALL
environments simultaneously, providing ~2-3x wall-clock speedup over the
single-environment EpisodeRunner.

Architecture:
    Main process           Child processes (env_worker)
    ────────────           ─────────────────────────────
    MAC.select_actions() ─────> env.step(actions)
    <───── obs, reward, done ── env.get_obs/state
    ...repeat until all envs terminate...
    <───── get_metrics ──────── WSN performance dict

Communication uses multiprocessing.Pipe. Each child also supports a
"get_metrics" command that returns WSN-specific metrics (PDR, latency,
energy, connectivity counters) from the environment's internal state.

Based on SubprocVecEnv from OpenAI Baselines:
https://github.com/openai/baselines/blob/master/baselines/common/vec_env/subproc_vec_env.py
"""
import os
import time
try:
    import psutil
except Exception:
    psutil = None
from envs import REGISTRY as env_REGISTRY
from functools import partial
from components.episode_buffer import EpisodeBatch
from multiprocessing import Pipe, Process
import numpy as np
import torch as th
import gym_examples

from utils.paths import RESULTS_DATA_DIR
base_back_up_dir = RESULTS_DATA_DIR + os.sep


class ParallelRunner:

    def __init__(self, args, logger):
        self.args = args
        self.logger = logger
        self.batch_size = self.args.batch_size_run

        # Make subprocesses for the envs
        self.parent_conns, self.worker_conns = zip(*[Pipe() for _ in range(self.batch_size)])
        env_fn = env_REGISTRY[self.args.env]
        env_args = [self.args.env_args.copy() for _ in range(self.batch_size)]
        for i in range(self.batch_size):
            env_args[i]["seed"] += i

        self.ps = [Process(target=env_worker, args=(worker_conn, CloudpickleWrapper(partial(env_fn, **env_arg))))
                            for env_arg, worker_conn in zip(env_args, self.worker_conns)]

        for p in self.ps:
            p.daemon = True
            p.start()

        self.parent_conns[0].send(("get_env_info", None))
        self.env_info = self.parent_conns[0].recv()
        self.episode_limit = self.env_info["episode_limit"]

        self.t = 0

        self.t_env = 0

        self.train_returns = []
        self.test_returns = []
        self.train_stats = {}
        self.test_stats = {}

        self.log_train_stats_t = -100000

        # Per-episode metric lists (same as EpisodeRunner)
        self.episode_returns = []
        self.episode_std_remaining_energy = []
        self.episode_total_consumption_energy = []
        self.episode_mean_remaining_energy = []
        self.episode_network_throughput = []
        self.episode_energy_efficiency = []
        self.episode_packet_delivery_ratio = []
        self.episode_network_lifetime = []
        self.episode_average_latency = []
        self.episode_wall_step_time_ms_mean = []
        self.episode_wall_step_time_ms_p95 = []
        self.episode_wall_step_time_ms_p99 = []
        self.episode_wall_episode_time_ms = []
        self.episode_peak_memory_mb = []
        self.episode_direct_to_bs_count = []
        self.episode_relay_delivery_count = []
        self.episode_out_of_range_count = []
        self.episode_tx_failures_count = []
        self.episode_rx_failures_count = []
        self.episode_avg_hops_per_delivered = []

    def setup(self, scheme, groups, preprocess, mac):
        self.new_batch = partial(EpisodeBatch, scheme, groups, self.batch_size, self.episode_limit + 1,
                                 preprocess=preprocess, device=self.args.device)
        self.mac = mac
        self.scheme = scheme
        self.groups = groups
        self.preprocess = preprocess

    def get_env_info(self):
        return self.env_info

    def save_replay(self):
        self.parent_conns[0].send(("save_replay", None))

    def close_env(self):
        for parent_conn in self.parent_conns:
            parent_conn.send(("close", None))

    def reset(self):
        self.batch = self.new_batch()

        # Reset the envs
        for parent_conn in self.parent_conns:
            parent_conn.send(("reset", None))

        pre_transition_data = {
            "state": [],
            "avail_actions": [],
            "obs": []
        }
        # Get the obs, state and avail_actions back
        for parent_conn in self.parent_conns:
            data = parent_conn.recv()
            pre_transition_data["state"].append(data["state"])
            pre_transition_data["avail_actions"].append(data["avail_actions"])
            pre_transition_data["obs"].append(data["obs"])

        self.batch.update(pre_transition_data, ts=0)

        self.t = 0
        self.env_steps_this_run = 0

    def run(self, test_mode=False):
        self.reset()

        all_terminated = False
        episode_returns = [0 for _ in range(self.batch_size)]
        episode_lengths = [0 for _ in range(self.batch_size)]
        self.mac.init_hidden(batch_size=self.batch_size)
        terminated = [False for _ in range(self.batch_size)]
        envs_not_terminated = [b_idx for b_idx, termed in enumerate(terminated) if not termed]
        final_env_infos = []  # may store extra stats like battle won. this is filled in ORDER OF TERMINATION

        # Timing: measure total wall time for this (batched) episode run
        _t_ep_start = time.perf_counter()
        # Per-step times for p95/p99 (approximate: one measurement per batch step)
        _step_times = []

        while True:

            _t_step_start = time.perf_counter()

            # Pass the entire batch of experiences up till now to the agents
            # Receive the actions for each agent at this timestep in a batch for each un-terminated env
            actions = self.mac.select_actions(self.batch, t_ep=self.t, t_env=self.t_env, bs=envs_not_terminated, test_mode=test_mode)
            cpu_actions = actions.to("cpu").numpy()

            # Update the actions taken
            actions_chosen = {
                "actions": actions.unsqueeze(1)
            }
            self.batch.update(actions_chosen, bs=envs_not_terminated, ts=self.t, mark_filled=False)

            # Send actions to each env
            action_idx = 0
            for idx, parent_conn in enumerate(self.parent_conns):
                if idx in envs_not_terminated: # We produced actions for this env
                    if not terminated[idx]: # Only send the actions to the env if it hasn't terminated
                        parent_conn.send(("step", cpu_actions[action_idx]))
                    action_idx += 1 # actions is not a list over every env
                    if idx == 0 and test_mode and self.args.render:
                        parent_conn.send(("render", None))

            # Update envs_not_terminated
            envs_not_terminated = [b_idx for b_idx, termed in enumerate(terminated) if not termed]
            all_terminated = all(terminated)
            if all_terminated:
                break

            # Post step data we will insert for the current timestep
            post_transition_data = {
                "reward": [],
                "terminated": []
            }
            # Data for the next step we will insert in order to select an action
            pre_transition_data = {
                "state": [],
                "avail_actions": [],
                "obs": []
            }

            # Receive data back for each unterminated env
            for idx, parent_conn in enumerate(self.parent_conns):
                if not terminated[idx]:
                    data = parent_conn.recv()
                    # Remaining data for this current timestep
                    post_transition_data["reward"].append((data["reward"],))

                    episode_returns[idx] += data["reward"]
                    episode_lengths[idx] += 1
                    if not test_mode:
                        self.env_steps_this_run += 1

                    env_terminated = False
                    if data["terminated"]:
                        final_env_infos.append(data["info"])
                    if data["terminated"] and not data["info"].get("episode_limit", False):
                        env_terminated = True
                    terminated[idx] = data["terminated"]
                    post_transition_data["terminated"].append((env_terminated,))

                    # Data for the next timestep needed to select an action
                    pre_transition_data["state"].append(data["state"])
                    pre_transition_data["avail_actions"].append(data["avail_actions"])
                    pre_transition_data["obs"].append(data["obs"])

            # Add post_transiton data into the batch
            self.batch.update(post_transition_data, bs=envs_not_terminated, ts=self.t, mark_filled=False)

            # Move onto the next timestep
            self.t += 1

            # Add the pre-transition data
            self.batch.update(pre_transition_data, bs=envs_not_terminated, ts=self.t, mark_filled=True)

            _step_times.append(time.perf_counter() - _t_step_start)

        if not test_mode:
            self.t_env += self.env_steps_this_run

        # --- Collect per-episode WSN metrics from each child env ---
        for parent_conn in self.parent_conns:
            parent_conn.send(("get_metrics", None))

        env_metrics_list = []
        for parent_conn in self.parent_conns:
            env_metrics_list.append(parent_conn.recv())

        # Get stats back for each env
        for parent_conn in self.parent_conns:
            parent_conn.send(("get_stats",None))

        env_stats = []
        for parent_conn in self.parent_conns:
            env_stat = parent_conn.recv()
            env_stats.append(env_stat)

        cur_stats = self.test_stats if test_mode else self.train_stats
        cur_returns = self.test_returns if test_mode else self.train_returns
        log_prefix = "test_" if test_mode else ""
        infos = [cur_stats] + final_env_infos
        cur_stats.update({k: sum(d.get(k, 0) for d in infos) for k in set.union(*[set(d) for d in infos])})
        cur_stats["n_episodes"] = self.batch_size + cur_stats.get("n_episodes", 0)
        cur_stats["ep_length"] = sum(episode_lengths) + cur_stats.get("ep_length", 0)

        # Episode wall-clock stats (batched)
        _t_ep = time.perf_counter() - _t_ep_start
        wall_episode_time_ms = float(_t_ep * 1000.0)
        # Per-env episode time (approximate: total / batch_size)
        wall_episode_time_ms_per_env = wall_episode_time_ms / self.batch_size

        if _step_times:
            _arr = np.asarray(_step_times, dtype=float) * 1000.0
            wall_step_time_ms_mean = float(_arr.mean())
            wall_step_time_ms_p95 = float(np.percentile(_arr, 95))
            wall_step_time_ms_p99 = float(np.percentile(_arr, 99))
        else:
            wall_step_time_ms_mean = 0.0
            wall_step_time_ms_p95 = 0.0
            wall_step_time_ms_p99 = 0.0

        # Peak memory (sample once per run() call, not per step)
        peak_memory_mb = 0.0
        if psutil:
            try:
                peak_memory_mb = float(psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024.0))
            except Exception:
                pass

        # Add to stats so they get logged/averaged
        cur_stats["wall_episode_time_ms"] = cur_stats.get("wall_episode_time_ms", 0.0) + wall_episode_time_ms
        cur_stats["wall_step_time_ms_mean"] = cur_stats.get("wall_step_time_ms_mean", 0.0) + wall_step_time_ms_mean

        cur_returns.extend(episode_returns)

        # Append per-episode metrics for each env in the batch
        for b_idx in range(self.batch_size):
            self.episode_returns.append(episode_returns[b_idx])
            m = env_metrics_list[b_idx]
            self.episode_std_remaining_energy.append(m["std_remaining_energy"])
            self.episode_total_consumption_energy.append(m["total_consumption_energy"])
            self.episode_mean_remaining_energy.append(m["mean_remaining_energy"])
            self.episode_network_throughput.append(m["network_throughput"])
            self.episode_energy_efficiency.append(m["energy_efficiency"])
            self.episode_packet_delivery_ratio.append(m["packet_delivery_ratio"])
            self.episode_network_lifetime.append(m["network_lifetime"])
            self.episode_average_latency.append(m["average_latency"])
            self.episode_direct_to_bs_count.append(m.get("direct_to_bs_count", 0))
            self.episode_relay_delivery_count.append(m.get("relay_delivery_count", 0))
            self.episode_out_of_range_count.append(m.get("out_of_range_count", 0))
            self.episode_tx_failures_count.append(m.get("tx_failures_count", 0))
            self.episode_rx_failures_count.append(m.get("rx_failures_count", 0))
            self.episode_avg_hops_per_delivered.append(m.get("avg_hops_per_delivered_packet", float("nan")))
            # Timing: same for all envs in batch (shared wall time)
            self.episode_wall_step_time_ms_mean.append(wall_step_time_ms_mean)
            self.episode_wall_step_time_ms_p95.append(wall_step_time_ms_p95)
            self.episode_wall_step_time_ms_p99.append(wall_step_time_ms_p99)
            self.episode_wall_episode_time_ms.append(wall_episode_time_ms_per_env)
            self.episode_peak_memory_mb.append(peak_memory_mb)

        # Save .npy files
        version = gym_examples.__version__
        seed_tag = os.getenv('SEED_TAG', '')  # e.g. "_seed42" for multi-seed runs
        algo_name = os.getenv("ALGO_NAME")
        if algo_name:
            metrics = {
                "mean_returns_" + algo_name: self.episode_returns,
                "std_remaining_energy_" + algo_name: self.episode_std_remaining_energy,
                "total_consumption_energy_" + algo_name: self.episode_total_consumption_energy,
                "network_throughput_" + algo_name: self.episode_network_throughput,
                "energy_efficiency_" + algo_name: self.episode_energy_efficiency,
                "packet_delivery_ratio_" + algo_name: self.episode_packet_delivery_ratio,
                "average_latency_" + algo_name: self.episode_average_latency,
                "wall_step_time_ms_mean_" + algo_name: self.episode_wall_step_time_ms_mean,
                "wall_step_time_ms_p95_" + algo_name: self.episode_wall_step_time_ms_p95,
                "wall_step_time_ms_p99_" + algo_name: self.episode_wall_step_time_ms_p99,
                "wall_episode_time_ms_" + algo_name: self.episode_wall_episode_time_ms,
                "peak_memory_mb_" + algo_name: self.episode_peak_memory_mb,
                "direct_to_bs_count_" + algo_name: self.episode_direct_to_bs_count,
                "relay_delivery_count_" + algo_name: self.episode_relay_delivery_count,
                "out_of_range_count_" + algo_name: self.episode_out_of_range_count,
                "tx_failures_count_" + algo_name: self.episode_tx_failures_count,
                "rx_failures_count_" + algo_name: self.episode_rx_failures_count,
                "avg_hops_per_delivered_" + algo_name: self.episode_avg_hops_per_delivered,
            }
            suffix = "_test_" if test_mode else "_"
            os.makedirs(base_back_up_dir, exist_ok=True)
            for metric_name, metric_value in metrics.items():
                np.save(f"{base_back_up_dir}{metric_name}{seed_tag}{suffix}{version}.npy", np.array(metric_value))

        n_test_runs = max(1, self.args.test_nepisode // self.batch_size) * self.batch_size
        if test_mode and (len(self.test_returns) == n_test_runs):
            self._log(cur_returns, cur_stats, log_prefix)
        elif self.t_env - self.log_train_stats_t >= self.args.runner_log_interval:
            self._log(cur_returns, cur_stats, log_prefix)
            if hasattr(self.mac.action_selector, "epsilon"):
                self.logger.log_stat("epsilon", self.mac.action_selector.epsilon, self.t_env)
            self.log_train_stats_t = self.t_env

        return self.batch

    def _log(self, returns, stats, prefix):
        self.logger.log_stat(prefix + "return_mean", np.mean(returns), self.t_env)
        self.logger.log_stat(prefix + "return_std", np.std(returns), self.t_env)
        returns.clear()

        for k, v in stats.items():
            if k != "n_episodes":
                self.logger.log_stat(prefix + k + "_mean" , v/stats["n_episodes"], self.t_env)
        stats.clear()

        # Log connectivity debug summary (test mode)
        if prefix == "test_":
            mean_direct_to_bs = np.mean(self.episode_direct_to_bs_count)
            mean_relay_delivery = np.mean(self.episode_relay_delivery_count)
            mean_out_of_range = np.mean(self.episode_out_of_range_count)
            mean_tx_failures = np.mean(self.episode_tx_failures_count)
            mean_rx_failures = np.mean(self.episode_rx_failures_count)
            avg_hops_arr = np.array(self.episode_avg_hops_per_delivered)
            mean_avg_hops = np.nanmean(avg_hops_arr) if not np.all(np.isnan(avg_hops_arr)) else 0.0

            print(f"\n[Connectivity Debug] Direct→BS: {mean_direct_to_bs:.1f}, Relay→BS: {mean_relay_delivery:.1f}, "
                  f"OutOfRange: {mean_out_of_range:.1f}, TxFail: {mean_tx_failures:.1f}, RxFail: {mean_rx_failures:.1f}, "
                  f"AvgHops: {mean_avg_hops:.2f}")


def env_worker(remote, env_fn):
    # Make environment
    env = env_fn.x()
    while True:
        cmd, data = remote.recv()
        if cmd == "step":
            actions = data
            # Take a step in the environment
            reward, terminated, env_info = env.step(actions)
            # Return the observations, avail_actions and state to make the next action
            state = env.get_state()
            avail_actions = env.get_avail_actions()
            obs = env.get_obs()
            remote.send({
                # Data for the next timestep needed to pick an action
                "state": state,
                "avail_actions": avail_actions,
                "obs": obs,
                # Rest of the data for the current timestep
                "reward": reward,
                "terminated": terminated,
                "info": env_info
            })
        elif cmd == "reset":
            env.reset()
            remote.send({
                "state": env.get_state(),
                "avail_actions": env.get_avail_actions(),
                "obs": env.get_obs()
            })
        elif cmd == "close":
            env.close()
            remote.close()
            break
        elif cmd == "get_env_info":
            remote.send(env.get_env_info())
        elif cmd == "get_stats":
            remote.send(env.get_stats())
        elif cmd == "get_metrics":
            # Collect WSN-specific metrics from the env for .npy saving
            obs = env.get_obs()
            try:
                perf = env.original_env.__dict__['env'].__dict__
            except Exception:
                perf = {}
            remote.send({
                "std_remaining_energy": float(np.std([o[0] for o in obs])),
                "total_consumption_energy": float(np.sum([o[1] for o in obs])),
                "mean_remaining_energy": float(np.mean([o[0] for o in obs])),
                "network_throughput": perf.get("network_throughput", 0.0),
                "energy_efficiency": perf.get("energy_efficiency", 0.0),
                "packet_delivery_ratio": perf.get("packet_delivery_ratio", 0.0),
                "network_lifetime": perf.get("network_lifetime", 0.0),
                "average_latency": perf.get("average_latency", float("nan")),
                "direct_to_bs_count": perf.get("direct_to_bs_count", 0),
                "relay_delivery_count": perf.get("relay_delivery_count", 0),
                "out_of_range_count": perf.get("out_of_range_count", 0),
                "tx_failures_count": perf.get("tx_failures_count", 0),
                "rx_failures_count": perf.get("rx_failures_count", 0),
                "avg_hops_per_delivered_packet": perf.get("avg_hops_per_delivered_packet", float("nan")),
            })
        elif cmd == "render":
            env.render()
        elif cmd == "save_replay":
            env.save_replay()
        else:
            raise NotImplementedError


class CloudpickleWrapper():
    """
    Uses cloudpickle to serialize contents (otherwise multiprocessing tries to use pickle)
    """
    def __init__(self, x):
        self.x = x
    def __getstate__(self):
        import cloudpickle
        return cloudpickle.dumps(self.x)
    def __setstate__(self, ob):
        import pickle
        self.x = pickle.loads(ob)
