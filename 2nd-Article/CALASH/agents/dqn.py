"""
Deep Q-Network (DQN) Routing Agent
===================================
Lightweight DQN for autonomous carbon-aware next-hop selection.

This is the **learning** component that makes CALASH genuinely autonomous:
the agent adapts its routing policy from experience during simulation,
without any offline training or human-in-the-loop parameter tuning.

Architecture (NumPy-only -- no PyTorch/TF dependency):
    - 2-layer MLP:  state(8) -> 64 -> 32 -> 1  (candidate value estimator)
    - ReLU activations, Xavier/Glorot initialization [3]
    - Experience replay buffer (10,000 transitions) [4]
    - Target network with Polyak soft-update (tau = 0.005) [5]
    - Epsilon-greedy exploration with cosine annealing
    - Double DQN action selection [2]: online network selects action,
      target network evaluates Q-value (reduces overestimation bias)

Design rationale (Contextual Value Network):
    Unlike standard DQN where actions are a fixed discrete set, WSN
    routing has a *variable* candidate set: the alive next-hop nodes
    change every round.  We handle this via a contextual architecture
    [6] where the state vector encodes BOTH the source context AND
    the candidate features:

        state = [e_src/E0, d_src_BS, CI, Z, alive_ratio,
                 e_cand/E0, d_cand_BS, hop_dist]

    The network outputs a single scalar V(state) estimating the value
    of choosing this particular candidate.  To select among K candidates,
    we evaluate V(state_k) for each k and pick argmax.

    This ensures stable Q-learning: the same state vector always maps
    to the same value, regardless of how many candidates exist.

State vector (8D):
    [e_src/E0, d_src_BS/d_max, CI_norm, Z_norm, alive_ratio,
     e_cand/E0, d_cand_BS/d_max, hop_dist/d_max]

Action: implicit in the state (candidate features encoded at positions 5-7)

Reward (multi-objective, novel to CALASH):
    r = +1.0 * (progress/d_max)             delivery progress
      - 0.3 * CI_norm * (E_tx * J_to_kWh)   carbon cost
      - 0.3 * (E_tx / E_src)                 energy fraction cost
      - 0.2 * max(0, LF - 1)                lifecycle penalty
      + 5.0 * I{delivered_to_BS}             delivery bonus
      - 2.0 * I{packet_dropped}              drop penalty

Computational complexity:
    Per routing decision: O(K * d) where K = |candidates|, d = 8
    Per training step:    O(B * d * H) where B = batch_size, H = hidden_dim
    Total per round:      O(C * K * d + train_step) where C = num_CHs

Implementation note:
    The entire DQN is implemented in pure NumPy (no PyTorch/TensorFlow)
    to ensure zero external dependencies and full reproducibility.
    Forward/backward passes, replay buffer, and target sync are all
    hand-coded. This makes the framework pip-installable with only
    numpy + matplotlib.

References
----------
[1] Mnih, V. et al. "Human-level control through deep reinforcement
    learning." Nature, 518(7540), pp. 529-533, 2015.
    DOI: 10.1038/nature14236

[2] Van Hasselt, H., Guez, A. & Silver, D. "Deep Reinforcement Learning
    with Double Q-learning." Proc. AAAI, 2016.
    DOI: 10.1609/aaai.v30i1.10295

[3] Glorot, X. & Bengio, Y. "Understanding the difficulty of training
    deep feedforward neural networks." Proc. AISTATS, 2010.
    (Xavier initialization used for weight matrices.)

[4] Lin, L.-J. "Self-improving reactive agents based on reinforcement
    learning, planning and teaching." Machine Learning, 8(3-4), 1992.
    DOI: 10.1007/BF00992699  (Experience replay buffer.)

[5] Polyak, B.T. & Juditsky, A.B. "Acceleration of stochastic
    approximation by averaging." SIAM J. Control and Optimization,
    30(4), 1992. (Polyak averaging / soft target update.)

[6] Dulac-Arnold, G. et al. "Deep Reinforcement Learning in Large
    Discrete Action Spaces." arXiv:1512.07679, 2015.
    (Contextual action encoding for variable action spaces.)
"""

import warnings as _warnings
import numpy as np
from typing import List, Tuple, Optional, Union
from models.network import Node

# Suppress matmul overflow warnings globally for this module
_warnings.filterwarnings('ignore', category=RuntimeWarning, module=__name__)


