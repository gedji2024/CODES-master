"""Single-environment episode runner for MARL training and evaluation.

Runs one episode at a time (batch_size_run=1). Each call to run() resets the
WSN routing environment, collects a full episode of transitions, records WSN
performance metrics (PDR, latency, energy, connectivity debug counters), and
saves them as .npy files under results/data/.

Wall-clock timing and peak RSS memory are also tracked for feasibility analysis.
psutil is sampled every 10 steps to minimise syscall overhead.
"""
import os
import time
try:
    import psutil  # For peak memory (RSS)
except Exception:  # graceful fallback if psutil isn't available
    psutil = None
from envs import REGISTRY as env_REGISTRY
from functools import partial
from components.episode_buffer import EpisodeBatch
import numpy as np
import gym_examples

from utils.paths import RESULTS_DATA_DIR
base_back_up_dir = RESULTS_DATA_DIR + os.sep

class EpisodeRunner:

    def __init__(self, args, logger):
        self.args = args
        self.logger = logger
        self.batch_size = self.args.batch_size_run
        assert self.batch_size == 1
        self.env = env_REGISTRY[self.args.env](**self.args.env_args)
        self.episode_limit = self.env.episode_limit
        self.t = 0

        self.t_env = 0

        self.train_returns = []
        self.test_returns = []
        self.train_stats = {}
        self.test_stats = {}

        # Log the first run
        self.log_train_stats_t = -1000000

        # Initialize lists to store returns and variances
        self.episode_returns = []
        self.episode_std_remaining_energy = []
        self.episode_total_consumption_energy = []
        self.episode_mean_remaining_energy = []
        self.episode_network_throughput = []
        self.episode_energy_efficiency = []
        self.episode_packet_delivery_ratio = []
        self.episode_network_lifetime = []
        self.episode_average_latency = []
        # Timing (wall-clock) per episode
        self.episode_wall_step_time_ms_mean = []
        self.episode_wall_step_time_ms_p95 = []
        self.episode_wall_step_time_ms_p99 = []
        self.episode_wall_episode_time_ms = []
        
        # Connectivity/routing debug metrics
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

    def get_env_info(self):
        return self.env.get_env_info()

    def save_replay(self):
        self.env.save_replay()

    def close_env(self):
        self.env.close()

    def reset(self):
        self.batch = self.new_batch()
        self.env.reset()
        self.t = 0

    def run(self, test_mode=False):
        self.reset()

        terminated = False
        episode_return = 0
        self.mac.init_hidden(batch_size=self.batch_size)

        # Timing & memory: wall-clock per step and peak RSS per episode
        _step_times = []
        _t_ep_start = time.perf_counter()
        _peak_rss = 0
        _proc = psutil.Process(os.getpid()) if psutil else None

        while not terminated:
            _t_step_start = time.perf_counter()

            pre_transition_data = {
                "state": [self.env.get_state()],
                "avail_actions": [self.env.get_avail_actions()],
                "obs": [self.env.get_obs()]
            }

            self.batch.update(pre_transition_data, ts=self.t)

            # Pass the entire batch of experiences up till now to the agents
            # Receive the actions for each agent at this timestep in a batch of size 1
            actions = self.mac.select_actions(self.batch, t_ep=self.t, t_env=self.t_env, test_mode=test_mode)
            reward, terminated, env_info = self.env.step(actions[0])
            if test_mode and self.args.render:
                self.env.render()
            episode_return += reward

            post_transition_data = {
                "actions": actions,
                "reward": [(reward,)],
                "terminated": [(terminated != env_info.get("episode_limit", False),)],
            }

            self.batch.update(post_transition_data, ts=self.t)

            self.t += 1

            # End-to-end step timing (agents + env + bookkeeping)
            _step_times.append(time.perf_counter() - _t_step_start)
            # Track peak memory (RSS) — sample every 10 steps to avoid syscall overhead
            if _proc and self.t % 10 == 0:
                try:
                    _rss = _proc.memory_info().rss
                    if _rss > _peak_rss:
                        _peak_rss = _rss
                except Exception:
                    pass

        last_data = {
            "state": [self.env.get_state()],
            "avail_actions": [self.env.get_avail_actions()],
            "obs": [self.env.get_obs()]
        }
        if test_mode and self.args.render:
            print(f"Episode return: {episode_return}")
        self.batch.update(last_data, ts=self.t)

        # Select actions in the last stored state
        actions = self.mac.select_actions(self.batch, t_ep=self.t, t_env=self.t_env, test_mode=test_mode)
        self.batch.update({"actions": actions}, ts=self.t)

        cur_stats = self.test_stats if test_mode else self.train_stats
        cur_returns = self.test_returns if test_mode else self.train_returns
        log_prefix = "test_" if test_mode else ""
        # Episode wall-clock stats
        _t_ep = time.perf_counter() - _t_ep_start
        if _step_times:
            _arr = np.asarray(_step_times, dtype=float)
            wall_step_time_ms_mean = float(_arr.mean() * 1000.0)
            wall_step_time_ms_p95 = float(np.percentile(_arr, 95) * 1000.0)
            wall_step_time_ms_p99 = float(np.percentile(_arr, 99) * 1000.0)
        else:
            wall_step_time_ms_mean = 0.0
            wall_step_time_ms_p95 = 0.0
            wall_step_time_ms_p99 = 0.0
        wall_episode_time_ms = float(_t_ep * 1000.0)
        peak_memory_mb = float((_peak_rss / (1024.0 * 1024.0)) if _peak_rss > 0 else 0.0)

        # Merge timing into env_info so it flows into stats/logging
        env_info.update({
            "wall_step_time_ms_mean": wall_step_time_ms_mean,
            "wall_step_time_ms_p95": wall_step_time_ms_p95,
            "wall_step_time_ms_p99": wall_step_time_ms_p99,
            "wall_episode_time_ms": wall_episode_time_ms,
            "peak_memory_mb": peak_memory_mb,
        })

        # Persist timing into per-episode arrays (for .npy saves)
        self.episode_wall_step_time_ms_mean.append(wall_step_time_ms_mean)
        # p95 & memory
        self.episode_wall_step_time_ms_p95.append(wall_step_time_ms_p95)
        self.episode_wall_step_time_ms_p99.append(wall_step_time_ms_p99)
        self.episode_wall_episode_time_ms.append(wall_episode_time_ms)
        if not hasattr(self, "episode_peak_memory_mb"):
            self.episode_peak_memory_mb = []
        self.episode_peak_memory_mb.append(peak_memory_mb)

        cur_stats.update({k: cur_stats.get(k, 0) + env_info.get(k, 0) for k in set(cur_stats) | set(env_info)})
        cur_stats["n_episodes"] = 1 + cur_stats.get("n_episodes", 0)
        cur_stats["ep_length"] = self.t + cur_stats.get("ep_length", 0)

        if not test_mode:
            self.t_env += self.t

        cur_returns.append(episode_return)

        # Save returns and variances
        self.episode_returns.append(episode_return)
        
        observations = self.env.get_obs()
        performances = self.env.original_env.__dict__['env'].__dict__
        self.episode_std_remaining_energy.append(np.std([o[0] for o in observations]))
        self.episode_total_consumption_energy.append(np.sum([o[1] for o in observations]))
        self.episode_mean_remaining_energy.append(np.mean([o[0] for o in observations]))
        self.episode_network_throughput.append(performances['network_throughput'])
        self.episode_energy_efficiency.append(performances['energy_efficiency'])
        self.episode_packet_delivery_ratio.append(performances['packet_delivery_ratio'])
        self.episode_network_lifetime.append(performances['network_lifetime'])
        self.episode_average_latency.append(performances['average_latency'])
        
        # Track connectivity/routing debug metrics
        self.episode_direct_to_bs_count.append(performances.get('direct_to_bs_count', 0))
        self.episode_relay_delivery_count.append(performances.get('relay_delivery_count', 0))
        self.episode_out_of_range_count.append(performances.get('out_of_range_count', 0))
        self.episode_tx_failures_count.append(performances.get('tx_failures_count', 0))
        self.episode_rx_failures_count.append(performances.get('rx_failures_count', 0))
        self.episode_avg_hops_per_delivered.append(performances.get('avg_hops_per_delivered_packet', float('nan')))

        # Get the version number of gym_examples
        version = gym_examples.__version__
        seed_tag = os.getenv('SEED_TAG', '')  # e.g. "_seed42" for multi-seed runs
        if not test_mode:
            algo_name = os.getenv('ALGO_NAME')
            if not algo_name:
                algo_name = self.args.config if hasattr(self.args, 'config') else "UNKNOWN"
                algo_name = algo_name.upper()
            metrics = {
                # Minimal, reviewer-focused metrics
                "mean_returns_" + algo_name: self.episode_returns,
                "std_remaining_energy_" + algo_name: self.episode_std_remaining_energy,
                "total_consumption_energy_" + algo_name: self.episode_total_consumption_energy,
                "network_throughput_" + algo_name: self.episode_network_throughput,
                "energy_efficiency_" + algo_name: self.episode_energy_efficiency,
                "packet_delivery_ratio_" + algo_name: self.episode_packet_delivery_ratio,
                "average_latency_" + algo_name: self.episode_average_latency,
                # Timing (feasibility)
                "wall_step_time_ms_mean_" + algo_name: self.episode_wall_step_time_ms_mean,
                "wall_step_time_ms_p95_" + algo_name: self.episode_wall_step_time_ms_p95,
                "wall_step_time_ms_p99_" + algo_name: self.episode_wall_step_time_ms_p99,
                "wall_episode_time_ms_" + algo_name: self.episode_wall_episode_time_ms,
                # Memory (feasibility)
                "peak_memory_mb_" + algo_name: self.episode_peak_memory_mb,
                # Connectivity/routing debug metrics
                "direct_to_bs_count_" + algo_name: self.episode_direct_to_bs_count,
                "relay_delivery_count_" + algo_name: self.episode_relay_delivery_count,
                "out_of_range_count_" + algo_name: self.episode_out_of_range_count,
                "tx_failures_count_" + algo_name: self.episode_tx_failures_count,
                "rx_failures_count_" + algo_name: self.episode_rx_failures_count,
                "avg_hops_per_delivered_" + algo_name: self.episode_avg_hops_per_delivered,
            }

            for metric_name, metric_value in metrics.items():
                np.save(f"{base_back_up_dir}{metric_name}{seed_tag}_{version}.npy", np.array(metric_value))
        if test_mode and (len(self.test_returns) == self.args.test_nepisode):
            print(f"test_mode: {test_mode}")
            print(f"len(self.test_returns): {len(self.test_returns)}")
            algo_name = os.getenv('ALGO_NAME')
            if not algo_name:
                algo_name = self.args.config if hasattr(self.args, 'config') else "UNKNOWN"
                algo_name = algo_name.upper()
            metrics = {
                # Minimal, reviewer-focused metrics (test)
                "mean_returns_" + algo_name: self.episode_returns,
                "std_remaining_energy_" + algo_name: self.episode_std_remaining_energy,
                "total_consumption_energy_" + algo_name: self.episode_total_consumption_energy,
                "network_throughput_" + algo_name: self.episode_network_throughput,
                "energy_efficiency_" + algo_name: self.episode_energy_efficiency,
                "packet_delivery_ratio_" + algo_name: self.episode_packet_delivery_ratio,
                "average_latency_" + algo_name: self.episode_average_latency,
                # Timing (feasibility)
                "wall_step_time_ms_mean_" + algo_name: self.episode_wall_step_time_ms_mean,
                "wall_step_time_ms_p95_" + algo_name: self.episode_wall_step_time_ms_p95,
                "wall_step_time_ms_p99_" + algo_name: self.episode_wall_step_time_ms_p99,
                "wall_episode_time_ms_" + algo_name: self.episode_wall_episode_time_ms,
                # Memory (feasibility)
                "peak_memory_mb_" + algo_name: self.episode_peak_memory_mb,
                # Connectivity/routing debug metrics (test)
                "direct_to_bs_count_" + algo_name: self.episode_direct_to_bs_count,
                "relay_delivery_count_" + algo_name: self.episode_relay_delivery_count,
                "out_of_range_count_" + algo_name: self.episode_out_of_range_count,
                "tx_failures_count_" + algo_name: self.episode_tx_failures_count,
                "rx_failures_count_" + algo_name: self.episode_rx_failures_count,
                "avg_hops_per_delivered_" + algo_name: self.episode_avg_hops_per_delivered,
            }

            for metric_name, metric_value in metrics.items():
                np.save(f"{base_back_up_dir}{metric_name}{seed_tag}_test_{version}.npy", np.array(metric_value))
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

        # Log mean network throughput and latency
        if prefix == "test_":
            mean_latency = np.mean(self.episode_average_latency)
            mean_network_throughput = np.mean(self.episode_network_throughput)
            mean_packet_delivery_ratio = np.mean(self.episode_packet_delivery_ratio)

            std_latency = np.std(self.episode_average_latency)
            std_network_throughput = np.std(self.episode_network_throughput)
            std_packet_delivery_ratio = np.std(self.episode_packet_delivery_ratio)

            mean_returns = np.mean(self.episode_returns)
            mean_std_remaining_energy = np.mean(self.episode_std_remaining_energy)
            mean_mean_remaining_energy = np.mean(self.episode_mean_remaining_energy)
            mean_total_consumption_energy = np.mean(self.episode_total_consumption_energy)
            mean_network_lifetime = np.mean(self.episode_network_lifetime)

            std_returns = np.std(self.episode_returns)          
            std_std_remaining_energy = np.std(self.episode_std_remaining_energy)  
            std_mean_remaining_energy = np.std(self.episode_mean_remaining_energy)            
            std_total_consumption_energy = np.std(self.episode_total_consumption_energy)            
            std_network_lifetime = np.std(self.episode_network_lifetime)

            self.logger.log_stat(prefix + "mean_network_throughput", mean_network_throughput, self.t_env)
            self.logger.log_stat(prefix + "mean_latency", mean_latency, self.t_env)
            self.logger.log_stat(prefix + "mean_packet_delivery_ratio", mean_packet_delivery_ratio, self.t_env)
            self.logger.log_stat(prefix + "mean_network_lifetime", mean_network_lifetime, self.t_env)

            self.logger.log_stat(prefix + "std_network_throughput", std_network_throughput, self.t_env)
            self.logger.log_stat(prefix + "std_latency", std_latency, self.t_env)
            self.logger.log_stat(prefix + "std_packet_delivery_ratio", std_packet_delivery_ratio, self.t_env)
            self.logger.log_stat(prefix + "std_network_lifetime", std_network_lifetime, self.t_env) 

            self.logger.log_stat(prefix + "mean_returns", mean_returns, self.t_env)
            self.logger.log_stat(prefix + "mean_std_remaining_energy", mean_std_remaining_energy, self.t_env)
            self.logger.log_stat(prefix + "mean_mean_remaining_energy", mean_mean_remaining_energy, self.t_env)
            self.logger.log_stat(prefix + "mean_total_consumption_energy", mean_total_consumption_energy, self.t_env)
            
            self.logger.log_stat(prefix + "std_returns", std_returns, self.t_env)
            self.logger.log_stat(prefix + "std_std_remaining_energy", std_std_remaining_energy, self.t_env)
            self.logger.log_stat(prefix + "std_mean_remaining_energy", std_mean_remaining_energy, self.t_env)
            self.logger.log_stat(prefix + "std_total_consumption_energy", std_total_consumption_energy, self.t_env)

            # Log connectivity/routing debug metrics
            mean_direct_to_bs = np.mean(self.episode_direct_to_bs_count)
            mean_relay_delivery = np.mean(self.episode_relay_delivery_count)
            mean_out_of_range = np.mean(self.episode_out_of_range_count)
            mean_tx_failures = np.mean(self.episode_tx_failures_count)
            mean_rx_failures = np.mean(self.episode_rx_failures_count)
            # Handle NaN in avg_hops (when no packets delivered)
            avg_hops_arr = np.array(self.episode_avg_hops_per_delivered)
            mean_avg_hops = np.nanmean(avg_hops_arr) if not np.all(np.isnan(avg_hops_arr)) else 0.0
            
            self.logger.log_stat(prefix + "mean_direct_to_bs_count", mean_direct_to_bs, self.t_env)
            self.logger.log_stat(prefix + "mean_relay_delivery_count", mean_relay_delivery, self.t_env)
            self.logger.log_stat(prefix + "mean_out_of_range_count", mean_out_of_range, self.t_env)
            self.logger.log_stat(prefix + "mean_tx_failures_count", mean_tx_failures, self.t_env)
            self.logger.log_stat(prefix + "mean_rx_failures_count", mean_rx_failures, self.t_env)
            self.logger.log_stat(prefix + "mean_avg_hops_per_delivered", mean_avg_hops, self.t_env)
            
            # Print connectivity summary for debugging
            total_deliveries = mean_direct_to_bs + mean_relay_delivery
            total_failures = mean_out_of_range + mean_tx_failures + mean_rx_failures
            print(f"\n[Connectivity Debug] Direct→BS: {mean_direct_to_bs:.1f}, Relay→BS: {mean_relay_delivery:.1f}, "
                  f"OutOfRange: {mean_out_of_range:.1f}, TxFail: {mean_tx_failures:.1f}, RxFail: {mean_rx_failures:.1f}, "
                  f"AvgHops: {mean_avg_hops:.2f}")
            if total_deliveries == 0:
                print(f"[WARNING] No packets delivered! Check action masking and network connectivity.")
