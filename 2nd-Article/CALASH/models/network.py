"""
Wireless Sensor Network Model
==============================
Node deployment, topology management, and adjacency computation.

Deployment model:
    - Uniform random 2D distribution in a rectangular area (standard in
      WSN literature since LEACH [1]). Each node is placed independently
      at (x, y) ~ Uniform([0, W] x [0, H]).
    - Base station (BS) located outside the deployment area (at y = H + 50m)
      to model a realistic remote sink scenario.
    - All nodes are homogeneous: same initial energy E_0, same radio,
      same sensing capability.

Connectivity model:
    - Nodes within tx_range (default 100m) can communicate directly.
    - This unit-disc graph connectivity model is standard in WSN analysis
      [2] and matches the crossover distance d_0 ~ 87.7m of the
      Heinzelman radio model.

References
----------
[1] Heinzelman, W.B., Chandrakasan, A.P. & Balakrishnan, H.
    "An Application-Specific Protocol Architecture for Wireless
    Microsensor Networks." IEEE Trans. Wireless Comm., 1(4), 2002.
    DOI: 10.1109/TWC.2002.804190

[2] Gupta, P. & Kumar, P.R. "The Capacity of Wireless Networks."
    IEEE Trans. Information Theory, 46(2), pp. 388-404, 2000.
    DOI: 10.1109/18.825799
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class Node:
    """A single sensor node in the WSN."""
    id: int
    x: float
    y: float
    energy: float                    # current energy (Joules)
    initial_energy: float            # initial energy (Joules)
    alive: bool = True
    is_ch: bool = False              # is cluster head this round
    cluster_head_id: int = -1        # which CH this node belongs to (-1 = none)
    embodied_carbon: float = 10000.0  # manufacturing carbon (gCO2eq)
    packets_sent: int = 0            # total packets transmitted
    packets_received: int = 0         # packets received this round (CH only)
    rounds_as_ch: int = 0            # total rounds served as CH
    last_ch_round: int = -1          # last round this node was CH

    def distance_to(self, other) -> float:
        """Euclidean distance to another node or (x,y) tuple."""
        if isinstance(other, Node):
            dx = self.x - other.x
            dy = self.y - other.y
            return math.sqrt(dx * dx + dy * dy)
        else:
            # (x, y) tuple
            dx = self.x - other[0]
            dy = self.y - other[1]
            return math.sqrt(dx * dx + dy * dy)

    def energy_fraction(self) -> float:
        """Remaining energy as fraction of initial."""
        return max(0.0, self.energy / self.initial_energy)

    def consume_energy(self, amount: float) -> bool:
        """
        Consume energy. Returns True if node survives, False if it dies.

        Parameters
        ----------
        amount : float
            Energy to consume in Joules.

        Returns
        -------
        bool
            True if node is still alive after consumption.
        """
        self.energy -= amount
        if self.energy <= 0:
            self.energy = 0.0
            self.alive = False
            self.is_ch = False
            return False
        return True


class Network:
    """
    Wireless Sensor Network topology and state management.

    Handles node deployment, adjacency computation, and network state queries.
    """

    def __init__(self, config, rng: np.random.Generator = None):
        """
        Initialize network with random node deployment.

        Parameters
        ----------
        config : SimulationConfig
            Simulation parameters.
        rng : np.random.Generator, optional
            Random number generator for reproducibility.
        """
        self.config = config
        self.rng = rng if rng is not None else np.random.default_rng(42)
        self.bs = (config.bs_x, config.bs_y)
        self.nodes: List[Node] = []
        self.adjacency: Dict[int, List[int]] = {}

        self._deploy_nodes()
        self._build_distance_matrix()
        self._compute_adjacency()
        # ── Alive mask for fast neighbor lookups ──────────────────
        self._alive_mask = np.ones(self.config.num_nodes, dtype=bool)
        # ── Cluster membership cache (ch_id -> [member_ids]) ─────
        self._cluster_cache: Dict[int, List[int]] = {}

    def _deploy_nodes(self):
        """Randomly deploy sensor nodes in the monitoring area."""
        for i in range(self.config.num_nodes):
            x = self.rng.uniform(0, self.config.area_width)
            y = self.rng.uniform(0, self.config.area_height)
            node = Node(
                id=i,
                x=x,
                y=y,
                energy=self.config.initial_energy,
                initial_energy=self.config.initial_energy,
                embodied_carbon=self.config.embodied_carbon_per_node,
            )
            self.nodes.append(node)

    def _build_distance_matrix(self):
        """Pre-compute NxN distance matrix and BS distances (vectorized)."""
        n = self.config.num_nodes
        x = np.array([nd.x for nd in self.nodes])
        y = np.array([nd.y for nd in self.nodes])
        # Pairwise distances via broadcasting (N×N)
        dx = x[:, np.newaxis] - x[np.newaxis, :]
        dy = y[:, np.newaxis] - y[np.newaxis, :]
        self._dist_matrix = np.sqrt(dx * dx + dy * dy)  # (N, N)
        # Distance to BS for every node
        bx, by = self.config.bs_x, self.config.bs_y
        self._dist_to_bs = np.sqrt((x - bx) ** 2 + (y - by) ** 2)  # (N,)

    def dist(self, i: int, j: int) -> float:
        """Fast O(1) distance lookup between nodes i and j."""
        return float(self._dist_matrix[i, j])

    def dist_to_bs(self, i: int) -> float:
        """Fast O(1) distance from node i to BS."""
        return float(self._dist_to_bs[i])

    def _compute_adjacency(self):
        """Precompute neighbor lists using distance matrix."""
        self.adjacency = {i: [] for i in range(self.config.num_nodes)}
        tx = self.config.tx_range
        for i in range(self.config.num_nodes):
            for j in range(i + 1, self.config.num_nodes):
                if self._dist_matrix[i, j] <= tx:
                    self.adjacency[i].append(j)
                    self.adjacency[j].append(i)
        # Convert to numpy arrays for faster iteration
        self._adj_arrays: Dict[int, np.ndarray] = {
            i: np.array(nbrs, dtype=np.int32)
            for i, nbrs in self.adjacency.items()
        }

    def alive_nodes(self) -> List[Node]:
        """Return list of alive nodes."""
        return [n for n in self.nodes if n.alive]

    def alive_node_ids(self) -> List[int]:
        """Return IDs of alive nodes."""
        return [n.id for n in self.nodes if n.alive]

    def num_alive(self) -> int:
        """Count of alive nodes."""
        return sum(1 for n in self.nodes if n.alive)

    def cluster_heads(self) -> List[Node]:
        """Return list of current cluster heads."""
        return [n for n in self.nodes if n.alive and n.is_ch]

    def cluster_members(self, ch_id: int) -> List[Node]:
        """Return members of a specific cluster (excluding CH)."""
        # Use cache if available (built during form_clusters)
        if ch_id in self._cluster_cache:
            return [self.nodes[i] for i in self._cluster_cache[ch_id]]
        return [n for n in self.nodes if n.alive and not n.is_ch
                and n.cluster_head_id == ch_id]

    def build_cluster_cache(self):
        """Rebuild cluster membership cache (call after form_clusters)."""
        self._cluster_cache.clear()
        for n in self.nodes:
            if n.alive and not n.is_ch and n.cluster_head_id >= 0:
                self._cluster_cache.setdefault(n.cluster_head_id, []).append(n.id)

    def refresh_alive_mask(self):
        """Refresh alive mask from node state. Call at round start."""
        for i, n in enumerate(self.nodes):
            self._alive_mask[i] = n.alive

    def alive_neighbors(self, node_id: int) -> List[Node]:
        """Return alive neighbors of a node (uses cached mask)."""
        nbrs = self._adj_arrays[node_id]
        mask = self._alive_mask[nbrs]
        return [self.nodes[nbrs[k]] for k in range(len(nbrs)) if mask[k]]

    def distance_to_bs(self, node: Node) -> float:
        """Euclidean distance from a node to the base station."""
        return node.distance_to(self.bs)

    def reset_round_state(self):
        """Reset per-round state (CH flags, cluster assignments, received counts)."""
        for node in self.nodes:
            if node.alive:
                node.is_ch = False
                node.cluster_head_id = -1
                node.packets_received = 0

    def reset_network(self):
        """Fully reset network to initial state (for new experiment run)."""
        for node in self.nodes:
            node.energy = node.initial_energy
            node.alive = True
            node.is_ch = False
            node.cluster_head_id = -1
            node.packets_sent = 0
            node.packets_received = 0
            node.rounds_as_ch = 0
            node.last_ch_round = -1

    def redeploy(self, rng: np.random.Generator):
        """Redeploy nodes with new random positions (for new seed)."""
        self.rng = rng
        self.nodes.clear()
        self.adjacency.clear()
        self._deploy_nodes()
        self._build_distance_matrix()
        self._compute_adjacency()
        self._alive_mask = np.ones(self.config.num_nodes, dtype=bool)
        self._cluster_cache.clear()

    def get_node_positions(self) -> np.ndarray:
        """Return Nx2 array of node positions."""
        return np.array([[n.x, n.y] for n in self.nodes])

    def get_energy_map(self) -> np.ndarray:
        """Return array of residual energies (0 for dead nodes)."""
        return np.array([n.energy if n.alive else 0.0 for n in self.nodes])

    def get_alive_mask(self) -> np.ndarray:
        """Return boolean array of alive status."""
        return np.array([n.alive for n in self.nodes])
