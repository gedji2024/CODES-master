"""WSN Routing Environment with Monotonic Attention-based Reward Scalarization.

This module implements a Wireless Sensor Network routing environment for
multi-agent reinforcement learning. Key features:
- Multi-objective rewards (angle, energy, dispersion, packets)
- Monotonic Q·K Attention Network for reward scalarization
- Evolution Strategies for meta-learning the scalarization
- Compatible with QMIX/QTRAN learners from epymarl

Author: PhD Research Project
Date: 2026
"""

import os
from collections import OrderedDict

import gym
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from gym.spaces import Box, Dict, MultiDiscrete, Tuple

# Define the network parameters for the final reward function
input_dim = 4  # length of the individual rewards vector
output_dim = 1  # final reward

# Objective names for interpretability
OBJECTIVE_NAMES = ['angle', 'energy', 'dispersion', 'packets']

Eelec = 50e-9  # energy consumption per bit in joules
Eamp = 100e-12  # energy consumption per bit per square meter in joules
info_amount = 512  # data size in bits
initial_energy = 1  # initial energy of each sensor (in joules)
lower_bound = 0  # lower bound of the sensor positions
upper_bound = 100  # upper bound of the sensor positions
base_station_position = np.array([(upper_bound - lower_bound)/2, (upper_bound - lower_bound)/2]) # position of the base station
initial_number_of_packets = 1  # initial number of packets to transmit
latency_per_hop = 1  # latency per hop in seconds

# Coverage radius: 35% of field size for realistic WSN connectivity
# Literature standard: 4-6 neighbors per sensor on average
# At 35m in 100x100m field with 70 sensors: avg ~5 neighbors
DEFAULT_COVERAGE_RADIUS = (upper_bound - lower_bound) * 0.35

base_back_up_dir = "results/data/"
max_reward = 1 # maximum reward value when the sensors sent data to the base station. The opposite value is when the sensors perform an unauthorized action

# Scale factor for attention-based relay reward.
# MonotonicAttentionNetwork output (baseline-subtracted) ranges [0, ~43.5].
# With ATTN_RELAY_SCALE=0.01:  max relay farming = 2100 hops × 0.435 = ~913
# vs delivery reward = 70 sensors × 100 = 7000  (7.7× advantage for delivery).
# This keeps the attention mechanism active for reward scalarization
# while preventing the relay-loop exploit (agents farming relay indefinitely).
ATTN_RELAY_SCALE = 0.01


