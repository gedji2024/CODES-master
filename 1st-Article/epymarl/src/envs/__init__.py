from functools import partial
import pretrained
from smac.env import MultiAgentEnv, StarCraft2Env
import sys
import os
import gym
from gym import ObservationWrapper, spaces
from gym.envs import registry as gym_registry
from gym.spaces import flatdim
import numpy as np
from gym.wrappers import TimeLimit as GymTimeLimit

def env_fn(env, **kwargs) -> MultiAgentEnv:
    return env(**kwargs)


REGISTRY = {}
REGISTRY["sc2"] = partial(env_fn, env=StarCraft2Env)

if sys.platform == "linux":
    os.environ.setdefault(
        "SC2PATH", os.path.join(os.getcwd(), "3rdparty", "StarCraftII")
    )


class TimeLimit(GymTimeLimit):
    def __init__(self, env, max_episode_steps=None):
        super().__init__(env)
        # if max_episode_steps is None and self.env.spec is not None:
        #     max_episode_steps = env.spec.max_episode_steps
        if self.env.spec is not None:
            self.env.spec.max_episode_steps = max_episode_steps
        self._max_episode_steps = max_episode_steps
        self._elapsed_steps = None

    def step(self, action):
        assert (
            self._elapsed_steps is not None
        ), "Cannot call env.step() before calling reset()"
        observation, reward, done, info = self.env.step(action)
        self._elapsed_steps += 1
        if self._elapsed_steps >= self._max_episode_steps:
            info["TimeLimit.truncated"] = not all(done) \
                if type(done) is list \
                else not done
            done = len(observation) * [True]
        return observation, reward, done, info


class FlattenObservation(ObservationWrapper):
    r"""Observation wrapper that flattens the observation of individual agents."""

    def __init__(self, env):
        super(FlattenObservation, self).__init__(env)

        ma_spaces = []
        for sa_obs in env.observation_space:
            flatdim = spaces.flatdim(sa_obs)
            ma_spaces += [
                spaces.Box(
                    low=-float("inf"),
                    high=float("inf"),
                    shape=(flatdim,),
                    dtype=np.float32,
                )
            ]

        self.observation_space = spaces.Tuple(tuple(ma_spaces))

    def observation(self, observation):
        return tuple(
            [
                spaces.flatten(obs_space, obs)
                for obs_space, obs in zip(self.env.observation_space, observation)
            ]
        )
    


