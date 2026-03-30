"""Action selection strategies for multi-agent reinforcement learning.

In the WSN routing environment, each agent (sensor node) chooses which
neighbor to forward its packet to. The action space has n_actions entries
where action i means "transmit to node i". The last action (n_actions-1)
is always the base station (BS).

Important: Apple MPS (Metal Performance Shaders) has a known bug where
torch.max() returns index -1 when all values are -inf. Both selectors
below include a fix that detects negative indices and falls back to a
random valid action instead of crashing or selecting action 0 (which is
out of communication range for most agents).
"""
import torch as th
from torch.distributions import Categorical
from .epsilon_schedules import DecayThenFlatSchedule
REGISTRY = {}


class MultinomialActionSelector():
    """Samples actions from a masked policy distribution (used by policy-gradient methods)."""

    def __init__(self, args):
        self.args = args

        self.schedule = DecayThenFlatSchedule(args.epsilon_start, args.epsilon_finish, args.epsilon_anneal_time,
                                              decay="linear")
        self.epsilon = self.schedule.eval(0)
        self.test_greedy = getattr(args, "test_greedy", True)

    def select_action(self, agent_inputs, avail_actions, t_env, test_mode=False):
        masked_policies = agent_inputs.clone()
        masked_policies[avail_actions == 0.0] = 0.0

        self.epsilon = self.schedule.eval(t_env)

        if test_mode and self.test_greedy:
            picked_actions = masked_policies.max(dim=2)[1]
            # Fix MPS bug: max() can return -1; fall back to sampling
            invalid = (picked_actions < 0)
            if invalid.any():
                fallback = Categorical(masked_policies).sample().long()
                picked_actions[invalid] = fallback[invalid]
        else:
            picked_actions = Categorical(masked_policies).sample().long()

        return picked_actions


REGISTRY["multinomial"] = MultinomialActionSelector


class EpsilonGreedyActionSelector():
    """Epsilon-greedy over Q-values (used by QMIX and QTRAN).

    During training, with probability epsilon a random valid action is chosen;
    otherwise the action with the highest Q-value is selected. During evaluation,
    epsilon is set to evaluation_epsilon (near 0) for near-greedy behaviour.
    """

    def __init__(self, args):
        self.args = args

        self.schedule = DecayThenFlatSchedule(args.epsilon_start, args.epsilon_finish, args.epsilon_anneal_time,
                                              decay="linear")
        self.epsilon = self.schedule.eval(0)

    def select_action(self, agent_inputs, avail_actions, t_env, test_mode=False):

        # Assuming agent_inputs is a batch of Q-Values for each agent bav
        self.epsilon = self.schedule.eval(t_env)

        if test_mode:
            # Greedy action selection only
            self.epsilon = self.args.evaluation_epsilon

        # Safety: if any agent has NO available actions, give it the last action
        # (BS = transmit to base station) as fallback to prevent Categorical
        # from crashing on an all-zero distribution.
        safe_avail = avail_actions.float()
        no_valid = (safe_avail.sum(dim=2) == 0)  # (batch, agents)
        if no_valid.any():
            safe_avail = safe_avail.clone()
            last_action = safe_avail.shape[2] - 1  # BS action
            safe_avail[:, :, last_action][no_valid] = 1.0

        # mask actions that are excluded from selection
        masked_q_values = agent_inputs.clone()
        masked_q_values[safe_avail == 0.0] = -float("inf")  # should never be selected!

        random_numbers = th.rand_like(agent_inputs[:, :, 0])
        pick_random = (random_numbers < self.epsilon).long()
        random_actions = Categorical(safe_avail).sample().long()

        greedy_actions = masked_q_values.max(dim=2)[1]

        # Fix MPS bug: max() on all-inf tensors returns -1.
        # Replace invalid greedy actions with a random valid action instead of
        # blindly clamping to 0 (action 0 is out-of-range for 46/70 agents).
        invalid_greedy = (greedy_actions < 0)
        if invalid_greedy.any():
            greedy_actions[invalid_greedy] = random_actions[invalid_greedy]

        picked_actions = pick_random * random_actions + (1 - pick_random) * greedy_actions
        return picked_actions


REGISTRY["epsilon_greedy"] = EpsilonGreedyActionSelector


class SoftPoliciesSelector():

    def __init__(self, args):
        self.args = args

    def select_action(self, agent_inputs, avail_actions, t_env, test_mode=False):
        m = Categorical(agent_inputs)
        picked_actions = m.sample().long()
        return picked_actions


REGISTRY["soft_policies"] = SoftPoliciesSelector