class MonotonicAttentionNetwork(nn.Module):
    """
    Monotonic Deep Neural Network with Q·K Attention for objective weighting.
    
    GUARANTEES: If r1_i <= r2_i for all i, then f(r1) <= f(r2)
    
    Architecture:
        r = [r_0, r_1, r_2, r_3]
                    ↓
        Q·K Attention: α_i = softmax(q · k_i / √d)  [LEARNED over episodes]
                    ↓
        Weighted Input: r' = α ⊙ r
                    ↓
        Monotonic Layers: positive weights + monotonic activations
                    ↓
        Scalar output
    
    Attention Mechanism:
    - Query q ∈ ℝ^d: learnable vector representing "ideal scalarization profile"
    - Keys k_i ∈ ℝ^d: learnable embeddings for each objective type
    - Attention: α_i = softmax(q · k_i / √d)
    
    Key Property for Monotonicity:
    - Attention weights α are computed from LEARNABLE PARAMETERS only
    - They do NOT depend on the input reward values r
    - Therefore: same r1 ≤ r2 → same α → monotonic output
    
    Learning Over Episodes:
    - Parameters (q, k, monotonic weights) updated via meta-learning
    - After each episode: compute meta-objective J (energy + balance)
    - Update parameters to maximize J using REINFORCE-style gradient
    
    References:
    - Vaswani et al. (2017): Attention Is All You Need (Q·K mechanism)
    - Sill (1998): Monotonic Networks
    """
    
    def __init__(self, n_objectives=4, embed_dim=16, hidden_dims=[16, 16]):
        """
        Args:
            n_objectives: Number of reward components (4 for WSN)
            embed_dim: Dimension of Q and K embeddings
            hidden_dims: List of hidden layer dimensions for monotonic net
        """
        super(MonotonicAttentionNetwork, self).__init__()
        
        self.n_objectives = n_objectives
        self.embed_dim = embed_dim
        self.hidden_dims = hidden_dims
        self.scale = 1.0 / (embed_dim ** 0.5)
        
        # =================================================================
        # Q·K ATTENTION COMPONENTS
        # =================================================================
        
        # Query: represents "what combination of objectives is ideal"
        # Learned to maximize meta-objective J over episodes
        self.query = nn.Parameter(torch.randn(embed_dim) * 0.1)
        
        # Keys: semantic embeddings for each objective type
        # k[0] = angle, k[1] = energy, k[2] = dispersion, k[3] = packets
        self.keys = nn.Parameter(torch.randn(n_objectives, embed_dim) * 0.1)
        
        # Initialize keys so energy & dispersion are more aligned with query
        self._initialize_attention_for_wsn()
        
        # =================================================================
        # MONOTONIC LAYERS: Weights constrained to be non-negative
        # =================================================================
        layers = []
        prev_dim = n_objectives
        
        for hidden_dim in hidden_dims:
            layers.append(MonotonicLinear(prev_dim, hidden_dim))
            layers.append(nn.Softplus())
            prev_dim = hidden_dim
        
        layers.append(MonotonicLinear(prev_dim, 1))
        self.monotonic_net = nn.Sequential(*layers)
        
        # Store attention weights for interpretability
        self.last_attention_weights = None
    
    def _initialize_attention_for_wsn(self):
        """Initialize Q·K so energy and dispersion get higher attention."""
        with torch.no_grad():
            # Create a base pattern for query
            base = torch.randn(self.embed_dim) * 0.1
            self.query.data = base.clone()
            
            # Keys aligned with query get higher attention
            # energy (idx 1) and dispersion (idx 2) aligned with query
            self.keys.data[1] = base + torch.randn(self.embed_dim) * 0.02  # energy
            self.keys.data[2] = base + torch.randn(self.embed_dim) * 0.02  # dispersion
            
            # angle (idx 0) and packets (idx 3) orthogonal to query
            self.keys.data[0] = torch.randn(self.embed_dim) * 0.1  # angle
            self.keys.data[3] = torch.randn(self.embed_dim) * 0.1  # packets
    
    def compute_attention_weights(self):
        """
        Compute attention weights using Q·K dot product.
        
        α_i = softmax(q · k_i / √d)
        
        IMPORTANT: These weights are computed from LEARNABLE PARAMETERS only.
        They do NOT depend on the input r, which preserves monotonicity.
        
        Returns:
            Tensor of shape (n_objectives,) with attention weights
        """
        # Dot product between query and each key: (n_objectives,)
        scores = torch.matmul(self.keys, self.query) * self.scale
        
        # Softmax to get weights that sum to 1
        weights = F.softmax(scores, dim=0)
        
        # Store for interpretability
        self.last_attention_weights = weights.detach()
        
        return weights
    
    def forward(self, r):
        """
        Compute scalar reward from multi-objective reward vector.
        
        The output is GUARANTEED to be monotonically increasing in each r_i.
        
        Args:
            r: Reward vector of shape (n_objectives,) or (batch, n_objectives)
        
        Returns:
            Scalar reward
        """
        squeeze_output = False
        if r.dim() == 1:
            r = r.unsqueeze(0)
            squeeze_output = True
        
        # Compute Q·K attention weights (independent of r!)
        attention_weights = self.compute_attention_weights()
        
        # Weight inputs by attention (preserves monotonicity since α > 0)
        weighted_r = r * attention_weights.unsqueeze(0)
        
        # Pass through monotonic network
        output = self.monotonic_net(weighted_r)
        
        if squeeze_output:
            output = output.squeeze(0)
        
        return output
    
    def get_interpretable_summary(self):
        """Return human-readable summary of learned Q·K attention."""
        weights = self.compute_attention_weights().cpu().detach().numpy()
        
        # Compute raw scores for more insight
        with torch.no_grad():
            scores = (torch.matmul(self.keys, self.query) * self.scale).cpu().numpy()
        
        summary = "\n" + "="*60 + "\n"
        summary += "  MONOTONIC Q·K ATTENTION NETWORK\n"
        summary += "="*60 + "\n"
        
        summary += "\n📊 Q·K ATTENTION WEIGHTS:\n"
        summary += "   α_i = softmax(q · k_i / √d)\n\n"
        
        sorted_idx = np.argsort(-weights)
        for idx in sorted_idx:
            bar_len = int(weights[idx] * 40)
            bar = "█" * bar_len + "░" * (40 - bar_len)
            summary += f"   {OBJECTIVE_NAMES[idx]:12s}: {weights[idx]:.3f} (score={scores[idx]:+.3f}) |{bar}|\n"
        
        summary += "\n🔍 HOW WEIGHTS ARE LEARNED:\n"
        summary += "   1. Episode runs with current attention weights\n"
        summary += "   2. Meta-objective J computed at episode end\n"
        summary += "   3. Q and K parameters updated to maximize J\n"
        summary += "   4. New weights emerge from updated Q·K products\n"
        
        summary += "\n✅ MONOTONICITY GUARANTEE:\n"
        summary += "   Attention weights don't depend on input r\n"
        summary += "   → Same ordering preserved for all inputs\n"
        
        summary += "\n" + "="*60 + "\n"
        return summary
    
    def verify_nonlinearity(self, n_samples=10):
        """
        Demonstrate that the network captures nonlinear interactions.
        
        A purely linear scalarizer would satisfy: f(αr) = αf(r)
        Our monotonic network with softplus activations is NONLINEAR.
        
        Returns:
            Dictionary with examples of nonlinear behavior
        """
        results = []
        
        with torch.no_grad():
            for _ in range(n_samples):
                r = torch.rand(4, dtype=torch.double) * 0.5 + 0.25  # [0.25, 0.75]
                alpha = 1.5
                
                f_r = self(r).item()
                f_alpha_r = self(alpha * r.clamp(max=1.0)).item()
                
                # For linear: f(αr) = αf(r)
                # Nonlinearity ratio: how different from linear
                expected_linear = alpha * f_r
                nonlinearity = abs(f_alpha_r - expected_linear) / (abs(expected_linear) + 1e-10)
                
                results.append({
                    'r': r.numpy(),
                    'f(r)': f_r,
                    'f(1.5r)': f_alpha_r,
                    'linear_expected': expected_linear,
                    'nonlinearity_ratio': nonlinearity
                })
        
        avg_nonlinearity = np.mean([r['nonlinearity_ratio'] for r in results])
        return {
            'samples': results,
            'avg_nonlinearity_ratio': avg_nonlinearity,
            'is_nonlinear': avg_nonlinearity > 0.01
        }


class MonotonicLinear(nn.Module):
    """
    Linear layer with non-negative weights (guarantees monotonicity).
    
    Uses softplus on raw weights to ensure w >= 0.
    
    Mathematical Guarantee:
        For y = σ(Wx + b) where W ≥ 0 and σ is monotonically increasing:
        ∂y/∂x = σ'(Wx + b) · W ≥ 0 (since σ' ≥ 0 and W ≥ 0)
        
    This means: if x1 ≤ x2 (component-wise), then y1 ≤ y2
    
    References:
        - Sill (1998): Monotonic Networks
        - Daniels & Velikova (2010): Monotone and Partially Monotone Neural Networks
    """
    
    def __init__(self, in_features, out_features):
        super(MonotonicLinear, self).__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        
        # Raw weights (unconstrained) - will be transformed by softplus
        self.weight_raw = nn.Parameter(torch.randn(out_features, in_features) * 0.1)
        self.bias = nn.Parameter(torch.zeros(out_features))
    
    def forward(self, x):
        # Apply softplus to ensure non-negative weights
        # softplus(x) = log(1 + exp(x)) ≥ 0 for all x
        weight_positive = F.softplus(self.weight_raw)
        return F.linear(x, weight_positive, self.bias)
    
    def get_positive_weights(self):
        """Return the actual (positive) weights used in forward pass."""
        return F.softplus(self.weight_raw)


# Alias for backward compatibility
ScalarAttentionModel = MonotonicAttentionNetwork

# ==============================================================================
# GLOBAL NETWORK INSTANCE
# ==============================================================================
# This network is shared across all environment instances and updated via 
# meta-learning at episode boundaries. The rewards computed by this network
# flow to the QMIX/QTRAN learners through batch["reward"] in the episode buffer.
#
# Architecture: Q·K Attention + Monotonic Neural Network
# Parameters: query (16), keys (4×16), monotonic weights (~400)
# ==============================================================================
net = MonotonicAttentionNetwork(n_objectives=input_dim, embed_dim=16, hidden_dims=[16, 16])
net = net.double()  # Use double precision for numerical stability