class _GymmaWrapper(MultiAgentEnv):
    def __init__(self, key, time_limit, pretrained_wrapper, seed, **kwargs):
        self.original_env = gym.make(f"{key}", **kwargs)
        # print(f"\n=====================================")
        # for attribute_name in dir(self.original_env.__dict__['env'].__dict__["network_throughput"]):
        #     attribute_value = getattr(self.original_env.__dict__['env'], attribute_name)
        #     # Check if the attribute is not callable (i.e., not a method)
        #     if not callable(attribute_value):
        #         try:
        #             print(f"{attribute_name}: {attribute_value}")
        #         except Exception as e:
        #             print(f"Error accessing {attribute_name}: {e}")
        # print(f"=====================================\n")
        # raise Exception("Stop here")
        self.episode_limit = time_limit
        self._env = TimeLimit(self.original_env, max_episode_steps=time_limit)
        self._env = FlattenObservation(self._env)
        
        if pretrained_wrapper:
            self._env = getattr(pretrained, pretrained_wrapper)(self._env)

        self.n_agents = self._env.n_agents
        self._obs = None
        self._info = None

        self.longest_action_space = max(self._env.action_space, key=lambda x: x.n)
        self.longest_observation_space = max(
            self._env.observation_space, key=lambda x: x.shape
        )
        # if os.getenv("ALGO_NAME") == "QMIX":
        #     seed = 738606919
        # elif os.getenv("ALGO_NAME") == "QTRAN":
        #     seed = 611004836
        self._seed = seed
        print("\n=====================================")
        print(f"Seed: {self._seed}")
        print("=====================================\n")
        self._env.seed(self._seed)

    def step(self, actions):
        """ Returns reward, terminated, info """
        actions = [int(a) for a in actions]
        self._obs, reward, done, self._info = self._env.step(actions)
        # Gym TimeLimit sets a flag in info when an episode terminates due to max_episode_steps.
        # EPyMARL uses this to decide whether a termination should bootstrap (episode_limit=True)
        # or be treated as a true terminal state.
        episode_limit = False
        try:
            if isinstance(self._info, dict) and self._info.get("TimeLimit.truncated", False):
                episode_limit = True
            # Fallback: infer from TimeLimit internals if present
            elif hasattr(self._env, "_elapsed_steps") and hasattr(self._env, "_max_episode_steps"):
                episode_limit = bool(done) and (self._env._elapsed_steps >= self._env._max_episode_steps)
        except Exception:
            episode_limit = False
        self._obs = [
            np.pad(
                o,
                (0, self.longest_observation_space.shape[0] - len(o)),
                "constant",
                constant_values=0,
            )
            for o in self._obs
        ]
        if type(reward) is list:
            reward = sum(reward)
        if type(done) is list:
            done = all(done)
        info = self._info if isinstance(self._info, dict) else {}
        info = dict(info)
        info["episode_limit"] = episode_limit
        return float(reward), bool(done), info

    def get_obs(self):
        """ Returns all agent observations in a list """
        return self._obs

    def get_obs_agent(self, agent_id):
        """ Returns observation for agent_id """
        raise self._obs[agent_id]

    def get_obs_size(self):
        """ Returns the shape of the observation """
        return flatdim(self.longest_observation_space)

    def get_state(self):
        return np.concatenate(self._obs, axis=0).astype(np.float32)

    def get_state_size(self):
        """ Returns the shape of the state"""
        if hasattr(self.original_env, 'state_size'):
            return self.original_env.state_size
        return self.n_agents * flatdim(self.longest_observation_space)

    def get_avail_actions(self):
        """Returns the available actions for all agents.
        
        If the underlying environment provides get_avail_actions (e.g., WSNRoutingEnv),
        use that for physically-constrained action masking. Otherwise fall back to
        the legacy behavior of marking all actions in the discrete space as valid.
        """
        # Try to get physically-constrained available actions from the unwrapped env
        unwrapped = getattr(self._env, "unwrapped", self._env)
        if hasattr(unwrapped, "get_avail_actions"):
            raw_avail = unwrapped.get_avail_actions()
            # Pad to longest_action_space if needed
            avail_actions = []
            for agent_id, agent_avail in enumerate(raw_avail):
                # Convert to list (works for lists, numpy arrays, tuples, etc.)
                valid = list(agent_avail)
                # Pad if the environment returns fewer actions than longest_action_space
                if len(valid) < self.longest_action_space.n:
                    valid = valid + [0] * (self.longest_action_space.n - len(valid))
                elif len(valid) > self.longest_action_space.n:
                    valid = valid[:self.longest_action_space.n]
                avail_actions.append(valid)
            return avail_actions
        
        # Fallback: all actions in action space are valid
        avail_actions = []
        for agent_id in range(self.n_agents):
            avail_agent = self.get_avail_agent_actions(agent_id)
            avail_actions.append(avail_agent)
        return avail_actions

    def get_avail_agent_actions(self, agent_id):
        """ Returns the available actions for agent_id """
        valid = flatdim(self._env.action_space[agent_id]) * [1]
        invalid = [0] * (self.longest_action_space.n - len(valid))
        return valid + invalid

    def get_total_actions(self):
        """ Returns the total number of actions an agent could ever take """
        # TODO: This is only suitable for a discrete 1 dimensional action space for each agent
        return flatdim(self.longest_action_space)

    def reset(self):
        """ Returns initial observations and states"""
        self._obs = self._env.reset()
               
        self._obs = [
            np.pad(
                o,
                (0, self.longest_observation_space.shape[0] - len(o)),
                "constant",
                constant_values=0,
            )
            for o in self._obs
        ]
        return self.get_obs(), self.get_state()

    def render(self):
        self._env.render()

    def close(self):
        self._env.close()

    def seed(self):
        return self._env.seed

    def save_replay(self):
        pass

    def get_stats(self):
        return {}


REGISTRY["gymma"] = partial(env_fn, env=_GymmaWrapper)
