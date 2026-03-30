"""QMIX Q-Learner: trains a value-factorized multi-agent Q-network.

QMIX factorizes the joint Q-value Q_tot as a monotonic combination of per-agent
Q-values Q_i via a hypernetwork-based mixing network. This allows decentralized
execution (each agent only needs its own Q_i) while training uses the richer
global state via the mixer.

Training uses Double Q-Learning with a target network that is hard-updated every
target_update_interval_or_tau episodes. The loss is standard TD error masked by
the episode's filled timesteps.

Non-strict mode (default): includes multiple nan_to_num guards to handle edge
cases from the MPS backend where max() over all-masked Q-values produces NaN/Inf.
"""
import copy
from components.episode_buffer import EpisodeBatch
from modules.mixers.vdn import VDNMixer
from modules.mixers.qmix import QMixer
import torch as th
from torch.optim import Adam
from components.standarize_stream import RunningMeanStd
import numpy as np


class QLearner:
    def __init__(self, mac, scheme, logger, args):
        self.args = args
        self.mac = mac
        self.logger = logger

        self.params = list(mac.parameters())
        self.last_target_update_episode = 0

        self.mixer = None
        if args.mixer is not None:
            if args.mixer == "vdn":
                self.mixer = VDNMixer()
            elif args.mixer == "qmix":
                self.mixer = QMixer(args)
            elif args.mixer == "grid":
                from modules.mixers.grid import GRIDMixer
                self.mixer = GRIDMixer(args)
            else:
                raise ValueError("Mixer {} not recognised.".format(args.mixer))
            self.params += list(self.mixer.parameters())
            self.target_mixer = copy.deepcopy(self.mixer)

        self.optimiser = Adam(params=self.params, lr=args.lr)

        # a little wasteful to deepcopy (e.g. duplicates action selector), but should work for any MAC
        self.target_mac = copy.deepcopy(mac)

        self.training_steps = 0
        self.last_target_update_step = 0
        self.log_stats_t = -self.args.learner_log_interval - 1

        device = "cuda" if args.use_cuda else ("mps" if getattr(args, 'use_mps', False) else "cpu")
        if self.args.standardise_returns:
            self.ret_ms = RunningMeanStd(shape=(self.args.n_agents,), device=device)
        if self.args.standardise_rewards:
            self.rew_ms = RunningMeanStd(shape=(1,), device=device)

    def train(self, batch: EpisodeBatch, t_env: int, episode_num: int):
        strict = getattr(self.args, "strict_math", False)
        # Get the relevant quantities
        rewards = batch["reward"][:, :-1]
        actions = batch["actions"][:, :-1]
        terminated = batch["terminated"][:, :-1].float()
        mask = batch["filled"][:, :-1].float()
        mask[:, 1:] = mask[:, 1:] * (1 - terminated[:, :-1])
        avail_actions = batch["avail_actions"]
        
        if self.args.standardise_rewards:
            self.rew_ms.update(rewards)
            rewards = (rewards - self.rew_ms.mean) / (th.sqrt(self.rew_ms.var) + 1e-10)

        # Calculate estimated Q-Values
        mac_out = []
        self.mac.init_hidden(batch.batch_size)
        for t in range(batch.max_seq_length):
            agent_outs = self.mac.forward(batch, t=t)
            mac_out.append(agent_outs)
        mac_out = th.stack(mac_out, dim=1)  # Concat over time
        # Pick the Q-Values for the actions taken by each agent
        chosen_action_qvals = th.gather(mac_out[:, :-1], dim=3, index=actions).squeeze(3)  # Remove the last dim

        # Calculate the Q-Values necessary for the target
        target_mac_out = []
        self.target_mac.init_hidden(batch.batch_size)
        for t in range(batch.max_seq_length):
            target_agent_outs = self.target_mac.forward(batch, t=t)
            target_mac_out.append(target_agent_outs)

        # We don't need the first timesteps Q-Value estimate for calculating targets
        target_mac_out = th.stack(target_mac_out[1:], dim=1)  # Concat across time

        # Mask out unavailable actions (next-step availability)
        target_mac_out[avail_actions[:, 1:] == 0] = -9999999
        # Guard: if for some timestep an agent has no valid actions at all, remember it
        no_valid_next = (avail_actions[:, 1:].sum(dim=3) == 0)

        # Max over target Q-Values
        if self.args.double_q:
            # Get actions that maximise live Q (for double q-learning)
            mac_out_detach = mac_out.clone().detach()
            mac_out_detach[avail_actions == 0] = -9999999
            cur_max_actions = mac_out_detach[:, 1:].max(dim=3, keepdim=True)[1]
            target_max_qvals = th.gather(target_mac_out, 3, cur_max_actions).squeeze(3)
            if not strict:
                # Replace non-finite values early to avoid NaN propagation
                target_max_qvals = th.nan_to_num(target_max_qvals, nan=0.0, posinf=0.0, neginf=0.0)
                # For agents/timesteps with no valid actions, force 0 target
                target_max_qvals[no_valid_next] = 0.0
        else:
            target_max_qvals = target_mac_out.max(dim=3)[0]
            if not strict:
                target_max_qvals = th.nan_to_num(target_max_qvals, nan=0.0, posinf=0.0, neginf=0.0)
                target_max_qvals[no_valid_next] = 0.0

        # Mix
        if self.mixer is not None:
            chosen_action_qvals = self.mixer(chosen_action_qvals, batch["state"][:, :-1])
            target_max_qvals = self.target_mixer(target_max_qvals, batch["state"][:, 1:])
            if not strict:
                # Sanitize post-mixing
                target_max_qvals = th.nan_to_num(target_max_qvals, nan=0.0, posinf=0.0, neginf=0.0)

        if self.args.standardise_returns:
            # Undo standardisation (ensure numerical stability)
            if strict:
                target_max_qvals = target_max_qvals * th.sqrt(self.ret_ms.var) + self.ret_ms.mean
            else:
                target_max_qvals = target_max_qvals * th.sqrt(self.ret_ms.var.clamp_min(1e-12)) + self.ret_ms.mean
                target_max_qvals = th.nan_to_num(target_max_qvals, nan=0.0, posinf=0.0, neginf=0.0)

        # Scale rewards to prevent explosive TD errors (delivery_bonus=100 → rewards up to ~2000)
        reward_scale = getattr(self.args, 'reward_scale', 0.01)
        scaled_rewards = rewards * reward_scale

        # Calculate 1-step Q-Learning targets
        if strict:
            targets = scaled_rewards + self.args.gamma * (1 - terminated) * target_max_qvals.detach()
        else:
            # Zero out next-state value for terminal transitions BEFORE multiplication to avoid 0*NaN = NaN
            safe_target_max = target_max_qvals.detach().clone()
            # Use where with broadcasting to avoid boolean indexing shape issues
            safe_target_max = th.where(terminated.bool(), th.zeros_like(safe_target_max), safe_target_max)
            safe_target_max = th.nan_to_num(safe_target_max, nan=0.0, posinf=0.0, neginf=0.0)
            targets = scaled_rewards + self.args.gamma * (1 - terminated) * safe_target_max

        if self.args.standardise_returns:
            self.ret_ms.update(targets)
            targets = (targets - self.ret_ms.mean) / (th.sqrt(self.ret_ms.var) + 1e-10)

        # Td-error
        if not strict:
            # Sanitize chosen_action_qvals too (MPS can produce NaN from mixer/gather)
            chosen_action_qvals = th.nan_to_num(chosen_action_qvals, nan=0.0, posinf=0.0, neginf=0.0)
        td_error = (chosen_action_qvals - targets.detach())
        if not strict:
            td_error = th.nan_to_num(td_error, nan=0.0, posinf=0.0, neginf=0.0)

        mask = mask.expand_as(td_error)

        # 0-out the targets that came from padded data
        masked_td_error = td_error * mask

        # Huber loss (delta=10) to handle large rewards (delivery_bonus=100 → rewards up to ~1300)
        # MSE with such rewards gives loss ~745k → NaN gradients on MPS
        loss = th.nn.functional.smooth_l1_loss(
            masked_td_error, th.zeros_like(masked_td_error), reduction='sum', beta=10.0
        ) / (mask.sum() + 1e-10)

        # Optimise — with NaN protection to prevent weight corruption
        self.optimiser.zero_grad()
        if th.isnan(loss) or th.isinf(loss):
            if t_env - self.log_stats_t >= self.args.learner_log_interval:
                self.logger.log_stat("nan_skips", 1, t_env)
            # Skip this update entirely — NaN loss would corrupt weights
        else:
            loss.backward()
            # Check for NaN gradients before stepping
            has_nan_grad = any(
                p.grad is not None and th.isnan(p.grad).any()
                for p in self.params
            )
            if has_nan_grad:
                self.optimiser.zero_grad()  # Discard NaN gradients
                if t_env - self.log_stats_t >= self.args.learner_log_interval:
                    self.logger.log_stat("nan_grad_skips", 1, t_env)
            else:
                grad_norm = th.nn.utils.clip_grad_norm_(self.params, self.args.grad_norm_clip)
                self.optimiser.step()

        self.training_steps += 1
        if self.args.target_update_interval_or_tau > 1 and (self.training_steps - self.last_target_update_step) / self.args.target_update_interval_or_tau >= 1.0:
            self._update_targets_hard()
            self.last_target_update_step = self.training_steps
        elif self.args.target_update_interval_or_tau <= 1.0:
            self._update_targets_soft(self.args.target_update_interval_or_tau)

        if t_env - self.log_stats_t >= self.args.learner_log_interval:
            self.logger.log_stat("loss", float(loss.item()) if not (th.isnan(loss) or th.isinf(loss)) else 0.0, t_env)
            try:
                self.logger.log_stat("grad_norm", float(grad_norm.item()), t_env)
            except Exception:
                self.logger.log_stat("grad_norm", 0.0, t_env)
            mask_elems = mask.sum().item()
            self.logger.log_stat("td_error_abs", (masked_td_error.abs().sum().item()/(mask_elems + 1e-10)), t_env)
            self.logger.log_stat("q_taken_mean", (chosen_action_qvals * mask).sum().item()/(mask_elems * self.args.n_agents + 1e-10), t_env)
            self.logger.log_stat("target_mean", (targets * mask).sum().item()/(mask_elems * self.args.n_agents + 1e-10), t_env)
            self.log_stats_t = t_env

    def _update_targets_hard(self):
        self.target_mac.load_state(self.mac)
        if self.mixer is not None:
            self.target_mixer.load_state_dict(self.mixer.state_dict())

    def _update_targets_soft(self, tau):
        for target_param, param in zip(self.target_mac.parameters(), self.mac.parameters()):
            target_param.data.copy_(target_param.data * (1.0 - tau) + param.data * tau)
        if self.mixer is not None:
            for target_param, param in zip(self.target_mixer.parameters(), self.mixer.parameters()):
                target_param.data.copy_(target_param.data * (1.0 - tau) + param.data * tau)

    def cuda(self):
        self.to_device("cuda")

    def to_device(self, device):
        """Move all networks to the specified device (cuda, mps, or cpu)."""
        self.mac.agent.to(device)
        self.target_mac.agent.to(device)
        if self.mixer is not None:
            self.mixer.to(device)
            self.target_mixer.to(device)

    def save_models(self, path):
        self.mac.save_models(path)
        if self.mixer is not None:
            th.save(self.mixer.state_dict(), "{}/mixer.th".format(path))
        th.save(self.optimiser.state_dict(), "{}/opt.th".format(path))

    def load_models(self, path):
        self.mac.load_models(path)
        # Not quite right but I don't want to save target networks
        self.target_mac.load_models(path)
        if self.mixer is not None:
            self.mixer.load_state_dict(th.load("{}/mixer.th".format(path), map_location=lambda storage, loc: storage))
        self.optimiser.load_state_dict(th.load("{}/opt.th".format(path), map_location=lambda storage, loc: storage))