# Optimizer for outer loop (meta-learning of Q, K, and monotonic weights)
net_optimizer = torch.optim.Adam(net.parameters(), lr=1e-3)

# Evolution Strategies: store perturbation noise BEFORE episode for proper gradient estimate
# The noise must be the SAME used to perturb AND to compute gradient
_es_noise_cache = {}  # Maps param id -> noise tensor
_es_sigma = 0.01  # Perturbation scale


def perturb_network_for_episode():
    """
    Apply random perturbation to network parameters BEFORE episode starts.
    
    This is step 1 of Evolution Strategies:
    θ_perturbed = θ + σε  where ε ~ N(0, I)
    
    The noise ε is stored so it can be used in the gradient estimate after the episode.
    
    Must be called at the START of each episode (in reset()).
    """
    global _es_noise_cache
    _es_noise_cache.clear()  # Use clear() to preserve dict reference
    
    with torch.no_grad():
        for name, param in net.named_parameters():
            # Generate and store noise
            noise = torch.randn_like(param)
            _es_noise_cache[name] = noise
            
            # Apply perturbation: θ → θ + σε
            param.add_(noise * _es_sigma)


def restore_and_update_network(advantage):
    """
    Restore original parameters and apply ES gradient update.
    
    This is step 3 of Evolution Strategies:
    1. Remove perturbation: θ_perturbed - σε = θ_original
    2. Apply gradient: θ += lr * advantage * ε
    
    The gradient estimate is: ∇J ≈ (J - baseline) * ε / σ
    
    Must be called at the END of each episode (in update_scalarizer()).
    
    Args:
        advantage: (J - baseline), positive means episode was better than average
    """
    global _es_noise_cache
    
    if not _es_noise_cache:
        return  # No perturbation was applied (first episode)
    
    with torch.no_grad():
        for name, param in net.named_parameters():
            noise = _es_noise_cache.get(name)
            if noise is None:
                continue
            
            # Step 1: Remove perturbation to get back to original θ
            param.sub_(noise * _es_sigma)
            
            # Step 2: Apply ES gradient update
            # ∇J ≈ advantage * ε / σ, but we absorb σ into learning rate
            # Update: θ += lr * advantage * ε
            # Using lr = 0.01 for stable updates
            param.add_(advantage * noise * 0.01)
    
    # Clear cache (use clear() to preserve dict reference for importers)
    _es_noise_cache.clear()


def verify_monotonicity(network, n_samples=100, verbose=False):
    """
    Verify that the network is monotonically increasing.
    
    Tests: if r1 ≤ r2 (component-wise), then f(r1) ≤ f(r2)
    
    Args:
        network: MonotonicAttentionNetwork instance
        n_samples: Number of random test pairs
        verbose: Print details of any violations
        
    Returns:
        (is_monotonic, n_violations): Tuple of (bool, int)
    """
    violations = 0
    
    with torch.no_grad():
        for _ in range(n_samples):
            # Generate two random reward vectors where r1 ≤ r2
            r1 = torch.rand(4, dtype=torch.double) * 0.5  # [0, 0.5]
            delta = torch.rand(4, dtype=torch.double) * 0.5  # [0, 0.5]
            r2 = r1 + delta  # r2 ≥ r1 component-wise
            
            f_r1 = network(r1).item()
            f_r2 = network(r2).item()
            
            if f_r1 > f_r2 + 1e-10:  # Small tolerance for numerical errors
                violations += 1
                if verbose:
                    print(f"VIOLATION: f({r1.numpy()}) = {f_r1:.6f} > f({r2.numpy()}) = {f_r2:.6f}")
    
    return violations == 0, violations

