from gym.envs.registration import register

register(
     id="WSNRouting-v0",
     entry_point="gym_examples.envs:WSNRoutingEnv",
)

__version__ = "3.3.3"  # Restore MonotonicAttentionNetwork for relay rewards (ATTN_RELAY_SCALE=0.01, 7.7x delivery advantage)
