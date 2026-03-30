"""QTRAN Q-Learner: trains a transformed Q-value factorization network.

QTRAN decomposes the joint Q-value using a transformation that is less
restrictive than QMIX's monotonicity constraint. It learns three components:
    1. Per-agent Q_i networks (via the MAC)
    2. A joint Q-value network (joint_qs)
    3. A state-value network V(s)

The total loss combines three terms:
    - TD loss:   standard temporal difference on the joint Q-value
    - Opt loss:  ensures the factored Q equals the joint Q at the optimal actions
    - Nopt loss: ensures non-optimal actions have lower factored Q than joint Q

Non-strict mode (default): includes nan_to_num guards for MPS backend stability.
"""
import copy
from components.episode_buffer import EpisodeBatch
from modules.mixers.qtran import QTranBase
import torch as th
from torch.optim import RMSprop, Adam


class QLearner:
    def __init__(self, mac, scheme, logger, args):
        self.args = args
        self.mac = mac
        self.logger = logger

        self.params = list(mac.parameters())

        self.last_target_update_episode = 0

        self.mixer = None
        if args.mixer == "qtran_base":
            self.mixer = QTranBase(args)
        elif args.mixer == "qtran_alt":
            raise Exception("Not implemented here!")

        self.params += list(self.mixer.parameters())
        self.target_mixer = copy.deepcopy(self.mixer)

        self.optimiser = RMSprop(params=self.params, lr=args.lr, alpha=args.optim_alpha, eps=args.optim_eps)

        # a little wasteful to deepcopy (e.g. duplicates action selector), but should work for any MAC
        self.target_mac = copy.deepcopy(mac)

        self.log_stats_t = -self.args.learner_log_interval - 1

    def train(self, batch: EpisodeBatch, t_env: int, episode_num: int):
        strict = getattr(self.args, "strict_math", False)
        # Get the relevant quantities
        rewards = batch["reward"][:, :-1]
        actions = batch["actions"][:, :-1]
        terminated = batch["terminated"][:, :-1].float()
        mask = batch["filled"][:, :-1].float()
        mask[:, 1:] = mask[:, 1:] * (1 - terminated[:, :-1])
        avail_actions = batch["avail_actions"]

        # Calculate estimated Q-Values
        mac_out = []
        mac_hidden_states = []
        self.mac.init_hidden(batch.batch_size)
        for t in range(batch.max_seq_length):
            agent_outs = self.mac.forward(batch, t=t)
            mac_out.append(agent_outs)
            mac_hidden_states.append(self.mac.hidden_states)
        mac_out = th.stack(mac_out, dim=1)  # Concat over time
        mac_hidden_states = th.stack(mac_hidden_states, dim=1)
        mac_hidden_states = mac_hidden_states.reshape(batch.batch_size, self.args.n_agents, batch.max_seq_length, -1).transpose(1,2) #btav

        # Pick the Q-Values for the actions taken by each agent
        chosen_action_qvals = th.gather(mac_out[:, :-1], dim=3, index=actions).squeeze(3)  # Remove the last dim

        # Calculate the Q-Values necessary for the target
        target_mac_out = []
        target_mac_hidden_states = []
        self.target_mac.init_hidden(batch.batch_size)
        for t in range(batch.max_seq_length):
            target_agent_outs = self.target_mac.forward(batch, t=t)
            target_mac_out.append(target_agent_outs)
            target_mac_hidden_states.append(self.target_mac.hidden_states)

        # We don't need the first timesteps Q-Value estimate for calculating targets
        target_mac_out = th.stack(target_mac_out[:], dim=1)  # Concat across time
        target_mac_hidden_states = th.stack(target_mac_hidden_states, dim=1)
        target_mac_hidden_states = target_mac_hidden_states.reshape(batch.batch_size, self.args.n_agents, batch.max_seq_length, -1).transpose(1,2) #btav

        # Mask out unavailable actions and detect no-valid-action cases.
        # In non-strict mode use -inf to avoid inflating scales with large finite sentinels.
        if strict:
            target_mac_out[avail_actions[:, :] == 0] = -9999999  # original sentinel
            mac_out_maxs = mac_out.clone()
            mac_out_maxs[avail_actions == 0] = -9999999
        else:
            target_mac_out = target_mac_out.masked_fill(avail_actions[:, :] == 0, float('-inf'))
            mac_out_maxs = mac_out.clone().masked_fill(avail_actions == 0, float('-inf'))
        no_valid_any = (avail_actions.sum(dim=3) == 0)

        # Best joint action computed by target agents (argmax ignores -inf automatically)
        target_max_actions = target_mac_out.max(dim=3, keepdim=True)[1]
        # Best joint-action computed by regular agents
        max_actions_qvals, max_actions_current = mac_out_maxs[:, :].max(dim=3, keepdim=True)
        if not strict:
            # Sanitize non-finite max values (all-masked case yields -inf)
            max_actions_qvals = th.nan_to_num(max_actions_qvals, nan=0.0, posinf=0.0, neginf=0.0)
            if t_env - self.log_stats_t >= self.args.learner_log_interval:
                self.logger.log_stat("qtran_max_actions_qvals_min", max_actions_qvals.min().item(), t_env)
                self.logger.log_stat("qtran_max_actions_qvals_max", max_actions_qvals.max().item(), t_env)

        if self.args.mixer == "qtran_base":
            # -- TD Loss --
            # Joint-action Q-Value estimates
            joint_qs, vs = self.mixer(batch[:, :-1], mac_hidden_states[:,:-1])
            if not strict and t_env - self.log_stats_t >= self.args.learner_log_interval:
                self.logger.log_stat("qtran_joint_qs_min", joint_qs.min().item(), t_env)
                self.logger.log_stat("qtran_joint_qs_max", joint_qs.max().item(), t_env)

            # Need to argmax across the target agents' actions to compute target joint-action Q-Values
            if self.args.double_q:
                max_actions_current_ = th.zeros(size=(batch.batch_size, batch.max_seq_length, self.args.n_agents, self.args.n_actions), device=batch.device)
                max_actions_current_onehot = max_actions_current_.scatter(3, max_actions_current[:, :], 1)
                max_actions_onehot = max_actions_current_onehot
            else:
                max_actions = th.zeros(size=(batch.batch_size, batch.max_seq_length, self.args.n_agents, self.args.n_actions), device=batch.device)
                max_actions_onehot = max_actions.scatter(3, target_max_actions[:, :], 1)
            target_joint_qs, target_vs = self.target_mixer(batch[:, 1:], hidden_states=target_mac_hidden_states[:,1:], actions=max_actions_onehot[:,1:])
            if not strict and t_env - self.log_stats_t >= self.args.learner_log_interval:
                self.logger.log_stat("qtran_target_joint_qs_min", target_joint_qs.min().item(), t_env)
                self.logger.log_stat("qtran_target_joint_qs_max", target_joint_qs.max().item(), t_env)
            if not strict:
                # Zero targets for terminal steps and sanitize
                target_joint_qs = th.nan_to_num(target_joint_qs, nan=0.0, posinf=0.0, neginf=0.0)

            # Scale rewards to prevent explosive TD errors (delivery_bonus=100 → rewards up to ~2000)
            reward_scale = getattr(self.args, 'reward_scale', 0.01)
            scaled_rewards = rewards * reward_scale

            # Td loss targets
            if strict:
                td_targets = scaled_rewards.reshape(-1,1) + self.args.gamma * (1 - terminated.reshape(-1, 1)) * target_joint_qs
            else:
                safe_tjq = target_joint_qs.clone()
                safe_tjq = th.where(terminated.reshape(-1,1).bool(), th.zeros_like(safe_tjq), safe_tjq)
                td_targets = scaled_rewards.reshape(-1,1) + self.args.gamma * (1 - terminated.reshape(-1, 1)) * safe_tjq
            if not strict:
                joint_qs = th.nan_to_num(joint_qs, nan=0.0, posinf=0.0, neginf=0.0)
            td_error = (joint_qs - td_targets.detach())
            if not strict:
                td_error = th.nan_to_num(td_error, nan=0.0, posinf=0.0, neginf=0.0)
            masked_td_error = td_error * mask.reshape(-1, 1)
            # Huber loss (delta=10) to handle large rewards (delivery_bonus=100 → rewards up to ~1300)
            td_loss = th.nn.functional.smooth_l1_loss(
                masked_td_error, th.zeros_like(masked_td_error), reduction='sum', beta=10.0
            ) / mask.sum()
            # -- TD Loss --

            # -- Opt Loss --
            # Argmax across the current agents' actions
            if not self.args.double_q: # Already computed if we're doing double Q-Learning
                max_actions_current_ = th.zeros(size=(batch.batch_size, batch.max_seq_length, self.args.n_agents, self.args.n_actions), device=batch.device )
                max_actions_current_onehot = max_actions_current_.scatter(3, max_actions_current[:, :], 1)
            max_joint_qs, _ = self.mixer(batch[:, :-1], mac_hidden_states[:,:-1], actions=max_actions_current_onehot[:,:-1]) # Don't use the target network and target agent max actions as per author's email
            if not strict:
                max_joint_qs = th.nan_to_num(max_joint_qs, nan=0.0, posinf=0.0, neginf=0.0)

            # max_actions_qvals = th.gather(mac_out[:, :-1], dim=3, index=max_actions_current[:,:-1])
            opt_error = max_actions_qvals[:,:-1].sum(dim=2).reshape(-1, 1) - max_joint_qs.detach() + vs
            if not strict:
                if not th.isfinite(opt_error).all():
                    raise RuntimeError("QTRAN: Non-finite opt_error encountered (NaN/Inf)")
            masked_opt_error = opt_error * mask.reshape(-1, 1)
            opt_loss = th.nn.functional.smooth_l1_loss(
                masked_opt_error, th.zeros_like(masked_opt_error), reduction='sum', beta=10.0
            ) / mask.sum()
            # -- Opt Loss --

            # -- Nopt Loss --
            # target_joint_qs, _ = self.target_mixer(batch[:, :-1])
            nopt_values = chosen_action_qvals.sum(dim=2).reshape(-1, 1) - joint_qs.detach() + vs # Don't use target networks here either
            if not strict:
                nopt_values = th.nan_to_num(nopt_values, nan=0.0, posinf=0.0, neginf=0.0)
            nopt_error = nopt_values.clamp(max=0)
            masked_nopt_error = nopt_error * mask.reshape(-1, 1)
            nopt_loss = th.nn.functional.smooth_l1_loss(
                masked_nopt_error, th.zeros_like(masked_nopt_error), reduction='sum', beta=10.0
            ) / mask.sum()
            # -- Nopt loss --

        elif self.args.mixer == "qtran_alt":
            raise Exception("Not supported yet.")

        loss = td_loss + self.args.opt_loss * opt_loss + self.args.nopt_min_loss * nopt_loss

        # Optimise — with NaN protection to prevent weight corruption
        self.optimiser.zero_grad()
        if th.isnan(loss) or th.isinf(loss):
            if t_env - self.log_stats_t >= self.args.learner_log_interval:
                self.logger.log_stat("nan_skips", 1, t_env)
        else:
            loss.backward()
            has_nan_grad = any(
                p.grad is not None and th.isnan(p.grad).any()
                for p in self.params
            )
            if has_nan_grad:
                self.optimiser.zero_grad()
                if t_env - self.log_stats_t >= self.args.learner_log_interval:
                    self.logger.log_stat("nan_grad_skips", 1, t_env)
            else:
                grad_norm = th.nn.utils.clip_grad_norm_(self.params, self.args.grad_norm_clip)
                self.optimiser.step()

        if (episode_num - self.last_target_update_episode) / self.args.target_update_interval >= 1.0:
            self._update_targets()
            self.last_target_update_episode = episode_num

        if t_env - self.log_stats_t >= self.args.learner_log_interval:
            self.logger.log_stat("loss", float(loss.item()) if not (th.isnan(loss) or th.isinf(loss)) else 0.0, t_env)
            self.logger.log_stat("td_loss", float(td_loss.item()) if not (th.isnan(td_loss) or th.isinf(td_loss)) else 0.0, t_env)
            self.logger.log_stat("opt_loss", float(opt_loss.item()) if not (th.isnan(opt_loss) or th.isinf(opt_loss)) else 0.0, t_env)
            self.logger.log_stat("nopt_loss", float(nopt_loss.item()) if not (th.isnan(nopt_loss) or th.isinf(nopt_loss)) else 0.0, t_env)
            try:
                self.logger.log_stat("grad_norm", float(grad_norm.item()), t_env)
            except Exception:
                self.logger.log_stat("grad_norm", 0.0, t_env)
            if self.args.mixer == "qtran_base":
                mask_elems = mask.sum().item()
                self.logger.log_stat("td_error_abs", (masked_td_error.abs().sum().item()/mask_elems), t_env)
                self.logger.log_stat("td_targets", ((masked_td_error).sum().item()/mask_elems), t_env)
                self.logger.log_stat("td_chosen_qs", (joint_qs.sum().item()/mask_elems), t_env)
                self.logger.log_stat("v_mean", (vs.sum().item()/mask_elems), t_env)
                self.logger.log_stat("agent_indiv_qs", ((chosen_action_qvals * mask).sum().item()/(mask_elems * self.args.n_agents)), t_env)
            self.log_stats_t = t_env

    def _update_targets(self):
        self.target_mac.load_state(self.mac)
        if self.mixer is not None:
            self.target_mixer.load_state_dict(self.mixer.state_dict())

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