class WSNRoutingEnv(gym.Env):

    ALGO_NAME = "" # Global flag to control the algorithm name
    gym_examples_current_version = "" # Global flag to control the gym_examples version
    coefficients = [] # Global flag for the weights of all the agents

    def __init__(
        self,
        n_sensors=70,
        coverage_radius=DEFAULT_COVERAGE_RADIUS,
        num_timesteps=None,
        version=None,
        invalid_action_penalty=0.02,
        living_penalty=0.001,
        delivery_bonus=100.0,
    ):

        super(WSNRoutingEnv, self).__init__()
        # Initialize local RNG (overridden by seed() if called before reset)
        self.np_random = np.random.RandomState()
        # Create filenames to save statistics for evaluation
        os.makedirs("results/data", exist_ok=True)
        algo_name = os.getenv('ALGO_NAME') or "UNKNOWN"
        gym_examples_current_version = os.getenv('gym_examples_current_version') or "unknown"
        self.statistics_filename = f"results/data/Statistics_filename_{algo_name}_{gym_examples_current_version}.txt"
        with open(self.statistics_filename, 'w') as file:
            file.write("returns, total_consumption_energy, std_remaining_energy, network_throughput, energy_efficiency, packet_delivery_ratio, network_lifetime, average_latency\n")
        # Initialize list of episode metrics
        self.num_timesteps = num_timesteps # This argument is for the PPO algorithm
        self.version = version # This argument is for the PPO algorithm
        self.number_of_steps = 0 # Total number of steps taken by the agent since the beginning of the training 
        self.episode_returns = []
        self.episode_std_remaining_energy = []
        self.episode_mean_remaining_energy = []
        self.episode_total_consumption_energy = []        
        self.episode_network_throughput = []
        self.episode_packet_delivery_ratio = []
        self.episode_network_lifetime = []
        self.episode_average_latency = []

        self.n_sensors = n_sensors
        self.n_agents = n_sensors
        self.coverage_radius = coverage_radius
        self.episode_count = 0
        self.scale_displacement = 0.01 * (upper_bound - lower_bound) # scale of the random displacement of the sensors
        self.epsilon = 1e-10 # small value to avoid division by zero

        # Reward shaping (kept small so it doesn't dominate task reward)
        # invalid_action_penalty: applied when a sensor chooses an impossible/forbidden action
        # living_penalty: applied each step to encourage finishing earlier
        self.invalid_action_penalty = float(invalid_action_penalty)
        self.living_penalty = float(living_penalty)
        self.delivery_bonus = float(delivery_bonus)

        # Cached baseline for reward centering (updated each episode in reset)
        self._reward_baseline = torch.tensor(0.0, dtype=torch.double)

        # Define observation space
        self.observation_space = Tuple(
            tuple([self._get_observation_space() for _ in range(self.n_sensors)])
        )

        self.action_space = MultiDiscrete([self.n_sensors + 1] * self.n_agents)

        self.reset()        

    def seed(self, seed=None):
        """Seed the environment's local RNG for reproducible topologies."""
        self.np_random = np.random.RandomState(seed)
        return [seed]

    def _check_network_connectivity(self):
        """Check if the network is connected to the base station using BFS.
        
        Returns True if at least one sensor can reach the BS (directly or via multi-hop).
        """
        # Find sensors that can directly reach BS
        direct_to_bs = set(np.where(self.distance_to_base <= self.coverage_radius)[0])
        
        if len(direct_to_bs) == 0:
            return False  # No sensor can reach BS
        
        # Build adjacency: sensor i can reach sensor j if within coverage_radius
        # Use BFS from BS-reachable sensors to see how many can route to BS
        reachable = set(direct_to_bs)
        frontier = list(direct_to_bs)
        
        while frontier:
            current = frontier.pop(0)
            for j in range(self.n_sensors):
                if j in reachable:
                    continue
                dist = np.linalg.norm(self.sensor_positions[current] - self.sensor_positions[j])
                if dist <= self.coverage_radius:
                    reachable.add(j)
                    frontier.append(j)
        
        # Return True if a reasonable fraction of sensors can reach BS
        connectivity_ratio = len(reachable) / self.n_sensors
        return connectivity_ratio >= 0.5  # At least 50% connectivity

    def reset(self):
        # Update scalarizer based on previous episode (if not first episode)
        if self.episode_count > 0:
            meta_J = self.compute_meta_objective()
            advantage = self.update_scalarizer(meta_J)
            print(f"[CAS] Meta-objective J={meta_J:.4f}, Advantage={advantage:.4f}")
            # Log learned capacities periodically
            if self.episode_count % 50 == 0:
                print(net.get_interpretable_summary())
        
        print("\n============================================")
        print(f"Episode count: {self.episode_count}")
        self.episode_return = 0
        
        # Generate sensor positions ensuring network connectivity
        max_attempts = 10
        for attempt in range(max_attempts):
            self.sensor_positions = self.np_random.rand(self.n_sensors, 2) * (upper_bound - lower_bound) + lower_bound
            self.distance_to_base = np.linalg.norm(self.sensor_positions - base_station_position, axis=1)
            
            if self._check_network_connectivity():
                break
            
            if attempt == max_attempts - 1:
                # Last attempt: place some sensors closer to BS to ensure connectivity
                n_close = max(7, self.n_sensors // 7)  # ~15% of sensors near BS
                for i in range(n_close):
                    # Place within coverage_radius of BS
                    angle = self.np_random.uniform(0, 2 * np.pi)
                    radius = self.np_random.uniform(0, self.coverage_radius * 0.9)
                    self.sensor_positions[i] = base_station_position + radius * np.array([np.cos(angle), np.sin(angle)])
                self.distance_to_base = np.linalg.norm(self.sensor_positions - base_station_position, axis=1)
                print(f"[WSN] Forced {n_close} sensors near BS for connectivity")
        
        self.remaining_energy = np.ones(self.n_sensors) * initial_energy
        self.number_of_packets = np.ones(self.n_sensors, dtype=int) * initial_number_of_packets # number of packets to transmit

        self.packets_delivered = 0
        self.total_energy_consumed = 0
        self.steps = 0
        self.first_node_dead_time = None
        self.total_latency = 0
        self.packet_latency = np.zeros(self.n_sensors)  # Latency for each packet
        self.total_packets_sent_by_sensors = 0

        self.network_throughput = None
        self.energy_efficiency = None
        self.packet_delivery_ratio = None
        self.network_lifetime = None
        self.average_latency = None

        # Extended per-episode counters for feasibility/runtime analysis
        self.delivered_hops_total = 0
        self.direct_to_bs_count = 0
        self.relay_delivery_count = 0
        self.rx_failures_count = 0
        self.tx_failures_count = 0
        self.out_of_range_count = 0
        self._step_times_ms = []
        self._stranded_sensors = set()  # sensors with packets/energy but no reachable targets

        self.episode_count += 1

        self.get_metrics()
        
        # ES Step 1: Perturb network parameters BEFORE this episode starts
        # This ensures the noise used for gradient estimation matches the perturbation
        perturb_network_for_episode()

        # Cache zero-input baseline for reward centering
        self._update_reward_baseline()

        return self._get_obs()


    def step(self, actions):
        import time
        t0 = time.perf_counter()
        self.number_of_steps += 1
        self.steps += 1 
        # Stranded set was populated by get_avail_actions() called before step()
        # rewards = [-max_reward] * self.n_sensors
        rewards = [np.array([-self.living_penalty] * input_dim, dtype=np.float64) for _ in range(self.n_sensors)]
        dones = [False] * self.n_sensors
        for i, action in enumerate(actions):
            if self.remaining_energy[i] <= 0 or self.number_of_packets[i] <= 0:
                rewards[i] = 0.0  # Inactive sensors contribute zero to team reward
                continue  # Skip if sensor has no energy left or no packets to transmit
            
            # Stranded sensors (have packets/energy but no valid target) get 0 reward.
            # They were given a fallback action in get_avail_actions() to avoid
            # empty action masks, but we don't penalize them for forced failures.
            if i in self._stranded_sensors:
                rewards[i] = 0.0
                continue
            
            if action == i:
                # Penalize forbidden self-loop (mild: masked out anyway)
                rewards[i] = -0.1
                continue
            
            if action == self.n_sensors:
                if self.distance_to_base[i] > self.coverage_radius:
                    self.out_of_range_count += 1
                    rewards[i] = -0.1  # mild: no state change
                    continue  # Out of range

                # Calculate the energy consumption for transmitting data to the base station
                transmission_energy = self.transmission_energy(self.number_of_packets[i], self.distance_to_base[i])
                if self.remaining_energy[i] < transmission_energy:
                    # self.remaining_energy[i] = 0
                    self.tx_failures_count += 1
                    rewards[i] = -0.5  # moderate: should have checked energy
                    continue  # Not enough energy
                
                self.update_sensor_energies(i, transmission_energy)

                # Update the metrics
                self.total_energy_consumed += transmission_energy
                self.packets_delivered += self.number_of_packets[i]
                self.total_packets_sent_by_sensors += self.number_of_packets[i]
                self.total_latency += self.packet_latency[i] + latency_per_hop
                # Count hops for delivery (approx: existing hops + this hop)
                hops = (self.packet_latency[i] / latency_per_hop) + 1
                self.delivered_hops_total += hops
                # Classify delivery path
                if self.packet_latency[i] > 0:
                    self.relay_delivery_count += 1
                else:
                    self.direct_to_bs_count += 1
                self.packet_latency[i] = 0

                n_delivered = self.number_of_packets[i]  # Save count before reset
                self.number_of_packets[i] = 0 # Reset the number of packets of the sensor i

                # Delivery reward: strong positive signal proportional to packets delivered
                rewards[i] = self.delivery_bonus * n_delivered
                dones[i] = True
                continue  # Done with this sensor
            else:
                distance = np.linalg.norm(self.sensor_positions[i] - self.sensor_positions[action])
                if distance > self.coverage_radius:
                    self.out_of_range_count += 1
                    rewards[i] = -0.1  # mild: no state change
                    continue

                transmission_energy = self.transmission_energy(self.number_of_packets[i], distance)
                reception_energy = self.reception_energy(self.number_of_packets[i])
                if self.remaining_energy[i] < transmission_energy:
                    # self.remaining_energy[i] = 0 
                    self.tx_failures_count += 1
                    rewards[i] = -0.5  # moderate: should have checked energy
                    continue
                
                self.update_sensor_energies(i, transmission_energy)
                # Update the metrics
                self.total_energy_consumed += transmission_energy
                self.total_packets_sent_by_sensors += self.number_of_packets[i]

                if self.remaining_energy[action] < reception_energy:
                    # self.remaining_energy[action] = 0
                    self.rx_failures_count += 1
                    self.packet_latency[i] = 0 # Reset the latency of the packet
                    self.number_of_packets[i] = 0 # Reset the number of packets of the sensor i
                    rewards[i] = -0.5  # moderate: packets lost + energy wasted
                    continue  # Skip if the next hop does not have enough energy to receive data

                self.update_sensor_energies(action, reception_energy) 

                # Update the metrics
                self.total_energy_consumed += reception_energy
                self.packet_latency[action] += self.packet_latency[i] + latency_per_hop
                self.packet_latency[i] = 0

                rewards[i] = rewards[i] + self.compute_individual_rewards(i, action)
                
                # Update the number of packets
                self.number_of_packets[action] += self.number_of_packets[i]
                
                self.number_of_packets[i] = 0 # Reset the number of packets of the sensor i
        
            # Relay reward: attention-based scalarization + progress shaping.
            #   attention: MonotonicAttentionNetwork(individual_rewards) - baseline
            #              Scales multi-objective [angle, energy, dispersion, packets]
            #              into a single scalar via Q·K attention + monotonic net.
            #              Output range [0, ~43.5], scaled by ATTN_RELAY_SCALE (0.01)
            #              to prevent relay-loop farming exploit.
            #   progress:  (dist_before - dist_after) / coverage_radius
            #              Rewards relays that move packets closer to BS.
            relay_attn = self.compute_attention_rewards(rewards[i])
            # Progress shaping: fraction of distance reduced toward BS
            dist_before = self.distance_to_base[i]
            dist_after  = self.distance_to_base[action]
            progress = (dist_before - dist_after) / (self.coverage_radius + 1e-8)
            attn_val = float(relay_attn.item() if isinstance(relay_attn, torch.Tensor) else relay_attn)
            rewards[i] = attn_val * ATTN_RELAY_SCALE + progress * 0.5

        # Integrate the mobility of the sensors
        # self.integrate_mobility() 

        self.distance_to_base = np.linalg.norm(self.sensor_positions - base_station_position, axis=1)

        if self.first_node_dead_time is None and np.any(self.remaining_energy <= 0):
            self.first_node_dead_time = self.steps

        self.get_metrics()

        def _as_scalar_reward(r):
            if isinstance(r, torch.Tensor):
                r = r.detach().cpu()
                return float(r.sum().item())
            if isinstance(r, np.ndarray):
                return float(np.sum(r))
            if isinstance(r, (list, tuple)):
                return float(np.sum(r))
            return float(r)

        # Ensure the environment returns a scalar reward even if intermediate reward
        # signals are vectors (e.g., attention-based rewards).
        rewards = sum(_as_scalar_reward(r) for r in rewards)

        # Episode ends only when ALL original packets have been delivered to BS.
        # TimeLimit wrapper handles truncation at time_limit steps for training.
        # This allows multi-hop routing to complete over many steps.
        dones = (self.packets_delivered >= self.n_sensors * initial_number_of_packets)

        self.episode_return += rewards

        # Record env step wall time (ms)
        self._step_times_ms.append((time.perf_counter() - t0) * 1000.0)
        return self._get_obs(), rewards, dones, self.get_metrics()


    def _get_obs(self):
        return [{'remaining_energy': np.array([e], dtype=np.float32), 
                 'consumption_energy': np.array([initial_energy - e], dtype=np.float32),
                 'sensor_positions': np.asarray(p, dtype=np.float32),
                 'number_of_packets': np.array([d], dtype=np.int64)
                } for e, p, d in zip(self.remaining_energy, self.sensor_positions, self.number_of_packets)]


    def _get_observation_space(self):
        return Dict(OrderedDict([
        ('remaining_energy', Box(low=0, high=initial_energy, shape=(1,), dtype=np.float32)),
        ('consumption_energy', Box(low=0, high=initial_energy, shape=(1,), dtype=np.float32)),
        ('sensor_positions', Box(low=lower_bound, high=upper_bound, shape=(2,), dtype=np.float32)),
        ('number_of_packets', Box(low=0, high=self.n_sensors * initial_number_of_packets + 1, shape=(1,), dtype=np.int64))
    ]))


    def get_state(self):
        return self._get_obs()
    

    def get_avail_actions(self):
        """Return available actions for each agent respecting physical constraints.
        
        For agent i, action j is available if:
        - j != i (no self-loop)
        - j < n_sensors: sensor j is within coverage_radius of sensor i AND
          sensor i has enough energy to transmit AND sensor j has enough energy to receive
        - j == n_sensors (base station): BS is within coverage_radius of sensor i AND
          sensor i has enough energy to transmit
        
        An agent with no packets or no energy has only a dummy action available
        (action 0, which will be skipped in step()).
        """
        avail = []
        for i in range(self.n_sensors):
            agent_avail = [0] * (self.n_sensors + 1)
            
            # If sensor has no packets or no energy, mark only one action available
            # (to avoid empty action space) but step() will skip this agent anyway
            if self.remaining_energy[i] <= 0 or self.number_of_packets[i] <= 0:
                agent_avail[0] = 1  # dummy valid action
                avail.append(agent_avail)
                continue
            
            # Check each potential target
            for j in range(self.n_sensors):
                if j == i:
                    continue  # No self-loop
                
                # Check if target sensor is within coverage radius
                distance = np.linalg.norm(self.sensor_positions[i] - self.sensor_positions[j])
                if distance > self.coverage_radius:
                    continue
                
                # Check if sender has enough energy to transmit
                tx_energy = self.transmission_energy(self.number_of_packets[i], distance)
                if self.remaining_energy[i] < tx_energy:
                    continue
                
                # Check if receiver has enough energy to receive
                rx_energy = self.reception_energy(self.number_of_packets[i])
                if self.remaining_energy[j] < rx_energy:
                    continue
                
                agent_avail[j] = 1
            
            # Check if base station is reachable (action n_sensors)
            if self.distance_to_base[i] <= self.coverage_radius:
                tx_energy_to_bs = self.transmission_energy(self.number_of_packets[i], self.distance_to_base[i])
                if self.remaining_energy[i] >= tx_energy_to_bs:
                    agent_avail[self.n_sensors] = 1
            
            # If no valid actions found, mark sensor as stranded (no reachable targets).
            # Provide a fallback action but step() will give reward=0 (not penalized).
            if sum(agent_avail) == 0:
                self._stranded_sensors.add(i)
                # Allow any in-range neighbor to avoid empty mask
                for j in range(self.n_sensors):
                    if j != i:
                        distance = np.linalg.norm(self.sensor_positions[i] - self.sensor_positions[j])
                        if distance <= self.coverage_radius:
                            agent_avail[j] = 1
                            break
                if sum(agent_avail) == 0:
                    # Last resort: mark first non-self action (will fail but won't crash)
                    fallback_action = 1 if i == 0 else 0
                    agent_avail[fallback_action] = 1
            
            avail.append(agent_avail)
        
        return avail
    
    
    def update_sensor_energies(self, i, delta_energy):
        self.remaining_energy[i] -= delta_energy
        if self.remaining_energy[i] < 0:
            self.remaining_energy[i] = 0


    def transmission_energy(self, number_of_packets, distance):
        # energy consumption for transmitting data on a distance        
        return number_of_packets * info_amount * (Eelec + Eamp * distance**2)
    

    def reception_energy(self, number_of_packets):
        # energy consumption for receiving data
        return number_of_packets * info_amount * Eelec
    

    def compute_angle_vectors(self, i, action):
        '''
        Compute the angle in radians between the vectors formed by (i, action) and (i, base station)
        '''
        if action == self.n_sensors:
            return 0
        else:
            vector_to_next_hop = self.sensor_positions[action] - self.sensor_positions[i]
            vector_to_base = base_station_position - self.sensor_positions[i]
            cosine_angle = np.dot(vector_to_next_hop, vector_to_base) / (np.linalg.norm(vector_to_next_hop) * np.linalg.norm(vector_to_base))
            
            return np.arccos(np.clip(cosine_angle, -1, 1))


    def compute_reward_angle(self, i, action):
        '''
        Compute the reward based on the angle between the vectors formed by (i, action) and (i, base station)
        '''
        # Calculate the angle in radians between the vectors formed by (i, action) and (i, base station)
        angle = self.compute_angle_vectors(i, action)
        # Normalize the angle
        normalized_angle = abs(angle) / np.pi

        return np.clip(1 - normalized_angle, 0, 1)
        # return np.clip(- normalized_angle, -1, 1)
    

    def compute_reward_distance(self, i, action):
        '''
        Compute the reward based on the distance to the next hop
        '''
        if action == self.n_sensors:
            # For base station, the distance is the precomputed scalar distance_to_base[i]
            distance = float(self.distance_to_base[i])
        else:
            distance = np.linalg.norm(self.sensor_positions[i] - self.sensor_positions[action])
        # Normalize the distance to the next hop
        normalized_distance_to_next_hop = distance / self.coverage_radius

        return np.clip(1 - normalized_distance_to_next_hop, 0, 1)
        # return np.clip(-normalized_distance_to_next_hop, -1, 1)


    def compute_reward_consumption_energy(self, i, action):
        '''
        Compute the reward based on the total energy consumption (transmission, reception)
        '''
        # Calculate the total energy consumption (transmission, reception)
        if action == self.n_sensors:
            total_energy = self.transmission_energy(self.number_of_packets[i], self.distance_to_base[i])
        else:
            distance = np.linalg.norm(self.sensor_positions[i] - self.sensor_positions[action])
            transmission_energy = self.transmission_energy(self.number_of_packets[i], distance)
            reception_energy = self.reception_energy(self.number_of_packets[i])
            total_energy = transmission_energy + reception_energy
        
        # Normalize the total energy consumption
        max_transmission_energy = self.transmission_energy(self.n_sensors * initial_number_of_packets, self.coverage_radius)
        max_reception_energy = self.reception_energy(self.n_sensors * initial_number_of_packets)
        max_total_energy = max_transmission_energy + max_reception_energy
        normalized_total_energy = total_energy / (max_total_energy + self.epsilon)

        return np.clip(1 - normalized_total_energy, 0, 1)
        # return np.clip(- normalized_total_energy, -1, 1)


    def compute_reward_dispersion_remaining_energy(self):
        '''
        Compute the reward based on the standard deviation of the remaining energy
        '''
        dispersion_remaining_energy = np.std(self.remaining_energy)
        # Normalize the standard deviation of the remaining energy
        max_dispersion_remaining_energy = initial_energy / 2 # maximum standard deviation of the remaining energy if n_sensors is even
        normalized_dispersion_remaining_energy = dispersion_remaining_energy / (max_dispersion_remaining_energy + self.epsilon)

        return np.clip(1 - normalized_dispersion_remaining_energy, 0, 1)
        # return np.clip(- normalized_dispersion_remaining_energy, -1, 1)


    def compute_reward_number_of_packets(self, action):
        '''
        Compute the reward based on the number of packets of the receiver
        '''
        max_number_of_packets = self.n_sensors * initial_number_of_packets
        if action == self.n_sensors:
            normalized_number_of_packets = 0
        else: 
            normalized_number_of_packets = self.number_of_packets[action] / (max_number_of_packets + self.epsilon)

        return np.clip(1 - normalized_number_of_packets, 0, 1)
        # return np.clip(- normalized_number_of_packets, -1, 1)


    def compute_individual_rewards(self, i, action):
        '''
        Compute the individual rewards
        '''
        #-- rewards related to the energy consumption minimization and energy balance
        reward_angle = self.compute_reward_angle(i, action)
        # reward_distance = self.compute_reward_distance(i, action)
        reward_consumption_energy = self.compute_reward_consumption_energy(i, action)
        reward_dispersion_remaining_energy = self.compute_reward_dispersion_remaining_energy()
        reward_number_of_packets = self.compute_reward_number_of_packets(action)

        rewards_energy = np.array([reward_angle, reward_consumption_energy, reward_dispersion_remaining_energy, reward_number_of_packets])

        #-- rewards related to the performance metrics
        reward_latency = self.compute_reward_latency()
        
        reward_network_throughput = self.compute_reward_network_throughput()
        reward_packet_delivery_ratio = self.compute_reward_packet_delivery_ratio()

        rewards_performance = np.array([reward_latency, reward_network_throughput, reward_packet_delivery_ratio])
    
        return rewards_energy
    

    def compute_network_rewards(self):

        reward_consumption_energy = self.network_reward_consumption_energy()
        reward_dispersion_remaining_energy = self.network_reward_dispersion_remaining_energy()
        rewards_energy = [reward_consumption_energy, reward_dispersion_remaining_energy]

        reward_latency = self.compute_reward_latency()
        reward_network_throughput = self.compute_reward_network_throughput()
        reward_packet_delivery_ratio = self.compute_reward_packet_delivery_ratio()        
        rewards_performance = [reward_latency, reward_network_throughput, reward_packet_delivery_ratio]

        return np.concatenate((rewards_energy, rewards_performance))


    def network_reward_dispersion_remaining_energy(self):
        '''
        Compute the reward based on the standard deviation of the remaining energy at the network level
        '''
        dispersion_remaining_energy = np.std(self.remaining_energy)
        # Normalize the standard deviation of the remaining energy
        max_dispersion_remaining_energy = initial_energy / 2 # maximum standard deviation of the remaining energy if n_sensors is even
        normalized_dispersion_remaining_energy = dispersion_remaining_energy / (max_dispersion_remaining_energy + self.epsilon)

        return np.clip(1 - normalized_dispersion_remaining_energy, 0, 1)
        # return np.clip(- normalized_dispersion_remaining_energy, -1, 1)
    

    def network_reward_consumption_energy(self):
        '''
        Compute the reward based on the total energy consumption (transmission, reception) at the network level
        '''
        total_energy = self.n_sensors * initial_energy - np.sum(self.remaining_energy)
        # Normalize the total energy consumption
        max_total_energy = self.n_sensors * initial_energy
        normalized_total_energy = total_energy / (max_total_energy + self.epsilon)

        return np.clip(1 - normalized_total_energy, 0, 1)
        # return np.clip(- normalized_total_energy, -1, 1)
    

    def compute_reward_packet_delivery_ratio(self):
        '''
        Compute the reward based on the packet delivery ratio
        '''
        packet_delivery_ratio = self.packets_delivered / self.total_packets_sent_by_sensors if self.total_packets_sent_by_sensors > 0 else 0
        return np.clip(packet_delivery_ratio, 0, 1)
    

    def compute_reward_latency(self):
        '''
        Compute the reward based on the average latency
        '''
        # Normalize the average latency
        # Bound in same units as total_latency (includes latency_per_hop per hop)
        max_latency = self.n_sensors * self.steps * latency_per_hop
        normalized_latency = self.total_latency / (max_latency + self.epsilon)

        return np.clip(1 - normalized_latency, 0, 1)
        # return np.clip(- normalized_latency, -1, 1)


    def compute_reward_network_throughput(self):
        '''
        Compute the reward based on the network throughput
        '''
        network_throughput = self.packets_delivered / self.steps if self.steps > 0 else 0
        maximum_throughput = self.n_sensors * initial_number_of_packets
        normalized_throughput = network_throughput / (maximum_throughput + self.epsilon)
        return np.clip(normalized_throughput, 0, 1)
    

    def compute_attention_rewards(self, reward):
        '''
        Compute scalar reward using Monotonic Q·K Attention Network.
        
        This method applies the MonotonicAttentionNetwork which:
        1. Uses Q·K attention over objective TYPES to compute importance weights
           α_i = softmax(q · k_i / √d) where q and k are learned over episodes
        2. Applies weighted input r' = α ⊙ r (element-wise product)
        3. Passes through monotonic neural network layers (W ≥ 0, softplus activation)
        
        The architecture GUARANTEES monotonicity:
        - If r1 ≤ r2 component-wise, then f(r1) ≤ f(r2)
        - Attention weights α depend only on learned parameters, NOT on input r
        
        Args:
            reward: numpy array of shape (4,) with [angle, energy, dispersion, packets]
                    Each component is normalized to [0, 1], higher = better
        
        Returns:
            Scalar reward (torch.Tensor) that is monotonic in the input
        
        Notes:
            - The global `net` (MonotonicAttentionNetwork) is updated at episode end
            - Learning is driven by meta-objective J (efficiency + balance)
        '''
        # Convert to torch tensor (no gradient needed during forward pass for RL)
        # Subtract baseline (output at zero input) to center rewards around 0.
        # Without centering, the network outputs ~86 even for zero input, making
        # the delivery signal (138) barely distinguishable from relay (128).
        # After centering: delivery ~52, relay ~42, inactive ~0.
        with torch.no_grad():
            rewards_i = torch.tensor(reward, dtype=torch.double)
            return net(rewards_i) - self._reward_baseline

    def _update_reward_baseline(self):
        """Cache the network output at zero input for reward centering.

        Called once per episode (in reset) after network perturbation.
        This ensures centered rewards regardless of network parameter values.
        """
        with torch.no_grad():
            self._reward_baseline = net(torch.zeros(input_dim, dtype=torch.double))

    def compute_meta_objective(self):
        '''
        Compute the meta-objective J for outer-loop learning.
        
        J measures the TRUE goals:
        - Minimize total energy consumption
        - Minimize energy dispersion (balance)
        
        Higher J = better episode.
        '''
        # Energy efficiency: 1 - (consumed / max_possible)
        total_consumed = self.n_sensors * initial_energy - np.sum(self.remaining_energy)
        max_consumed = self.n_sensors * initial_energy
        efficiency_score = 1 - (total_consumed / (max_consumed + self.epsilon))
        
        # Energy balance: 1 - (std / max_std)
        std_remaining = np.std(self.remaining_energy)
        max_std = initial_energy / 2  # Theoretical max std
        balance_score = 1 - (std_remaining / (max_std + self.epsilon))
        
        # Combined meta-objective (both in [0,1], higher is better)
        # Equal weight by default, can be adjusted
        lambda_balance = 1.0
        J = efficiency_score + lambda_balance * balance_score
        
        return J
    
    def update_scalarizer(self, meta_return):
        '''
        Update the Q·K Attention Network based on episode meta-return.
        
        This is the OUTER LOOP of the bi-level optimization:
        - Inner loop: RL policy (QMIX/QTRAN) trained with scalar rewards from network
        - Outer loop: Attention network trained to maximize meta-objective J
        
        Evolution Strategies (ES) Update:
        -----------------------------------
        ES is a gradient-free optimization method that estimates gradients via:
            ∇J ≈ (1/σ) * E[(J(θ + σε) - baseline) * ε]
        
        The algorithm works in 3 steps:
        1. BEFORE episode: Perturb θ → θ + σε (done in reset() via perturb_network_for_episode())
        2. RUN episode with perturbed parameters, compute J
        3. AFTER episode: Update θ += lr * (J - baseline) * ε using SAME noise ε
        
        This is correct because the noise ε used to perturb is the SAME noise
        used to compute the gradient. This correlation is what makes ES work.
        
        Args:
            meta_return: The meta-objective J value at episode end
                        J = efficiency_score + balance_score ∈ [0, 2]
        
        Returns:
            advantage: meta_return - baseline (positive = better than average)
        
        Connection to QMIX/QTRAN:
        - The learners (q_learner.py, qtran_learner.py) receive scalar rewards
        - These rewards come from env.step() which calls compute_attention_rewards()
        - The reward flows: r_vector → MonotonicAttentionNetwork → scalar → batch["reward"]
        '''
        # Compute baseline using exponential moving average (EMA)
        # EMA with β=0.9 roughly averages over the last ~10 episodes
        # This reduces variance in the gradient estimate
        if not hasattr(self, '_meta_baseline'):
            self._meta_baseline = meta_return
        else:
            self._meta_baseline = 0.9 * self._meta_baseline + 0.1 * meta_return
        
        advantage = meta_return - self._meta_baseline
        
        # ES Step 3: Restore original params and apply gradient using SAME noise from Step 1
        # Only update if advantage is significant (reduces noise)
        if abs(advantage) > 0.01:
            restore_and_update_network(advantage)
        else:
            # Still need to restore even if not updating
            restore_and_update_network(0.0)  # advantage=0 means no update, just restore
        
        return advantage

    def integrate_mobility(self):
        '''
        Integrate the mobility of the sensors after each step
        '''
        # Add a small random displacement to each sensor's position
        displacement = self.np_random.normal(scale=self.scale_displacement, size=(self.n_sensors, 2))
        self.sensor_positions += displacement
        # Cancel the displacement if the sensor goes out of bounds
        for i in range(self.n_sensors):
            if not(np.all(self.sensor_positions[i] >= lower_bound) and np.all(self.sensor_positions[i] <= upper_bound)):
                self.sensor_positions[i] -= displacement[i]
    

    def get_metrics(self):
        # Calculate network throughput
        self.network_throughput = self.packets_delivered / self.steps if self.steps > 0 else 0
        # Calculate energy efficiency
        self.energy_efficiency = self.packets_delivered / self.total_energy_consumed if self.total_energy_consumed > 0 else 0
        # Calculate packet delivery ratio
        # PDR uses original packet count as denominator (not relay-inflated count)
        self.packet_delivery_ratio = self.packets_delivered / (self.n_sensors * initial_number_of_packets)
        # Calculate network lifetime
        self.network_lifetime = self.first_node_dead_time if self.first_node_dead_time is not None else self.steps
        # Calculate average latency: undefined when no packets delivered (use NaN)
        self.average_latency = (self.total_latency / self.packets_delivered) if self.packets_delivered > 0 else float('nan')
        # Extended aggregates
        self.avg_hops_per_delivered_packet = (self.delivered_hops_total / self.packets_delivered) if self.packets_delivered > 0 else float('nan')
        env_step_time_ms_mean = float(np.mean(self._step_times_ms)) if len(self._step_times_ms) > 0 else 0.0

        return {
            "network_throughput": self.network_throughput,
            "energy_efficiency": self.energy_efficiency,
            "packet_delivery_ratio": self.packet_delivery_ratio,
            "network_lifetime": self.network_lifetime,
            "average_latency": self.average_latency,
            # Extended metrics (env runtime and structure/failures)
            "avg_hops_per_delivered_packet": self.avg_hops_per_delivered_packet,
            "direct_to_bs_count": self.direct_to_bs_count,
            "relay_delivery_count": self.relay_delivery_count,
            "rx_failures_count": self.rx_failures_count,
            "tx_failures_count": self.tx_failures_count,
            "out_of_range_count": self.out_of_range_count,
            "env_step_time_ms_mean": env_step_time_ms_mean
        }
    

    def find_next_sensor(self):
        for offset in range(1, self.n_sensors):
            next_index = (self.current_sensor + offset) % self.n_sensors
            if self.remaining_energy[next_index] > 0 and self.number_of_packets[next_index] > 0:
                return next_index
        return None  # If no such sensor is found
    

    def to_base_n(self, number, base):
        """Convert a number to a base-n number."""
        if number == 0:
            return [0] * (base - 1)
        
        digits = []
        while number:
            digits.append(number % base)
            number //= base
        return digits[::-1]  # Reverse the list to get the correct order