# ═══════════════════════════════════════════════════════════════════
# NumPy MLP — lightweight 2-layer neural network
# ═══════════════════════════════════════════════════════════════════

class _NumpyMLP:
    """Minimal 2-hidden-layer MLP using only NumPy."""

    def __init__(self, input_dim: int, hidden1: int, hidden2: int,
                 output_dim: int, rng: np.random.Generator):
        # Xavier initialization
        self.W1 = rng.normal(0, np.sqrt(2.0 / input_dim),
                             (input_dim, hidden1)).astype(np.float32)
        self.b1 = np.zeros(hidden1, dtype=np.float32)
        self.W2 = rng.normal(0, np.sqrt(2.0 / hidden1),
                             (hidden1, hidden2)).astype(np.float32)
        self.b2 = np.zeros(hidden2, dtype=np.float32)
        self.W3 = rng.normal(0, np.sqrt(2.0 / hidden2),
                             (hidden2, output_dim)).astype(np.float32)
        self.b3 = np.zeros(output_dim, dtype=np.float32)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass.  x: (batch, input_dim) or (input_dim,).

        Activations are clamped to [-1e6, 1e6] to prevent float32 overflow
        when weights are still large during early training.
        """
        single = x.ndim == 1
        if single:
            x = x[np.newaxis, :]
        # Guard: sanitise any inf/nan from replay buffer or energy model
        np.nan_to_num(x, copy=False, nan=0.0, posinf=1.0, neginf=0.0)
        h1 = x @ self.W1
        h1 += self.b1
        np.maximum(h1, 0, out=h1)          # ReLU in-place
        np.clip(h1, 0, 1e6, out=h1)
        h2 = h1 @ self.W2
        h2 += self.b2
        np.maximum(h2, 0, out=h2)          # ReLU in-place
        np.clip(h2, 0, 1e6, out=h2)
        out = h2 @ self.W3
        out += self.b3
        np.clip(out, -1e6, 1e6, out=out)
        np.nan_to_num(out, copy=False, nan=0.0, posinf=1e6, neginf=-1e6)
        return out[0] if single else out

    def parameters(self):
        """Return list of (weight, bias) tuples."""
        return [(self.W1, self.b1), (self.W2, self.b2), (self.W3, self.b3)]

    def copy_from(self, other: '_NumpyMLP'):
        """Hard copy weights from another network."""
        self.W1[:] = other.W1
        self.b1[:] = other.b1
        self.W2[:] = other.W2
        self.b2[:] = other.b2
        self.W3[:] = other.W3
        self.b3[:] = other.b3

    def soft_update(self, other: '_NumpyMLP', tau: float):
        """Polyak averaging: θ_target ← τ·θ_online + (1-τ)·θ_target."""
        for (Ws, bs), (Wo, bo) in zip(self.parameters(), other.parameters()):
            Ws[:] = tau * Wo + (1 - tau) * Ws
            bs[:] = tau * bo + (1 - tau) * bs


# ═══════════════════════════════════════════════════════════════════
# Experience Replay Buffer
# ═══════════════════════════════════════════════════════════════════

class _ReplayBuffer:
    """Circular experience replay buffer."""

    def __init__(self, capacity: int, state_dim: int):
        self.capacity = capacity
        self.idx = 0
        self.size = 0
        self.states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.actions = np.zeros(capacity, dtype=np.int32)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=np.float32)

    def push(self, state, action, reward, next_state, done):
        self.states[self.idx] = state
        self.actions[self.idx] = action
        self.rewards[self.idx] = reward
        self.next_states[self.idx] = next_state
        self.dones[self.idx] = float(done)
        self.idx = (self.idx + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int, rng: np.random.Generator):
        idxs = rng.choice(self.size, size=batch_size, replace=False)
        return (self.states[idxs], self.actions[idxs], self.rewards[idxs],
                self.next_states[idxs], self.dones[idxs])


# ═══════════════════════════════════════════════════════════════════
# DQN Routing Agent
# ═══════════════════════════════════════════════════════════════════

class DQNRouter:
    """
    Deep Q-Network for autonomous carbon-aware next-hop routing.

    Learns online during simulation — no pre-training required.
    Uses a contextual value network: the state encodes both source
    context AND candidate features, and the network outputs a scalar
    value V(s) estimating the quality of choosing that candidate.

    Architecture: state(8) → 64 → 32 → 1  (contextual value estimator)

    This design handles the variable-size action space inherent in
    WSN routing (alive neighbours change each round) while maintaining
    stable Q-learning: the same (source, candidate) pair always maps
    to the same value, regardless of how many other candidates exist.
    """

    # State dimension: 9 features per (source, candidate) pair
    STATE_DIM = 9
    # Output dimension: 1 scalar value per candidate
    OUTPUT_DIM = 1

    def __init__(self, config, rng: np.random.Generator = None):
        self.rng = rng if rng is not None else np.random.default_rng(42)
        self.config = config

        # Hyperparameters
        self.gamma = 0.95           # discount factor
        self.lr = 1e-3              # learning rate (SGD)
        self.tau = 0.005            # soft-update rate
        self.batch_size = 64
        self.buffer_capacity = 10_000
        self.min_buffer = 256       # start learning after this many transitions
        self.epsilon = 1.0          # exploration rate
        self.epsilon_min = 0.05
        self.epsilon_decay_steps = 3000  # cosine annealing period
        self.train_every = 4            # train every Nth store call (speed vs quality)

        # Networks: output dimension = 1 (contextual value estimator)
        self._online = _NumpyMLP(self.STATE_DIM, 64, 32,
                                 self.OUTPUT_DIM, self.rng)
        self._target = _NumpyMLP(self.STATE_DIM, 64, 32,
                                 self.OUTPUT_DIM, self.rng)
        self._target.copy_from(self._online)

        # Replay buffer
        self._buffer = _ReplayBuffer(self.buffer_capacity, self.STATE_DIM)

        # Normalisation constants (derived from config)
        self._d_max = np.sqrt(config.area_width**2 + config.area_height**2
                              + (config.bs_y - config.area_height/2)**2)
        self._ci_min = config.ci_min
        self._ci_range = max(config.ci_max - config.ci_min, 1.0)
        self._e0 = config.initial_energy
        self._z_max = 1e4  # normalisation scale for carbon queue

        # Counters
        self._step = 0
        self._train_calls = 0
        self._total_loss = 0.0

    def reset(self):
        """Reset for a new experiment (keeps learned weights)."""
        self.epsilon = 1.0
        self._step = 0

    def full_reset(self):
        """Full reset including weights (for new seed)."""
        self.reset()
        self._online = _NumpyMLP(self.STATE_DIM, 64, 32,
                                 self.OUTPUT_DIM, self.rng)
        self._target = _NumpyMLP(self.STATE_DIM, 64, 32,
                                 self.OUTPUT_DIM, self.rng)
        self._target.copy_from(self._online)
        self._buffer = _ReplayBuffer(self.buffer_capacity, self.STATE_DIM)
        self._train_calls = 0
        self._total_loss = 0.0

    # ─── State Construction ───────────────────────────────────────

    def _build_state(self, source: Node, candidate, bs: tuple,
                     ci: float, z_queue: float,
                     alive_ratio: float,
                     lifecycle_factor: float = 1.0) -> np.ndarray:
        """
        Build normalised 9D state vector for a (source, candidate) pair.

        Features:
            0: source residual energy / E0
            1: source distance to BS / d_max
            2: normalised carbon intensity
            3: normalised carbon queue pressure
            4: network alive ratio
            5: candidate residual energy / E0  (0 if BS)
            6: candidate distance to BS / d_max  (0 if BS)
            7: hop distance / d_max
            8: candidate lifecycle penalty (0 = healthy, 1 = near-death)
        """
        s = np.zeros(self.STATE_DIM, dtype=np.float32)
        s[0] = source.energy / self._e0
        s[1] = source.distance_to(bs) / self._d_max
        s[2] = (ci - self._ci_min) / self._ci_range
        s[3] = min(z_queue / self._z_max, 1.0)
        s[4] = alive_ratio

        if candidate == 'BS':
            s[5] = 1.0   # BS has "infinite energy"
            s[6] = 0.0   # at BS
            s[7] = source.distance_to(bs) / self._d_max
        else:
            s[5] = candidate.energy / self._e0
            s[6] = candidate.distance_to(bs) / self._d_max
            s[7] = source.distance_to(candidate) / self._d_max

        # Feature 8: lifecycle penalty (normalised to [0, 1])
        # 0 = healthy node, 1 = near-death with high unamortised carbon
        s[8] = min((lifecycle_factor - 1.0) / 2.0, 1.0)

        return s

    # ─── Action Selection ─────────────────────────────────────────

    def select_next_hop(self, source: Node, candidate_chs: List[Node],
                        bs: tuple, ci: float, z_queue: float,
                        alive_ratio: float,
                        energy_model, packet_bits: int,
                        lifecycle_factor_fn=None) -> Union[Node, str]:
        """
        Select next hop using ε-greedy contextual value network.

        For each candidate k, builds state_k = features(source, candidate_k)
        and evaluates V(state_k) via the online network.  Selects
        argmax_k V(state_k) (exploitation) or random (exploration).

        This contextual architecture [Dulac-Arnold et al., 2015] ensures
        stable Q-learning with variable-size candidate sets: the same
        (source, candidate) state always maps to the same value.

        Parameters
        ----------
        source : Node
            Current transmitting node.
        candidate_chs : List[Node]
            Alive CHs that could serve as relay (already filtered by caller).
        bs : tuple
            Base station (x, y).
        ci : float
            Current carbon intensity.
        z_queue : float
            Current Lyapunov carbon queue value.
        alive_ratio : float
            Fraction of nodes alive in the network.
        energy_model : EnergyModel
            For energy cost estimation.
        packet_bits : int
            Packet size.

        Returns
        -------
        Node or 'BS'
            Selected next-hop.
        """
        source_dist_bs = source.distance_to(bs)

        # Build candidate list: [BS] + nearby CHs making progress
        candidates = ['BS'] if source_dist_bs <= self.config.tx_range else []
        for ch in candidate_chs:
            if (ch.id != source.id and ch.alive
                    and source.distance_to(ch) <= self.config.tx_range
                    and ch.distance_to(bs) < source_dist_bs):
                candidates.append(ch)
            if len(candidates) >= 20:
                break

        if not candidates:
            return 'BS'  # fallback

        # ε-greedy exploration
        if self.rng.random() < self.epsilon:
            idx = self.rng.integers(len(candidates))
        else:
            # Batch evaluate V(state_k) for ALL candidates at once
            n_cand = len(candidates)
            states_batch = np.zeros((n_cand, self.STATE_DIM), dtype=np.float32)
            for i, cand in enumerate(candidates):
                lf = 1.0
                if lifecycle_factor_fn is not None and cand != 'BS':
                    lf = lifecycle_factor_fn(cand)
                states_batch[i] = self._build_state(
                    source, cand, bs, ci, z_queue, alive_ratio,
                    lifecycle_factor=lf)
            v_vals = self._online.forward(states_batch).reshape(-1)
            idx = int(np.argmax(v_vals))

        return candidates[idx]

    # ─── Learning ─────────────────────────────────────────────────

    def store_transition(self, state: np.ndarray, action: int,
                         reward: float, next_state: np.ndarray,
                         done: bool):
        """Store a transition in the replay buffer."""
        self._buffer.push(state, action, reward, next_state, done)
        self._step += 1

        # Cosine annealing of ε
        progress = min(self._step / self.epsilon_decay_steps, 1.0)
        self.epsilon = self.epsilon_min + 0.5 * (1.0 - self.epsilon_min) * (
            1.0 + np.cos(np.pi * progress)
        )

    def train_step(self) -> float:
        """
        One gradient step of DQN with experience replay.

        Only trains every self.train_every calls to balance speed vs.
        learning quality. Skipping some steps is standard DQN practice
        (Mnih et al., 2015 used frame-skipping of 4).

        Returns
        -------
        float
            Mean TD loss for this batch (0.0 if skipped).
        """
        if self._buffer.size < self.min_buffer:
            return 0.0
        # Only train every Nth call
        if self._step % self.train_every != 0:
            return 0.0

        import warnings

        states, actions, rewards, next_states, dones = \
            self._buffer.sample(self.batch_size, self.rng)

        # Sanitise replay data
        states = np.nan_to_num(states, nan=0.0, posinf=1.0, neginf=0.0)
        next_states = np.nan_to_num(next_states, nan=0.0, posinf=1.0, neginf=0.0)

        # Forward pass with cached activations (avoids recomputation in backprop)
        h1 = np.maximum(0, states @ self._online.W1 + self._online.b1)
        np.clip(h1, 0, 1e6, out=h1)
        h2 = np.maximum(0, h1 @ self._online.W2 + self._online.b2)
        np.clip(h2, 0, 1e6, out=h2)
        v_current = (h2 @ self._online.W3 + self._online.b3).reshape(-1)

        # Target V(s') — Double DQN with scalar output
        v_next_target = self._target.forward(next_states).reshape(-1)

        # TD targets: y = r + γ·V_target(s') · (1 - done)
        targets = rewards + self.gamma * v_next_target * (1.0 - dones)

        # TD errors
        td_errors = targets - v_current
        np.nan_to_num(td_errors, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        loss = float(np.mean(td_errors ** 2))

        # ── Manual backpropagation (SGD) ──────────────────────────
        # loss = mean( (target - V(s))^2 )
        # ∂loss/∂V(s) = -2 · td_error / batch_size

        # Gradient for scalar output
        dV = (-2.0 * td_errors / self.batch_size).reshape(-1, 1)  # (batch, 1)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            # Backprop through layer 3: out = h2 @ W3 + b3
            # (h1 and h2 already computed in forward pass above)

            dW3 = h2.T @ dV
            db3 = dV.sum(axis=0)
            dh2 = dV @ self._online.W3.T

            # Backprop through ReLU + layer 2
            dh2 = dh2 * (h2 > 0).astype(np.float32)
            dW2 = h1.T @ dh2
            db2 = dh2.sum(axis=0)
            dh1 = dh2 @ self._online.W2.T

            # Backprop through ReLU + layer 1
            dh1 = dh1 * (h1 > 0).astype(np.float32)
            dW1 = states.T @ dh1
            db1 = dh1.sum(axis=0)

        # Gradient clipping (max norm = 1.0) + NaN guard
        grads = [dW1, db1, dW2, db2, dW3, db3]
        for g in grads:
            np.nan_to_num(g, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
            norm = np.linalg.norm(g)
            if norm > 1.0:
                g *= 1.0 / norm

        # SGD update
        self._online.W1 -= self.lr * dW1
        self._online.b1 -= self.lr * db1
        self._online.W2 -= self.lr * dW2
        self._online.b2 -= self.lr * db2
        self._online.W3 -= self.lr * dW3
        self._online.b3 -= self.lr * db3

        # Weight clipping to prevent numerical overflow in forward pass.
        # With normalised [0,1] inputs and small networks, weights beyond
        # ±5.0 indicate divergence.
        _WCLIP = 5.0
        for W, b in self._online.parameters():
            np.clip(W, -_WCLIP, _WCLIP, out=W)
            np.clip(b, -_WCLIP, _WCLIP, out=b)

        # Soft-update target network
        self._target.soft_update(self._online, self.tau)

        self._train_calls += 1
        self._total_loss += loss
        return loss

    def compute_reward(self, source: Node, selected, bs: tuple,
                       ci: float, energy_model, packet_bits: int,
                       delivered: bool, dropped: bool,
                       lifecycle_factor: float = 1.0) -> float:
        """
        Compute the scalar reward for a routing decision.

        Reward = progress_reward - carbon_penalty - energy_penalty
                 - lifecycle_penalty + delivery_bonus - drop_penalty
        """
        source_dist_bs = source.distance_to(bs)

        if selected == 'BS':
            progress = source_dist_bs
            e_tx = energy_model.tx_energy(packet_bits, source_dist_bs)
        else:
            progress = source_dist_bs - selected.distance_to(bs)
            d_hop = source.distance_to(selected)
            e_tx = energy_model.tx_energy(packet_bits, d_hop)

        ci_norm = (ci - self._ci_min) / self._ci_range

        r = 0.0
        r += 1.0 * (progress / self._d_max)            # delivery progress
        r -= 0.3 * ci_norm * (e_tx * 1e6 / 3.6e6)      # carbon cost
        r -= 0.3 * (e_tx / max(source.energy, 1e-10))   # energy fraction
        r -= 0.2 * max(0.0, lifecycle_factor - 1.0)      # lifecycle penalty
        if delivered:
            r += 5.0
        if dropped:
            r -= 2.0

        return float(np.clip(r, -10.0, 10.0))

    def get_diagnostics(self) -> dict:
        """Return training diagnostics."""
        return {
            'epsilon': self.epsilon,
            'buffer_size': self._buffer.size,
            'train_steps': self._train_calls,
            'avg_loss': (self._total_loss / max(self._train_calls, 1)),
        }
