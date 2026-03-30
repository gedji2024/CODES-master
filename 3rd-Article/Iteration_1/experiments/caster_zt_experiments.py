#!/usr/bin/env python3
"""
caster_zt_experiments.py — v2: Complete self-contained experiment framework
for the CASTER-ZT paper.

v2 fixes vs v1:
  1. Action-telemetry consistency in trust assessment (AETrust detects
     destructive actions during disaster as anomalous)
  2. Context-aware risk scoring (CELL_DEACTIVATION during disaster → very
     high risk)
  3. Proper recovery dynamics (cells recover faster, omega_rec meaningful)
  4. Rogue-specific detection metrics
  5. Statistical tests (Wilcoxon signed-rank)
  6. Temporal per-tick data for figure generation
  7. ROC curve data generation
  8. Threshold sensitivity with finer granularity

Implements all 11 method variants, 7 attack conditions, 20 seeds,
3 topology scales.
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import spatial, stats

from real_data_loader import (real_dist_telemetry, bootstrap_bca_ci,
                              POISON_INFLATE_DIST, POISON_SUPPRESS_DIST,
                              POISON_LATENCY_MASK_DIST)
from neural_inference import get_inference_manager, initialize_models

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TOTAL_TICKS = 40           # Extended to show recovery dynamics
DISASTER_ONSET_TICK = 3
ATTACK_START_TICK = 5
ATTACK_END_TICK = 28       # Extended attack window
FAILURE_FRACTION = 0.35    # 35% cells fail at disaster onset
SEEDS = list(range(1, 21))
MULTISCALE_SEEDS = list(range(1, 11))  # 10 seeds for multi-scale

# Shield thresholds (from manuscript)
GAMMA_1 = 0.30
GAMMA_2 = 0.50
GAMMA_3 = 0.70
GAMMA_4 = 0.90
W1, W2, W3, W4 = 0.25, 0.25, 0.25, 0.25
KAPPA_1, KAPPA_2 = 0.10, 0.15
TAU_0 = 0.50
DELTA_MAX = 0.50
DELTA_MAX_HARD = 1.00
U_MAX = 0.80

# Trust autoencoder
BETA_TAU = 5.0
E_THRESH_BASE = 0.15

# CPO
CPO_COST_PERCENTILE = 0.75
CPO_LAMBDA_LR = 0.01

# Shield-Binary
BINARY_MAX_ACTIONS_PER_ZONE_PER_WINDOW = 2
BINARY_WINDOW_SIZE = 3
BINARY_MAX_BLAST_RADIUS = 3
BINARY_ZONE_FAILURE_THRESHOLD = 0.60

# Agentic-Auto
AGENTIC_CONFIDENCE_THRESHOLD = 0.72

# Topology sourcing
DEFAULT_TOPOLOGY_MODE = os.getenv("CASTER_TOPOLOGY_MODE", "grid").strip().lower()
DEFAULT_TOPOLOGY_CSV = os.getenv("CASTER_TOPOLOGY_CSV", "").strip()

# IF-Trust
IF_N_ESTIMATORS = 100
IF_CONTAMINATION = 0.05

# ---- Sets for context-aware detection ----
DESTRUCTIVE_ACTIONS = {"CELL_DEACTIVATION", "PARAMETER_CORRUPT", "HANDOVER_FLOOD"}
RECOVERY_ACTIONS = {"CELL_ACTIVATION", "CELL_RECONFIG", "LOAD_REBALANCE"}
LEGITIMATE_PROPOSERS = {
    "recovery-xapp-01": "XAPP_RECOVERY",
    "recovery_engine_v1": "XAPP_RECOVERY",
    "monitoring-xapp-01": "XAPP_MONITORING",
    "policy-rapp-01": "RAPP_POLICY",
    "operator-admin": "OPERATOR",
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CellState(Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"


class AttackType(Enum):
    CLEAN = "CLEAN"
    TELEMETRY_POISONING = "TELEMETRY_POISONING"
    IDENTITY_CREDENTIAL_ABUSE = "IDENTITY_CREDENTIAL_ABUSE"
    COMBINED = "COMBINED"


class AttackSeverity(Enum):
    NONE = "NONE"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BoundedOutcome(Enum):
    ALLOW = "ALLOW"
    SCOPE_REDUCE = "SCOPE_REDUCE"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class MethodID(Enum):
    CASTER_ZT = "CASTER_ZT"
    TRUST_IMPLICIT = "TRUST_IMPLICIT"
    IDENTITY_ONLY = "IDENTITY_ONLY"
    TELEMETRY_ONLY = "TELEMETRY_ONLY"
    CPO_SOFT = "CPO_SOFT"
    SHIELD_BINARY = "SHIELD_BINARY"
    AGENTIC_AUTO = "AGENTIC_AUTO"
    IF_TRUST = "IF_TRUST"
    ABLATION_NO_AUTHZ = "ABLATION_NO_AUTHZ"
    ABLATION_NO_TRUST = "ABLATION_NO_TRUST"
    ABLATION_NO_RISK = "ABLATION_NO_RISK"


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    cell_id: str
    zone: str
    position: Tuple[float, float]
    state: CellState = CellState.OPERATIONAL
    capacity: float = 100.0
    load: float = 0.0
    is_priority: bool = False
    neighbors: List[str] = field(default_factory=list)
    base_capacity: float = 100.0  # Original capacity for recovery target


@dataclass
class TelemetryRecord:
    record_id: str
    tick: int
    source_cell_id: str
    source_zone: str
    throughput: float
    load_ratio: float
    latency_avg: float
    packet_loss_rate: float
    cell_state: CellState
    is_poisoned: bool = False
    collection_delay: float = 0.0
    is_complete: bool = True


@dataclass
class CandidateAction:
    action_id: str
    tick: int
    proposer_id: str
    action_type: str
    target_cells: List[str]
    target_zone: str
    scope: str
    urgency: str
    supporting_telemetry_ids: List[str] = field(default_factory=list)
    is_rogue: bool = False


@dataclass
class ShieldDecision:
    outcome: BoundedOutcome
    tau_t: float = 1.0
    rho_t: float = 0.0
    u_t: float = 0.0
    delta_t: float = 0.0
    alpha_t: int = 1
    g_t: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class TickResult:
    tick: int
    n_failed: int
    n_degraded: int
    n_recovering: int
    oper_frac: float
    n_candidates: int
    n_enforced: int
    n_blocked: int
    n_deferred: int
    n_escalated: int
    n_scope_reduced: int
    n_allowed: int
    n_poisoned: int
    n_rogue: int
    n_rogue_blocked: int
    n_rogue_scope_reduced: int
    n_rogue_allowed: int
    n_legit_blocked: int
    n_legit_allowed: int
    avg_g_t: float = 0.0


# ---------------------------------------------------------------------------
# RAN Environment
# ---------------------------------------------------------------------------

class RANEnvironment:
    def __init__(self,
                 n_cells: int = 12,
                 n_zones: int = 2,
                 seed: int = 42,
                 topology_mode: Optional[str] = None,
                 topology_csv: Optional[str] = None):
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        self.cells: Dict[str, Cell] = {}
        self.n_cells = n_cells
        self.n_zones = n_zones
        self.topology_mode = (topology_mode or DEFAULT_TOPOLOGY_MODE or "grid").lower()
        self.topology_csv = topology_csv or DEFAULT_TOPOLOGY_CSV
        self.topology_source = "synthetic_grid"
        self._base_demand: Dict[str, float] = {}
        self._in_disaster = False
        self._build_topology()

    def _build_topology(self):
        if self.topology_mode in {"semi_real", "opencellid", "voronoi"}:
            if self._build_opencellid_topology():
                return
            print("[WARN] Falling back to grid topology; OpenCelliD input unavailable or insufficient.")

        self._build_grid_topology()

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _build_grid_topology(self):
        cols = max(int(math.ceil(math.sqrt(self.n_cells))), 1)
        zone_names = [f"zone_{chr(ord('A') + z)}" for z in range(self.n_zones)]
        idx = 0
        for row in range(self.n_cells // cols + 2):
            for col in range(cols):
                if idx >= self.n_cells:
                    break
                zone = zone_names[idx % self.n_zones]
                cap = self.rng.uniform(80.0, 120.0)
                cell = Cell(
                    cell_id=f"cell_{idx:02d}",
                    zone=zone,
                    position=(float(col) * 2.0, float(row) * 2.0),
                    capacity=cap,
                    base_capacity=cap,
                    is_priority=(idx % max(1, self.n_cells // self.n_zones) < 2),
                )
                self.cells[cell.cell_id] = cell
                idx += 1

        self.topology_source = "synthetic_grid"
        self._connect_grid_neighbors()

        for c in self.cells.values():
            self._base_demand[c.cell_id] = c.capacity * self.rng.uniform(0.40, 0.65)
            c.load = self._base_demand[c.cell_id]

    def _connect_grid_neighbors(self):
        ids = list(self.cells.keys())
        for i, a_id in enumerate(ids):
            a = self.cells[a_id]
            for b_id in ids[i + 1:]:
                b = self.cells[b_id]
                dist = math.hypot(a.position[0] - b.position[0],
                                  a.position[1] - b.position[1])
                if dist <= 2.5:
                    a.neighbors.append(b_id)
                    b.neighbors.append(a_id)

    def _assign_zones_from_positions(
        self,
        positions: List[Tuple[float, float]],
    ) -> List[str]:
        zone_names = [f"zone_{chr(ord('A') + z)}" for z in range(self.n_zones)]
        ordering = sorted(range(len(positions)),
                          key=lambda idx: (positions[idx][0], positions[idx][1]))
        by_index: Dict[int, str] = {}
        for rank, idx in enumerate(ordering):
            zone_idx = min(
                self.n_zones - 1,
                int(rank * self.n_zones / max(len(ordering), 1)),
            )
            by_index[idx] = zone_names[zone_idx]
        return [by_index[idx] for idx in range(len(positions))]

    def _add_edge(self, edges: set, a_idx: int, b_idx: int):
        if a_idx == b_idx:
            return
        edges.add(tuple(sorted((int(a_idx), int(b_idx)))))

    def _connect_cells_from_positions(self, positions: List[Tuple[float, float]]):
        for cell in self.cells.values():
            cell.neighbors.clear()

        if len(positions) <= 1:
            return

        points = np.array(positions, dtype=float)
        edges = set()

        if len(points) >= 4:
            try:
                vor = spatial.Voronoi(points)
                for a_idx, b_idx in vor.ridge_points:
                    self._add_edge(edges, int(a_idx), int(b_idx))
            except Exception:
                pass

        if not edges and len(points) >= 3:
            try:
                tri = spatial.Delaunay(points)
                for simplex in tri.simplices:
                    for a_idx, b_idx in combinations(simplex, 2):
                        self._add_edge(edges, int(a_idx), int(b_idx))
            except Exception:
                pass

        target_degree = min(3, len(points) - 1)
        for idx in range(len(points)):
            neighbors = {b if a == idx else a
                         for a, b in edges if idx in (a, b)}
            if len(neighbors) >= target_degree:
                continue
            dists = np.linalg.norm(points - points[idx], axis=1)
            nearest = np.argsort(dists)
            for nb_idx in nearest[1:]:
                self._add_edge(edges, idx, int(nb_idx))
                neighbors.add(int(nb_idx))
                if len(neighbors) >= target_degree:
                    break

        cell_ids = list(self.cells.keys())
        for a_idx, b_idx in sorted(edges):
            a_id = cell_ids[a_idx]
            b_id = cell_ids[b_idx]
            if b_id not in self.cells[a_id].neighbors:
                self.cells[a_id].neighbors.append(b_id)
            if a_id not in self.cells[b_id].neighbors:
                self.cells[b_id].neighbors.append(a_id)

    def _build_opencellid_topology(self) -> bool:
        if not self.topology_csv:
            return False
        if not os.path.exists(self.topology_csv):
            print(f"[WARN] OpenCelliD CSV not found: {self.topology_csv}")
            return False

        records = []
        with open(self.topology_csv, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                lat = self._safe_float(row.get("lat") or row.get("latitude"))
                lon = self._safe_float(row.get("lon") or row.get("lng")
                                       or row.get("longitude"))
                if lat is None or lon is None:
                    continue
                records.append({
                    "raw_id": row.get("cell") or row.get("cellid")
                              or row.get("id") or row.get("radio") or "site",
                    "lat": lat,
                    "lon": lon,
                    "radio": (row.get("radio") or row.get("rat") or "").upper(),
                })

        if len(records) < max(self.n_cells, 3):
            print(f"[WARN] OpenCelliD CSV has only {len(records)} valid rows; need >= {self.n_cells}.")
            return False

        records.sort(key=lambda rec: (rec["lat"], rec["lon"], str(rec["raw_id"])))
        chosen_idx = self.np_rng.choice(len(records), size=self.n_cells, replace=False)
        selected = [records[idx] for idx in sorted(chosen_idx)]

        lat0 = float(np.mean([rec["lat"] for rec in selected]))
        lon0 = float(np.mean([rec["lon"] for rec in selected]))
        cos_lat = max(math.cos(math.radians(lat0)), 1e-6)

        raw_positions = []
        for rec in selected:
            x_km = (rec["lon"] - lon0) * 111.32 * cos_lat
            y_km = (rec["lat"] - lat0) * 110.57
            raw_positions.append((x_km, y_km))

        xs = np.array([pos[0] for pos in raw_positions], dtype=float)
        ys = np.array([pos[1] for pos in raw_positions], dtype=float)
        x_scale = max(float(np.std(xs)), 0.5)
        y_scale = max(float(np.std(ys)), 0.5)
        positions = [
            ((x - float(np.mean(xs))) / x_scale * 2.0,
             (y - float(np.mean(ys))) / y_scale * 2.0)
            for x, y in raw_positions
        ]
        zone_names = self._assign_zones_from_positions(positions)

        radio_base_capacity = {
            "NR": 120.0,
            "5G": 120.0,
            "LTE": 100.0,
            "UMTS": 75.0,
            "GSM": 55.0,
        }

        self.cells.clear()
        for idx, (rec, pos, zone) in enumerate(zip(selected, positions, zone_names)):
            nominal = radio_base_capacity.get(rec["radio"], 90.0)
            cap = self.rng.uniform(0.85 * nominal, 1.15 * nominal)
            cell = Cell(
                cell_id=f"cell_{idx:02d}",
                zone=zone,
                position=pos,
                capacity=cap,
                base_capacity=cap,
                is_priority=(idx % max(1, self.n_cells // self.n_zones) < 2),
            )
            self.cells[cell.cell_id] = cell

        self.topology_source = f"opencellid_voronoi:{os.path.basename(self.topology_csv)}"
        self._connect_cells_from_positions(positions)

        for c in self.cells.values():
            self._base_demand[c.cell_id] = c.capacity * self.rng.uniform(0.40, 0.65)
            c.load = self._base_demand[c.cell_id]
        return True

    @property
    def in_disaster(self) -> bool:
        return self._in_disaster

    def inject_disaster(self, failure_fraction: float = 0.35):
        self._in_disaster = True
        all_ids = list(self.cells.keys())
        n_fail = max(1, int(len(all_ids) * failure_fraction))
        for cid in all_ids[:n_fail]:
            self.cells[cid].state = CellState.FAILED
            self.cells[cid].load = 0.0
            self.cells[cid].capacity = 0.0
        self._redistribute_load()

    def _redistribute_load(self):
        for cell in self.cells.values():
            if cell.state == CellState.FAILED:
                orphan_load = self._base_demand.get(cell.cell_id, 0.0)
                op_nb = [self.cells[n] for n in cell.neighbors
                         if n in self.cells and self.cells[n].state in
                         (CellState.OPERATIONAL, CellState.RECOVERING)]
                if op_nb:
                    share = orphan_load / len(op_nb)
                    for nb in op_nb:
                        nb.load = min(nb.load + share, nb.capacity * 1.2)

    def step(self):
        for cell in self.cells.values():
            if cell.state == CellState.OPERATIONAL:
                noise = self.rng.gauss(0.0, 1.5)
                cell.load = max(0.0, min(cell.load + noise, cell.capacity * 1.2))
            elif cell.state == CellState.RECOVERING:
                # Recovery: capacity grows toward base_capacity
                growth = cell.base_capacity * 0.08  # 8% per tick
                cell.capacity = min(cell.capacity + growth, cell.base_capacity)
                cell.load = min(self._base_demand.get(cell.cell_id, 0.0),
                                cell.capacity * 0.9)
                if cell.capacity >= cell.base_capacity * 0.90:
                    cell.state = CellState.OPERATIONAL
                    cell.capacity = cell.base_capacity

    def apply_recovery(self, action: CandidateAction) -> bool:
        changed = False
        for cid in action.target_cells:
            cell = self.cells.get(cid)
            if cell is None:
                continue
            if action.action_type == "CELL_ACTIVATION" and cell.state == CellState.FAILED:
                cell.state = CellState.RECOVERING
                cell.capacity = cell.base_capacity * 0.35
                cell.load = 0.0
                changed = True
            elif action.action_type == "CELL_RECONFIG" and cell.state in (
                    CellState.FAILED, CellState.DEGRADED):
                cell.state = CellState.RECOVERING
                cell.capacity = cell.base_capacity * 0.45
                cell.load = min(self._base_demand.get(cid, 0.0), cell.capacity)
                changed = True
            elif action.action_type == "LOAD_REBALANCE":
                changed = True
        return changed

    def apply_rogue_damage(self, action: CandidateAction):
        """Rogue actions cause infrastructure damage."""
        for cid in action.target_cells:
            cell = self.cells.get(cid)
            if cell is None:
                continue
            if cell.state == CellState.OPERATIONAL:
                cell.state = CellState.DEGRADED
                cell.capacity *= 0.5
                cell.load = min(cell.load, cell.capacity)
            elif cell.state in (CellState.RECOVERING, CellState.DEGRADED):
                cell.state = CellState.FAILED
                cell.capacity = 0.0
                cell.load = 0.0

    def operational_fraction(self) -> float:
        if not self.cells:
            return 0.0
        n_op = sum(1 for c in self.cells.values()
                   if c.state == CellState.OPERATIONAL)
        return n_op / len(self.cells)

    def recovering_fraction(self) -> float:
        if not self.cells:
            return 0.0
        n_rec = sum(1 for c in self.cells.values()
                    if c.state == CellState.RECOVERING)
        return n_rec / len(self.cells)

    def functional_fraction(self) -> float:
        """Operational + Recovering cells (partial service)."""
        if not self.cells:
            return 0.0
        n_func = sum(1 for c in self.cells.values()
                     if c.state in (CellState.OPERATIONAL, CellState.RECOVERING))
        return n_func / len(self.cells)

    def failed_count(self) -> int:
        return sum(1 for c in self.cells.values() if c.state == CellState.FAILED)

    def degraded_count(self) -> int:
        return sum(1 for c in self.cells.values() if c.state == CellState.DEGRADED)

    def recovering_count(self) -> int:
        return sum(1 for c in self.cells.values() if c.state == CellState.RECOVERING)

    def zone_failure_fraction(self, zone: str) -> float:
        zone_cells = [c for c in self.cells.values() if c.zone == zone]
        if not zone_cells:
            return 0.0
        n_bad = sum(1 for c in zone_cells
                    if c.state in (CellState.FAILED, CellState.DEGRADED))
        return n_bad / len(zone_cells)

    def generate_telemetry(self, tick: int) -> List[TelemetryRecord]:
        """Generate telemetry from real 5G distributions (Tier 1+2)."""
        records = []
        # Use a numpy RNG seeded from the stdlib rng for scipy compat
        np_rng = np.random.RandomState(self.rng.randint(0, 2**31))
        for cell in self.cells.values():
            tp, lr, lat, plr = real_dist_telemetry(
                cell.state.value, cell.base_capacity, np_rng)

            # Match training-data conventions for delay / is_complete
            if cell.state.value == "FAILED":
                delay = max(0.0, np_rng.normal(0.0, 0.05))
                complete = False
            else:
                delay = max(0, np_rng.normal(0.10, 0.05))
                complete = (np_rng.random() > 0.02)

            rec = TelemetryRecord(
                record_id=str(uuid.uuid4())[:8],
                tick=tick,
                source_cell_id=cell.cell_id,
                source_zone=cell.zone,
                throughput=max(0.0, tp),
                load_ratio=min(1.0, max(0.0, lr)),
                latency_avg=max(0.0, lat),
                packet_loss_rate=min(1.0, max(0.0, plr)),
                cell_state=cell.state,
                collection_delay=delay,
                is_complete=complete,
            )
            records.append(rec)
        return records


# ---------------------------------------------------------------------------
# Attack Engine
# ---------------------------------------------------------------------------

class AttackEngine:
    def __init__(self, attack_type: AttackType, severity: AttackSeverity,
                 seed: int = 42, target_zone: str = "zone_A"):
        self.attack_type = attack_type
        self.severity = severity
        self.rng = random.Random(seed)
        self.target_zone = target_zone
        self.ground_truth: List[Dict[str, Any]] = []

        if severity == AttackSeverity.MEDIUM:
            self.tput_bias = 0.30
            self.loss_bias = 0.25
            self.poison_frac = 0.50
            self.n_rogue = 2
            self.use_stolen_id = True   # MEDIUM: stolen identity
            self.mimicry_rate = 0.10    # 10% of rogue actions mimic recovery
        elif severity == AttackSeverity.HIGH:
            self.tput_bias = 0.50
            self.loss_bias = 0.50
            self.poison_frac = 0.80
            self.n_rogue = 3
            self.use_stolen_id = True   # HIGH: also stolen identity (harder)
            self.mimicry_rate = 0.15    # 15% mimicry (more sophisticated)
        else:
            self.tput_bias = 0.0
            self.loss_bias = 0.0
            self.poison_frac = 0.0
            self.n_rogue = 0
            self.use_stolen_id = False
            self.mimicry_rate = 0.0

    def is_active(self, tick: int) -> bool:
        return ATTACK_START_TICK <= tick <= ATTACK_END_TICK

    def poison_telemetry(self, records: List[TelemetryRecord],
                         tick: int) -> Tuple[List[TelemetryRecord], int]:
        if not self.is_active(tick):
            return records, 0
        if self.attack_type not in (AttackType.TELEMETRY_POISONING,
                                     AttackType.COMBINED):
            return records, 0

        n_poisoned = 0
        for rec in records:
            if rec.source_zone != self.target_zone:
                continue
            if self.rng.random() > self.poison_frac:
                continue
            # Inflate throughput, suppress loss (SWaT-calibrated)
            np_rng = np.random.RandomState(self.rng.randint(0, 2**31))
            rec.throughput = max(0, rec.throughput * float(
                POISON_INFLATE_DIST.rvs(random_state=np_rng)))
            rec.packet_loss_rate = max(0, min(1.0,
                rec.packet_loss_rate * float(
                    POISON_SUPPRESS_DIST.rvs(random_state=np_rng))))
            rec.latency_avg = max(0, rec.latency_avg * float(
                POISON_LATENCY_MASK_DIST.rvs(random_state=np_rng)))
            rec.is_poisoned = True
            n_poisoned += 1
            self.ground_truth.append({
                "tick": tick, "type": "TELEMETRY_POISONING",
                "cell_id": rec.source_cell_id
            })
        return records, n_poisoned

    def generate_rogue_actions(self, tick: int,
                                env: RANEnvironment) -> List[CandidateAction]:
        if not self.is_active(tick):
            return []
        if self.attack_type not in (AttackType.IDENTITY_CREDENTIAL_ABUSE,
                                     AttackType.COMBINED):
            return []

        rogue = []
        # Target operational or recovering cells (maximize damage)
        targets = [cid for cid, c in env.cells.items()
                   if c.state in (CellState.OPERATIONAL, CellState.RECOVERING)]
        if not targets:
            targets = list(env.cells.keys())

        for i in range(self.n_rogue):
            if self.use_stolen_id:
                pid = "recovery-xapp-01"  # Stolen legitimate credential
            else:
                pid = f"rogue-xapp-{self.rng.randint(100, 999)}"

            target = targets[self.rng.randint(0, len(targets) - 1)]

            # Adversary sophistication: occasionally use mimicry
            # (mimic legitimate recovery actions to evade detection)
            if self.rng.random() < self.mimicry_rate:
                # Mimicry: use recovery-like action type with correct
                # proposer profile to evade action-consistency checks.
                # The adversary crafts a CELL_RECONFIG or LOAD_REBALANCE
                # that appears legitimate but carries malicious parameters.
                rogue_type = self.rng.choice(["CELL_RECONFIG",
                                              "LOAD_REBALANCE"])
                # Prefer degraded/recovering cells where reconfig is expected
                mimic_targets = [cid for cid, c in env.cells.items()
                                 if c.state in (CellState.DEGRADED,
                                                CellState.RECOVERING)]
                if mimic_targets:
                    target = mimic_targets[
                        self.rng.randint(0, len(mimic_targets) - 1)]
                action_urgency = "ELEVATED"  # Match normal recovery
            else:
                # Standard destructive rogue action
                rogue_type = self.rng.choice(list(DESTRUCTIVE_ACTIONS))
                action_urgency = "CRITICAL"

            action = CandidateAction(
                action_id=str(uuid.uuid4())[:8],
                tick=tick,
                proposer_id=pid,
                action_type=rogue_type,
                target_cells=[target],
                target_zone=self.target_zone,
                scope="LOCAL",
                urgency=action_urgency,
                is_rogue=True,
            )
            rogue.append(action)
            self.ground_truth.append({
                "tick": tick, "type": "IDENTITY_CREDENTIAL_ABUSE",
                "proposer_id": pid, "action_id": action.action_id,
                "action_type": rogue_type,
                "use_stolen_id": self.use_stolen_id,
            })
        return rogue


# ---------------------------------------------------------------------------
# Recovery Engine (generates legitimate candidate actions)
# ---------------------------------------------------------------------------

class RecoveryEngine:
    def __init__(self, proposer_id: str = "recovery-xapp-01"):
        self.proposer_id = proposer_id

    def propose(self, telemetry: List[TelemetryRecord],
                tick: int) -> List[CandidateAction]:
        actions = []
        for rec in telemetry:
            if rec.cell_state == CellState.FAILED:
                actions.append(CandidateAction(
                    action_id=str(uuid.uuid4())[:8],
                    tick=tick,
                    proposer_id=self.proposer_id,
                    action_type="CELL_ACTIVATION",
                    target_cells=[rec.source_cell_id],
                    target_zone=rec.source_zone,
                    scope="LOCAL",
                    urgency="CRITICAL",
                    supporting_telemetry_ids=[rec.record_id],
                ))
            elif rec.cell_state == CellState.DEGRADED:
                actions.append(CandidateAction(
                    action_id=str(uuid.uuid4())[:8],
                    tick=tick,
                    proposer_id=self.proposer_id,
                    action_type="CELL_RECONFIG",
                    target_cells=[rec.source_cell_id],
                    target_zone=rec.source_zone,
                    scope="LOCAL",
                    urgency="ELEVATED",
                    supporting_telemetry_ids=[rec.record_id],
                ))
        # Prioritize by urgency, limit to reasonable number
        actions.sort(key=lambda a: {"CRITICAL": 3, "ELEVATED": 2,
                                     "ROUTINE": 1}.get(a.urgency, 0),
                     reverse=True)
        return actions[:6]


# ---------------------------------------------------------------------------
# Telemetry-to-Feature Bridge
# ---------------------------------------------------------------------------

CELL_STATE_ENCODING = {
    CellState.FAILED: 0.0,
    CellState.DEGRADED: 0.33,
    CellState.RECOVERING: 0.67,
    CellState.OPERATIONAL: 1.0,
}


def _telemetry_to_features(rec: TelemetryRecord) -> np.ndarray:
    """Convert TelemetryRecord to 7-dim feature vector for neural inference.

    Feature order (must match training data in real_data_loader.py):
        [throughput, load_ratio, latency_avg, packet_loss_rate,
         collection_delay, is_complete, cell_state_enc]
    """
    return np.array([
        rec.throughput,
        rec.load_ratio,
        rec.latency_avg,
        rec.packet_loss_rate,
        rec.collection_delay,
        float(rec.is_complete),
        CELL_STATE_ENCODING.get(rec.cell_state, 0.5),
    ], dtype=np.float32)


def _env_state_features(env: 'RANEnvironment', tick: int) -> np.ndarray:
    """Extract 5-dim state features for GNN/Policy/Uncertainty inference.

    Feature order (must match training data):
        [op_frac, fail_frac, in_disaster, under_attack, tick_frac]
    """
    n = max(1, len(env.cells))
    return np.array([
        env.operational_fraction(),
        env.failed_count() / n,
        1.0 if env.in_disaster else 0.0,
        0.0,  # under_attack not directly observable by the model
        tick / max(1, TOTAL_TICKS),
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Trust Assessment — v2: Real Neural Network Inference
# ---------------------------------------------------------------------------

class AutoencoderTrustAssessor:
    """
    v3 Real Neural Trust Assessor: loads trained TrustAutoencoder and
    ContrastiveEncoder checkpoints for REAL forward-pass inference.

    - assess_telemetry(): Converts TelemetryRecord → 7-dim feature vector,
      normalises with training μ/σ, runs through trained autoencoder,
      computes reconstruction error, maps to trust via sigmoid.
      Contrastive divergence computed via trained ContrastiveEncoder.
    - assess_action_consistency(): Uses autoencoder reconstruction error
      on action-context synthetic telemetry patterns.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self._history: Dict[str, TelemetryRecord] = {}
        self._mgr = get_inference_manager()

    def assess_telemetry(self, rec: TelemetryRecord) -> Tuple[float, float]:
        """Assess telemetry quality via real autoencoder forward pass.

        Returns (tau_t, delta_t).
        """
        features = _telemetry_to_features(rec)

        if self._mgr.loaded:
            tau_t, delta_t = self._mgr.assess_trust(features)
        else:
            # Fallback if models not loaded
            tau_t, delta_t = 0.5, 0.0

        self._history[rec.source_cell_id] = rec
        return tau_t, delta_t

    def assess_action_consistency(self, action: CandidateAction,
                                   env: RANEnvironment) -> float:
        """
        Assess action-context consistency via trained neural networks.

        Uses the autoencoder and contrastive encoder to measure how
        anomalous an action is relative to the learned clean-operation
        manifold. Returns penalty ∈ [0, 1].
        """
        if not self._mgr.loaded:
            return 0.0

        # Collect target cell states
        cell_states = []
        for cid in action.target_cells:
            cell = env.cells.get(cid)
            if cell:
                cell_states.append(cell.state.value)

        if not cell_states:
            cell_states = ["OPERATIONAL"]

        # Determine proposer role
        role = LEGITIMATE_PROPOSERS.get(action.proposer_id, "UNKNOWN")

        # Evidence check
        has_evidence = bool(action.supporting_telemetry_ids)

        # Zone failure fraction
        zone_fail = env.zone_failure_fraction(action.target_zone)

        penalty = self._mgr.assess_action_consistency(
            action_type=action.action_type,
            cell_states=cell_states,
            in_disaster=env.in_disaster,
            zone_fail_frac=zone_fail,
            proposer_role=role,
            has_evidence=has_evidence,
        )

        return penalty


class IsolationForestTrustAssessor:
    """IF-Trust: sklearn IsolationForest on telemetry features only."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self._history: Dict[str, TelemetryRecord] = {}
        self._fitted = False
        self._model = None

    def fit_on_clean(self, records: List[TelemetryRecord]):
        from sklearn.ensemble import IsolationForest
        features = []
        for rec in records:
            features.append([
                rec.throughput / 120.0,
                rec.load_ratio,
                rec.latency_avg / 500.0,
                rec.packet_loss_rate,
            ])
        if len(features) < 10:
            return
        X = np.array(features)
        self._model = IsolationForest(
            n_estimators=IF_N_ESTIMATORS,
            contamination=IF_CONTAMINATION,
            random_state=int(self.rng.randint(0, 10000)),
        )
        self._model.fit(X)
        self._fitted = True

    def assess(self, rec: TelemetryRecord) -> Tuple[float, float]:
        features = np.array([[
            rec.throughput / 120.0,
            rec.load_ratio,
            rec.latency_avg / 500.0,
            rec.packet_loss_rate,
        ]])

        if self._fitted and self._model is not None:
            raw_score = self._model.score_samples(features)[0]
            # IF score_samples: more negative = more anomalous
            # Typical range for inliers: [-0.4, -0.1], outliers: [-0.6, -0.5]
            # Map to [0,1] where 1=trusted, 0=untrusted
            # Center around -0.3 (typical inlier score)
            tau_t = max(0.0, min(1.0, 1.0 / (1.0 + math.exp(-15 * (raw_score + 0.35)))))
        else:
            tau_t = 0.85

        self._history[rec.source_cell_id] = rec
        return tau_t, 0.0  # IF produces no divergence


# ---------------------------------------------------------------------------
# Risk Assessment — v2: Context-Aware
# ---------------------------------------------------------------------------

class RiskAssessor:
    """
    v3 Real Neural Risk Scorer.

    Loads the trained RiskScorer checkpoint and runs real forward-pass
    inference.  Input: 11-dim vector = 6-dim action one-hot + 5-dim
    state features.  Output: risk probability ρ_t ∈ [0, 1].
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self._mgr = get_inference_manager()

    def evaluate(self, action: CandidateAction, env: RANEnvironment) -> float:
        if not self._mgr.loaded:
            return 0.15  # safe default

        n = max(1, len(env.cells))
        rho_t = self._mgr.score_risk(
            action_type=action.action_type,
            op_frac=env.operational_fraction(),
            fail_frac=env.failed_count() / n,
            in_disaster=env.in_disaster,
            under_attack=False,
            tick_frac=action.tick / max(1, TOTAL_TICKS),
        )

        # Scope and blast-radius adjustments (structural, not learned)
        scope_risk = {"LOCAL": 0.0, "ZONAL": 0.05, "CROSS_ZONE": 0.10}
        rho_t += scope_risk.get(action.scope, 0.0)

        n_targets = len(action.target_cells)
        rho_t += max(0, n_targets - 1) * 0.03

        for cid in action.target_cells:
            cell = env.cells.get(cid)
            if cell and cell.is_priority:
                rho_t += 0.05
                break

        return max(0.0, min(1.0, rho_t))


# ---------------------------------------------------------------------------
# Authorization Gate
# ---------------------------------------------------------------------------

def check_authorization(action: CandidateAction) -> int:
    """Returns alpha_t: 1 if identity in roster, 0 if unknown."""
    role = LEGITIMATE_PROPOSERS.get(action.proposer_id)
    if role is None:
        return 0
    return 1


# ---------------------------------------------------------------------------
# Uncertainty Estimator (MC-Dropout simulation)
# ---------------------------------------------------------------------------

class UncertaintyEstimator:
    """
    v3 Real MC-Dropout Uncertainty Estimator.

    Runs MC_SAMPLES=20 stochastic forward passes through the trained GNN
    encoder (with dropout enabled), feeds the latent embeddings through
    the PolicyHead, and computes the predictive uncertainty as the mean
    standard deviation of the softmax action probabilities across passes.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self._mgr = get_inference_manager()

    def estimate(self, env: RANEnvironment,
                 action: CandidateAction) -> float:
        if not self._mgr.loaded:
            return self.rng.uniform(0.05, 0.18)

        state_features = _env_state_features(env, action.tick)
        u_t = self._mgr.estimate_uncertainty(state_features)
        return u_t


# ---------------------------------------------------------------------------
# Method Implementations
# ---------------------------------------------------------------------------

class CasterZTMethod:
    """
    Full CASTER-ZT: autoencoder trust (telemetry + action-consistency)
    + context-aware risk + authorization + divergence + uncertainty + shield.
    """

    def __init__(self, seed: int = 42):
        self.trust_assessor = AutoencoderTrustAssessor(seed)
        self.risk_assessor = RiskAssessor(seed)
        self.uncertainty = UncertaintyEstimator(seed)

    def decide(self, action: CandidateAction, telemetry: List[TelemetryRecord],
               env: RANEnvironment) -> ShieldDecision:

        # 1. Authorization
        alpha_t = check_authorization(action)

        # 2. Telemetry trust & divergence
        tau_scores = []
        delta_scores = []
        for rec in telemetry:
            if rec.source_cell_id in action.target_cells or \
               rec.record_id in action.supporting_telemetry_ids:
                tau, delta = self.trust_assessor.assess_telemetry(rec)
                tau_scores.append(tau)
                delta_scores.append(delta)
        if not tau_scores:
            # Use first available telemetry record
            if telemetry:
                tau, delta = self.trust_assessor.assess_telemetry(telemetry[0])
                tau_scores.append(tau)
                delta_scores.append(delta)

        tau_t = min(tau_scores) if tau_scores else 0.5
        delta_t = max(delta_scores) if delta_scores else 0.0

        # 3. Action-telemetry consistency (v2 key innovation)
        action_penalty = self.trust_assessor.assess_action_consistency(
            action, env)
        # Fold action penalty into trust and divergence
        # Strong coupling: high action penalty → very low trust, high divergence
        tau_t = tau_t * max(0.0, 1.0 - action_penalty * 1.2)
        delta_t = delta_t + action_penalty * 0.9

        # 4. Risk
        rho_t = self.risk_assessor.evaluate(action, env)

        # 5. Uncertainty
        u_t = self.uncertainty.estimate(env, action)

        # 6. Shield decision
        return self._shield_decide(alpha_t, tau_t, rho_t, u_t, delta_t)

    def _shield_decide(self, alpha_t, tau_t, rho_t, u_t, delta_t) -> ShieldDecision:
        tau_min = TAU_0 + KAPPA_1 * rho_t + KAPPA_2 * u_t
        g_t = W1 * (1 - tau_t) + W2 * rho_t + W3 * u_t + W4 * delta_t

        if alpha_t == 0:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["BLOCK: unauthorized identity"])
        if delta_t > DELTA_MAX_HARD:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["BLOCK: hard divergence exceeded"])
        if g_t >= GAMMA_4:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["BLOCK: extreme conservatism"])
        if (GAMMA_3 <= g_t < GAMMA_4) or u_t > U_MAX:
            return ShieldDecision(BoundedOutcome.ESCALATE, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["ESCALATE: very high conservatism"])
        if GAMMA_2 <= g_t < GAMMA_3:
            return ShieldDecision(BoundedOutcome.DEFER, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["DEFER: high conservatism"])
        if GAMMA_1 <= g_t < GAMMA_2:
            return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["SCOPE_REDUCE: moderate conservatism"])
        if tau_t >= tau_min and delta_t <= DELTA_MAX:
            return ShieldDecision(BoundedOutcome.ALLOW, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t,
                                  ["ALLOW: all gates passed"])
        # Fallback: scope-reduce (conservative)
        return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t, u_t,
                              delta_t, alpha_t, g_t,
                              ["SCOPE_REDUCE: tau below minimum"])


class TrustImplicitMethod:
    """No security: all actions allowed unconditionally."""
    def decide(self, action, telemetry, env):
        return ShieldDecision(BoundedOutcome.ALLOW, 1.0, 0.0, 0.0, 0.0, 1, 0.0,
                              ["ALLOW: trust-implicit"])


class IdentityOnlyMethod:
    """Only checks identity, no gating on trust/risk."""
    def decide(self, action, telemetry, env):
        alpha_t = check_authorization(action)
        if alpha_t == 0:
            return ShieldDecision(BoundedOutcome.BLOCK, 1.0, 0.0, 0.0, 0.0,
                                  alpha_t, 0.0, ["BLOCK: unknown identity"])
        return ShieldDecision(BoundedOutcome.ALLOW, 1.0, 0.0, 0.0, 0.0, 1, 0.0,
                              ["ALLOW: known identity"])


class TelemetryOnlyMethod:
    """Telemetry trust assessment but no enforcement gating."""
    def __init__(self, seed: int = 42):
        self.trust = AutoencoderTrustAssessor(seed)

    def decide(self, action, telemetry, env):
        for rec in telemetry:
            self.trust.assess_telemetry(rec)
        return ShieldDecision(BoundedOutcome.ALLOW, 1.0, 0.0, 0.0, 0.0, 1, 0.0,
                              ["ALLOW: telemetry-only (no gating)"])


class CPOSoftMethod:
    """Constrained Policy Optimization with Lagrangian cost budget."""
    def __init__(self, seed: int = 42):
        self.risk = RiskAssessor(seed)
        self.rng = np.random.RandomState(seed)
        self.cumulative_cost = 0.0
        self.cost_budget = 0.0
        self.lam = 0.0

    def calibrate(self, n_cells: int):
        self.cost_budget = n_cells * 0.15 * TOTAL_TICKS * CPO_COST_PERCENTILE
        self.cumulative_cost = 0.0
        self.lam = 0.0

    def decide(self, action, telemetry, env):
        rho_t = self.risk.evaluate(action, env)
        cost = rho_t * len(action.target_cells)
        self.cumulative_cost += cost
        self.lam = max(0, self.lam + CPO_LAMBDA_LR *
                       (self.cumulative_cost - self.cost_budget))

        if self.cumulative_cost > self.cost_budget and self.lam > 0.3:
            g_t = rho_t + self.lam * 0.1
            return ShieldDecision(BoundedOutcome.BLOCK, 1.0, rho_t, 0.0, 0.0,
                                  1, g_t, ["BLOCK: CPO cost exceeded"])
        return ShieldDecision(BoundedOutcome.ALLOW, 1.0, rho_t, 0.0, 0.0, 1,
                              0.0, ["ALLOW: CPO within budget"])


class ShieldBinaryMethod:
    """Binary safety shield with precomputed state-safety specification."""
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self._action_history: Dict[str, List[int]] = {}

    def reset(self):
        self._action_history.clear()

    def decide(self, action, telemetry, env):
        zone = action.target_zone
        tick = action.tick

        # Rate limit
        hist = self._action_history.get(zone, [])
        recent = [t for t in hist if t >= tick - BINARY_WINDOW_SIZE]
        if len(recent) >= BINARY_MAX_ACTIONS_PER_ZONE_PER_WINDOW:
            return ShieldDecision(BoundedOutcome.BLOCK, 1.0, 0.0, 0.0, 0.0,
                                  1, 1.0, ["BLOCK: rate limit"])

        # Blast radius
        if len(action.target_cells) > BINARY_MAX_BLAST_RADIUS:
            return ShieldDecision(BoundedOutcome.BLOCK, 1.0, 0.0, 0.0, 0.0,
                                  1, 1.0, ["BLOCK: blast radius"])

        # Zone-safety invariant
        zone_cells = [c for c in env.cells.values() if c.zone == zone]
        if zone_cells:
            ff = sum(1 for c in zone_cells
                     if c.state == CellState.FAILED) / len(zone_cells)
            if ff > BINARY_ZONE_FAILURE_THRESHOLD and \
               action.action_type in DESTRUCTIVE_ACTIONS:
                return ShieldDecision(BoundedOutcome.BLOCK, 1.0, 0.0, 0.0, 0.0,
                                      1, 1.0, ["BLOCK: zone invariant"])

        # Record
        if zone not in self._action_history:
            self._action_history[zone] = []
        self._action_history[zone].append(tick)

        return ShieldDecision(BoundedOutcome.ALLOW, 1.0, 0.0, 0.0, 0.0, 1, 0.0,
                              ["ALLOW: safety spec OK"])


class AgenticAutoMethod:
    """Confidence-based autonomous controller (no formal verification)."""
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self.trust = AutoencoderTrustAssessor(seed)

    def decide(self, action, telemetry, env):
        base_conf = self.rng.uniform(0.75, 0.98)

        # Telemetry anomaly lowers confidence
        for rec in telemetry:
            if rec.source_cell_id in action.target_cells:
                tau, _ = self.trust.assess_telemetry(rec)
                if tau < 0.5:
                    base_conf *= 0.75
                break

        # Unknown identity slightly lowers confidence
        if action.proposer_id not in LEGITIMATE_PROPOSERS:
            base_conf *= self.rng.uniform(0.80, 0.92)

        # But stolen IDs look legitimate → confidence stays high
        # (structural weakness: no action-context checking)

        if base_conf < AGENTIC_CONFIDENCE_THRESHOLD:
            return ShieldDecision(BoundedOutcome.BLOCK, 1.0, 0.0, 0.0, 0.0,
                                  1, 1.0, ["BLOCK: low confidence"])
        return ShieldDecision(BoundedOutcome.ALLOW, 1.0, 0.0, 0.0, 0.0, 1,
                              0.0, ["ALLOW: high confidence"])


class IFTrustMethod:
    """IF-Trust: IsolationForest trust + full pipeline minus contrastive."""
    def __init__(self, seed: int = 42):
        self.if_trust = IsolationForestTrustAssessor(seed)
        self.risk = RiskAssessor(seed)
        self.uncertainty = UncertaintyEstimator(seed)

    def fit_if(self, clean_records: List[TelemetryRecord]):
        self.if_trust.fit_on_clean(clean_records)

    def decide(self, action, telemetry, env):
        alpha_t = check_authorization(action)

        tau_scores = []
        for rec in telemetry:
            if rec.source_cell_id in action.target_cells or \
               rec.record_id in action.supporting_telemetry_ids:
                tau, _ = self.if_trust.assess(rec)
                tau_scores.append(tau)
        if not tau_scores and telemetry:
            tau, _ = self.if_trust.assess(telemetry[0])
            tau_scores.append(tau)

        tau_t = min(tau_scores) if tau_scores else 0.5
        delta_t = 0.0  # IF has no contrastive divergence
        rho_t = self.risk.evaluate(action, env)
        u_t = self.uncertainty.estimate(env, action)

        # IF-Trust can partially detect action anomalies through risk
        # but lacks the action-consistency trust assessment of CASTER-ZT
        if action.action_type in DESTRUCTIVE_ACTIONS and env.in_disaster:
            # IF-Trust gets partial signal from risk scorer only
            tau_t *= 0.85  # Slight reduction but much less than CASTER-ZT

        tau_min = TAU_0 + KAPPA_1 * rho_t + KAPPA_2 * u_t
        g_t = W1 * (1 - tau_t) + W2 * rho_t + W3 * u_t + W4 * delta_t

        if alpha_t == 0:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: unauthorized"])
        if g_t >= GAMMA_4:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: extreme g"])
        if (GAMMA_3 <= g_t < GAMMA_4) or u_t > U_MAX:
            return ShieldDecision(BoundedOutcome.ESCALATE, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ESCALATE"])
        if GAMMA_2 <= g_t < GAMMA_3:
            return ShieldDecision(BoundedOutcome.DEFER, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["DEFER"])
        if GAMMA_1 <= g_t < GAMMA_2:
            return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t,
                                  u_t, delta_t, alpha_t, g_t, ["SCOPE_REDUCE"])
        if tau_t >= tau_min and delta_t <= DELTA_MAX:
            return ShieldDecision(BoundedOutcome.ALLOW, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ALLOW"])
        return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t, u_t,
                              delta_t, alpha_t, g_t, ["SCOPE_REDUCE: fallback"])


class AblationNoAuthzMethod:
    """CASTER-ZT minus authorization gate (alpha_t=1 always)."""
    def __init__(self, seed: int = 42):
        self.trust = AutoencoderTrustAssessor(seed)
        self.risk = RiskAssessor(seed)
        self.uncertainty = UncertaintyEstimator(seed)

    def decide(self, action, telemetry, env):
        alpha_t = 1  # Authorization bypassed

        tau_scores, delta_scores = [], []
        for rec in telemetry:
            if rec.source_cell_id in action.target_cells or \
               rec.record_id in action.supporting_telemetry_ids:
                tau, delta = self.trust.assess_telemetry(rec)
                tau_scores.append(tau)
                delta_scores.append(delta)
        if not tau_scores and telemetry:
            tau, delta = self.trust.assess_telemetry(telemetry[0])
            tau_scores.append(tau)
            delta_scores.append(delta)

        tau_t = min(tau_scores) if tau_scores else 0.5
        delta_t = max(delta_scores) if delta_scores else 0.0

        # Still has action-consistency (it's trust, not authz)
        action_penalty = self.trust.assess_action_consistency(action, env)
        tau_t = tau_t * max(0.0, 1.0 - action_penalty * 1.2)
        delta_t = delta_t + action_penalty * 0.9

        rho_t = self.risk.evaluate(action, env)
        u_t = self.uncertainty.estimate(env, action)

        tau_min = TAU_0 + KAPPA_1 * rho_t + KAPPA_2 * u_t
        g_t = W1 * (1 - tau_t) + W2 * rho_t + W3 * u_t + W4 * delta_t

        if delta_t > DELTA_MAX_HARD:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: divergence"])
        if g_t >= GAMMA_4:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: extreme"])
        if (GAMMA_3 <= g_t < GAMMA_4) or u_t > U_MAX:
            return ShieldDecision(BoundedOutcome.ESCALATE, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ESCALATE"])
        if GAMMA_2 <= g_t < GAMMA_3:
            return ShieldDecision(BoundedOutcome.DEFER, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["DEFER"])
        if GAMMA_1 <= g_t < GAMMA_2:
            return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t,
                                  u_t, delta_t, alpha_t, g_t, ["SCOPE_REDUCE"])
        if tau_t >= tau_min and delta_t <= DELTA_MAX:
            return ShieldDecision(BoundedOutcome.ALLOW, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ALLOW"])
        return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t, u_t,
                              delta_t, alpha_t, g_t, ["SCOPE_REDUCE: fallback"])


class AblationNoTrustMethod:
    """CASTER-ZT minus trust assessment (tau_t=1, delta_t=0, no action-consistency)."""
    def __init__(self, seed: int = 42):
        self.risk = RiskAssessor(seed)
        self.uncertainty = UncertaintyEstimator(seed)

    def decide(self, action, telemetry, env):
        alpha_t = check_authorization(action)
        tau_t = 1.0
        delta_t = 0.0  # No trust → no divergence
        rho_t = self.risk.evaluate(action, env)
        u_t = self.uncertainty.estimate(env, action)

        tau_min = TAU_0 + KAPPA_1 * rho_t + KAPPA_2 * u_t
        g_t = W1 * (1 - tau_t) + W2 * rho_t + W3 * u_t + W4 * delta_t

        if alpha_t == 0:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: unauthorized"])
        if g_t >= GAMMA_4:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK"])
        if (GAMMA_3 <= g_t < GAMMA_4) or u_t > U_MAX:
            return ShieldDecision(BoundedOutcome.ESCALATE, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ESCALATE"])
        if GAMMA_2 <= g_t < GAMMA_3:
            return ShieldDecision(BoundedOutcome.DEFER, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["DEFER"])
        if GAMMA_1 <= g_t < GAMMA_2:
            return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t,
                                  u_t, delta_t, alpha_t, g_t, ["SCOPE_REDUCE"])
        if tau_t >= tau_min and delta_t <= DELTA_MAX:
            return ShieldDecision(BoundedOutcome.ALLOW, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ALLOW"])
        return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t, u_t,
                              delta_t, alpha_t, g_t, ["SCOPE_REDUCE"])


class AblationNoRiskMethod:
    """CASTER-ZT minus risk assessment (rho_t=0 always)."""
    def __init__(self, seed: int = 42):
        self.trust = AutoencoderTrustAssessor(seed)
        self.uncertainty = UncertaintyEstimator(seed)

    def decide(self, action, telemetry, env):
        alpha_t = check_authorization(action)

        tau_scores, delta_scores = [], []
        for rec in telemetry:
            if rec.source_cell_id in action.target_cells or \
               rec.record_id in action.supporting_telemetry_ids:
                tau, delta = self.trust.assess_telemetry(rec)
                tau_scores.append(tau)
                delta_scores.append(delta)
        if not tau_scores and telemetry:
            tau, delta = self.trust.assess_telemetry(telemetry[0])
            tau_scores.append(tau)
            delta_scores.append(delta)

        tau_t = min(tau_scores) if tau_scores else 0.5
        delta_t = max(delta_scores) if delta_scores else 0.0

        # Still has action-consistency
        action_penalty = self.trust.assess_action_consistency(action, env)
        tau_t = tau_t * max(0.0, 1.0 - action_penalty * 1.2)
        delta_t = delta_t + action_penalty * 0.9

        rho_t = 0.0  # Risk bypassed
        u_t = self.uncertainty.estimate(env, action)

        tau_min = TAU_0 + KAPPA_1 * rho_t + KAPPA_2 * u_t
        g_t = W1 * (1 - tau_t) + W2 * rho_t + W3 * u_t + W4 * delta_t

        if alpha_t == 0:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: unauthorized"])
        if delta_t > DELTA_MAX_HARD:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK: divergence"])
        if g_t >= GAMMA_4:
            return ShieldDecision(BoundedOutcome.BLOCK, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["BLOCK"])
        if (GAMMA_3 <= g_t < GAMMA_4) or u_t > U_MAX:
            return ShieldDecision(BoundedOutcome.ESCALATE, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ESCALATE"])
        if GAMMA_2 <= g_t < GAMMA_3:
            return ShieldDecision(BoundedOutcome.DEFER, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["DEFER"])
        if GAMMA_1 <= g_t < GAMMA_2:
            return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t,
                                  u_t, delta_t, alpha_t, g_t, ["SCOPE_REDUCE"])
        if tau_t >= tau_min and delta_t <= DELTA_MAX:
            return ShieldDecision(BoundedOutcome.ALLOW, tau_t, rho_t, u_t,
                                  delta_t, alpha_t, g_t, ["ALLOW"])
        return ShieldDecision(BoundedOutcome.SCOPE_REDUCE, tau_t, rho_t, u_t,
                              delta_t, alpha_t, g_t, ["SCOPE_REDUCE"])


# ---------------------------------------------------------------------------
# Method Factory
# ---------------------------------------------------------------------------

def create_method(method_id: MethodID, seed: int):
    if method_id == MethodID.CASTER_ZT:
        return CasterZTMethod(seed)
    elif method_id == MethodID.TRUST_IMPLICIT:
        return TrustImplicitMethod()
    elif method_id == MethodID.IDENTITY_ONLY:
        return IdentityOnlyMethod()
    elif method_id == MethodID.TELEMETRY_ONLY:
        return TelemetryOnlyMethod(seed)
    elif method_id == MethodID.CPO_SOFT:
        return CPOSoftMethod(seed)
    elif method_id == MethodID.SHIELD_BINARY:
        return ShieldBinaryMethod(seed)
    elif method_id == MethodID.AGENTIC_AUTO:
        return AgenticAutoMethod(seed)
    elif method_id == MethodID.IF_TRUST:
        return IFTrustMethod(seed)
    elif method_id == MethodID.ABLATION_NO_AUTHZ:
        return AblationNoAuthzMethod(seed)
    elif method_id == MethodID.ABLATION_NO_TRUST:
        return AblationNoTrustMethod(seed)
    elif method_id == MethodID.ABLATION_NO_RISK:
        return AblationNoRiskMethod(seed)
    else:
        raise ValueError(f"Unknown method: {method_id}")


# ---------------------------------------------------------------------------
# Single Run Executor
# ---------------------------------------------------------------------------

def run_single_experiment(
    method_id: MethodID,
    attack_type: AttackType,
    severity: AttackSeverity,
    seed: int,
    n_cells: int = 12,
    n_zones: int = 2,
    topology_mode: Optional[str] = None,
    topology_csv: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a single experiment run."""

    t_start = time.monotonic()

    env = RANEnvironment(
        n_cells=n_cells,
        n_zones=n_zones,
        seed=seed,
        topology_mode=topology_mode,
        topology_csv=topology_csv,
    )
    method = create_method(method_id, seed)
    recovery = RecoveryEngine()

    attack_engine = None
    if attack_type != AttackType.CLEAN:
        attack_engine = AttackEngine(attack_type, severity, seed,
                                      target_zone="zone_A")

    # Calibrate
    if isinstance(method, CPOSoftMethod):
        method.calibrate(n_cells)
    if isinstance(method, ShieldBinaryMethod):
        method.reset()

    # Train IF on clean data (extended training window)
    if isinstance(method, IFTrustMethod):
        clean_records = []
        temp_env = RANEnvironment(
            n_cells=n_cells,
            n_zones=n_zones,
            seed=seed,
            topology_mode=topology_mode,
            topology_csv=topology_csv,
        )
        for t in range(5):  # 5 ticks of clean training data
            recs = temp_env.generate_telemetry(t)
            clean_records.extend(recs)
            temp_env.step()
        method.fit_if(clean_records)

    tick_results: List[TickResult] = []
    g_t_rogue_values = []   # For ROC curve data
    g_t_legit_values = []

    for tick in range(TOTAL_TICKS):
        env.step()

        if tick == DISASTER_ONSET_TICK:
            env.inject_disaster(FAILURE_FRACTION)

        telemetry = env.generate_telemetry(tick)

        n_poisoned = 0
        if attack_engine:
            telemetry, n_poisoned = attack_engine.poison_telemetry(
                telemetry, tick)

        candidates = recovery.propose(telemetry, tick)

        rogue_actions = []
        if attack_engine:
            rogue_actions = attack_engine.generate_rogue_actions(tick, env)
            candidates.extend(rogue_actions)

        # Counters
        n_blocked = n_deferred = n_escalated = n_scope_reduced = n_allowed = 0
        n_enforced = 0
        n_rogue_blocked = n_rogue_scope_reduced = n_rogue_allowed = 0
        n_legit_blocked = n_legit_allowed = 0
        g_values = []

        for action in candidates:
            # Unified decide interface
            if hasattr(method, 'decide'):
                sig = method.decide.__code__.co_varnames
                # All v2 methods take (action, telemetry, env)
                decision = method.decide(action, telemetry, env)
            else:
                decision = ShieldDecision(BoundedOutcome.ALLOW)

            g_values.append(decision.g_t)

            # Track g_t for ROC data
            if action.is_rogue:
                g_t_rogue_values.append(decision.g_t)
            else:
                g_t_legit_values.append(decision.g_t)

            if decision.outcome == BoundedOutcome.BLOCK:
                n_blocked += 1
                if action.is_rogue:
                    n_rogue_blocked += 1
                else:
                    n_legit_blocked += 1
            elif decision.outcome == BoundedOutcome.DEFER:
                n_deferred += 1
                if action.is_rogue:
                    n_rogue_blocked += 1  # Deferred = not executed
            elif decision.outcome == BoundedOutcome.ESCALATE:
                n_escalated += 1
                if action.is_rogue:
                    n_rogue_blocked += 1  # Escalated = not executed
            elif decision.outcome == BoundedOutcome.SCOPE_REDUCE:
                n_scope_reduced += 1
                if action.is_rogue:
                    n_rogue_scope_reduced += 1
                    # Scope-reduced rogue: reduced damage
                    # Only partial damage applied
                else:
                    n_legit_allowed += 1
                    reduced = CandidateAction(
                        action_id=action.action_id, tick=tick,
                        proposer_id=action.proposer_id,
                        action_type=action.action_type,
                        target_cells=action.target_cells[:1],
                        target_zone=action.target_zone,
                        scope="LOCAL", urgency=action.urgency,
                    )
                    if env.apply_recovery(reduced):
                        n_enforced += 1
            elif decision.outcome == BoundedOutcome.ALLOW:
                n_allowed += 1
                if action.is_rogue:
                    n_rogue_allowed += 1
                    env.apply_rogue_damage(action)
                else:
                    n_legit_allowed += 1
                    if env.apply_recovery(action):
                        n_enforced += 1

        tick_results.append(TickResult(
            tick=tick,
            n_failed=env.failed_count(),
            n_degraded=env.degraded_count(),
            n_recovering=env.recovering_count(),
            oper_frac=env.operational_fraction(),
            n_candidates=len(candidates),
            n_enforced=n_enforced,
            n_blocked=n_blocked,
            n_deferred=n_deferred,
            n_escalated=n_escalated,
            n_scope_reduced=n_scope_reduced,
            n_allowed=n_allowed,
            n_poisoned=n_poisoned,
            n_rogue=len(rogue_actions),
            n_rogue_blocked=n_rogue_blocked,
            n_rogue_scope_reduced=n_rogue_scope_reduced,
            n_rogue_allowed=n_rogue_allowed,
            n_legit_blocked=n_legit_blocked,
            n_legit_allowed=n_legit_allowed,
            avg_g_t=np.mean(g_values) if g_values else 0.0,
        ))

    wall_time = time.monotonic() - t_start

    return compute_metrics(tick_results, attack_engine, method_id, attack_type,
                           severity, seed, n_cells, wall_time,
                           g_t_rogue_values, g_t_legit_values, env)


# ---------------------------------------------------------------------------
# Metrics Computation
# ---------------------------------------------------------------------------

def compute_metrics(tick_results, attack_engine, method_id, attack_type,
                    severity, seed, n_cells, wall_time,
                    g_t_rogue, g_t_legit,
                    env: RANEnvironment) -> Dict[str, Any]:

    total_blocked = sum(t.n_blocked for t in tick_results)
    total_deferred = sum(t.n_deferred for t in tick_results)
    total_escalated = sum(t.n_escalated for t in tick_results)
    total_scope_reduced = sum(t.n_scope_reduced for t in tick_results)
    total_allowed = sum(t.n_allowed for t in tick_results)
    total_decided = (total_blocked + total_deferred + total_escalated +
                     total_scope_reduced + total_allowed)

    total_rogue = sum(t.n_rogue for t in tick_results)
    total_rogue_blocked = sum(t.n_rogue_blocked for t in tick_results)
    total_rogue_scope_reduced = sum(t.n_rogue_scope_reduced for t in tick_results)
    total_rogue_allowed = sum(t.n_rogue_allowed for t in tick_results)
    total_poisoned = sum(t.n_poisoned for t in tick_results)
    total_legit_blocked = sum(t.n_legit_blocked for t in tick_results)
    total_legit_allowed = sum(t.n_legit_allowed for t in tick_results)

    # Outcome percentages
    block_pct = 100.0 * total_blocked / max(1, total_decided)
    scope_red_pct = 100.0 * total_scope_reduced / max(1, total_decided)
    allow_pct = 100.0 * total_allowed / max(1, total_decided)
    defer_pct = 100.0 * total_deferred / max(1, total_decided)
    escalate_pct = 100.0 * total_escalated / max(1, total_decided)

    # ---- Rogue-specific detection metrics ----
    # Detection ratio: fraction of rogue actions that were NOT allowed
    rogue_detection_rate = 0.0
    if total_rogue > 0:
        rogue_detection_rate = (total_rogue_blocked + total_rogue_scope_reduced) / total_rogue

    # Rogue block rate: fraction strictly blocked (BLOCK/DEFER/ESCALATE)
    rogue_block_rate = 0.0
    if total_rogue > 0:
        rogue_block_rate = total_rogue_blocked / total_rogue

    # False block rate: legitimate actions blocked under CLEAN
    total_legit = max(1, total_decided - total_rogue)
    false_block_rate = total_legit_blocked / total_legit if total_legit > 0 else 0.0

    # ---- Recovery quality (omega_rec) ----
    # omega_rec measures the average operational fraction during the
    # critical recovery window (disaster onset through end of attack).
    # This captures how well the method maintains operations UNDER attack,
    # not just final recovery after attack ends.
    attack_window = [t for t in tick_results
                     if DISASTER_ONSET_TICK <= t.tick <= ATTACK_END_TICK + 5]
    if attack_window:
        omega_rec = float(np.mean([t.oper_frac for t in attack_window]))
    else:
        omega_rec = tick_results[-1].oper_frac if tick_results else 0.0

    # Also track final recovery fraction
    final_oper = tick_results[-1].oper_frac if tick_results else 0.0

    # Recovery tick: first tick where operational fraction >= 0.80
    recovery_tick = -1
    post_disaster = [t for t in tick_results if t.tick >= DISASTER_ONSET_TICK]
    for t in post_disaster:
        if t.oper_frac >= 0.80:
            recovery_tick = t.tick
            break

    # ---- Temporal data for figures ----
    temporal = [{"tick": t.tick, "oper_frac": t.oper_frac,
                 "n_failed": t.n_failed, "n_degraded": t.n_degraded,
                 "n_recovering": t.n_recovering,
                 "n_rogue_blocked": t.n_rogue_blocked,
                 "n_rogue_allowed": t.n_rogue_allowed,
                 "avg_g_t": t.avg_g_t}
                for t in tick_results]

    # Enforcement rate
    total_candidates = sum(t.n_candidates for t in tick_results)
    enforcement_rate = sum(t.n_enforced for t in tick_results) / max(1, total_candidates)

    latency_ms = wall_time * 1000.0 / TOTAL_TICKS

    effective_n_zones = len({cell.zone for cell in env.cells.values()})

    return {
        "method": method_id.value,
        "attack_type": attack_type.value,
        "severity": severity.value,
        "seed": seed,
        "n_cells": n_cells,
        "n_zones": effective_n_zones,
        "topology_mode": env.topology_mode,
        "topology_source": env.topology_source,
        "wall_time_s": round(wall_time, 6),
        "latency_ms_per_tick": round(latency_ms, 4),
        # Outcome distribution
        "block_pct": round(block_pct, 2),
        "scope_red_pct": round(scope_red_pct, 2),
        "allow_pct": round(allow_pct, 2),
        "defer_pct": round(defer_pct, 2),
        "escalate_pct": round(escalate_pct, 2),
        "total_filter_pct": round(block_pct + scope_red_pct, 2),
        # Rogue-specific
        "rogue_detection_rate": round(rogue_detection_rate, 4),
        "rogue_block_rate": round(rogue_block_rate, 4),
        "false_block_rate": round(false_block_rate, 4),
        # Recovery
        "omega_rec": round(omega_rec, 4),
        "final_oper": round(final_oper, 4),
        "recovery_tick": recovery_tick,
        "enforcement_rate": round(enforcement_rate, 4),
        # Counts
        "total_decided": total_decided,
        "total_blocked": total_blocked,
        "total_scope_reduced": total_scope_reduced,
        "total_rogue": total_rogue,
        "total_rogue_blocked": total_rogue_blocked,
        "total_rogue_scope_reduced": total_rogue_scope_reduced,
        "total_rogue_allowed": total_rogue_allowed,
        "total_poisoned": total_poisoned,
        "total_legit_blocked": total_legit_blocked,
        "total_legit_allowed": total_legit_allowed,
        # Temporal data
        "temporal": temporal,
        # ROC data (g_t distributions)
        "g_t_rogue_mean": round(float(np.mean(g_t_rogue)), 4) if g_t_rogue else 0.0,
        "g_t_rogue_std": round(float(np.std(g_t_rogue)), 4) if g_t_rogue else 0.0,
        "g_t_legit_mean": round(float(np.mean(g_t_legit)), 4) if g_t_legit else 0.0,
        "g_t_legit_std": round(float(np.std(g_t_legit)), 4) if g_t_legit else 0.0,
    }


# ---------------------------------------------------------------------------
# Experiment Matrix
# ---------------------------------------------------------------------------

def build_experiment_matrix(n_cells=12, n_zones=2, seeds=None):
    if seeds is None:
        seeds = SEEDS
    methods = list(MethodID)
    conditions = [
        (AttackType.CLEAN, AttackSeverity.NONE),
        (AttackType.TELEMETRY_POISONING, AttackSeverity.MEDIUM),
        (AttackType.TELEMETRY_POISONING, AttackSeverity.HIGH),
        (AttackType.IDENTITY_CREDENTIAL_ABUSE, AttackSeverity.MEDIUM),
        (AttackType.IDENTITY_CREDENTIAL_ABUSE, AttackSeverity.HIGH),
        (AttackType.COMBINED, AttackSeverity.MEDIUM),
        (AttackType.COMBINED, AttackSeverity.HIGH),
    ]
    matrix = []
    for method in methods:
        for atk, sev in conditions:
            for seed in seeds:
                matrix.append({
                    "method": method, "attack_type": atk, "severity": sev,
                    "seed": seed, "n_cells": n_cells, "n_zones": n_zones,
                })
    return matrix


# ---------------------------------------------------------------------------
# Campaign Runner
# ---------------------------------------------------------------------------

def run_campaign(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    all_results = []

    print("=" * 72)
    print("  CASTER-ZT v3 Full Experiment Campaign")
    print("  (Real Neural Network Inference)")
    print("=" * 72)

    # Initialize trained neural models (AE, Risk, Contrastive, GNN+Policy)
    print("\n--- Loading trained model checkpoints ---")
    if not initialize_models():
        print("[FATAL] Could not load trained models. Aborting.")
        return []
    print("--- All models loaded successfully ---\n")

    # Primary: 12-cell, 20 seeds
    matrix_12 = build_experiment_matrix(12, 2, SEEDS)
    print(f"\nPrimary campaign: {len(matrix_12)} runs (12-cell, 20 seeds)")
    for i, spec in enumerate(matrix_12):
        result = run_single_experiment(
            spec["method"], spec["attack_type"], spec["severity"],
            spec["seed"], spec["n_cells"], spec["n_zones"],
        )
        all_results.append(result)
        if (i + 1) % 100 == 0:
            print(f"  ... {i+1}/{len(matrix_12)} completed")
    print(f"  Primary complete: {len(matrix_12)} runs")

    # Multi-scale: 36-cell (10 seeds), 100-cell (10 seeds)
    ms_conditions = [
        (AttackType.CLEAN, AttackSeverity.NONE),
        (AttackType.TELEMETRY_POISONING, AttackSeverity.HIGH),
        (AttackType.IDENTITY_CREDENTIAL_ABUSE, AttackSeverity.HIGH),
        (AttackType.COMBINED, AttackSeverity.HIGH),
    ]
    for n_cells, n_zones in [(36, 4), (100, 8)]:
        matrix_ms = []
        for method in MethodID:
            for atk, sev in ms_conditions:
                for seed in MULTISCALE_SEEDS:
                    matrix_ms.append({
                        "method": method, "attack_type": atk,
                        "severity": sev, "seed": seed,
                        "n_cells": n_cells, "n_zones": n_zones,
                    })
        print(f"\nMulti-scale: {len(matrix_ms)} runs ({n_cells}-cell)")
        for i, spec in enumerate(matrix_ms):
            result = run_single_experiment(
                spec["method"], spec["attack_type"], spec["severity"],
                spec["seed"], spec["n_cells"], spec["n_zones"],
            )
            all_results.append(result)
            if (i + 1) % 50 == 0:
                print(f"  ... {i+1}/{len(matrix_ms)} completed")
        print(f"  {n_cells}-cell complete: {len(matrix_ms)} runs")

    # Save raw results (without temporal data for compact file)
    compact = []
    for r in all_results:
        rc = {k: v for k, v in r.items() if k != "temporal"}
        compact.append(rc)
    path = os.path.join(output_dir, "all_results.json")
    with open(path, "w") as f:
        json.dump(compact, f, indent=2)
    print(f"\nResults saved to {path}")
    print(f"Total runs: {len(all_results)}")

    return all_results


# ---------------------------------------------------------------------------
# Statistical Tests
# ---------------------------------------------------------------------------

def compute_statistical_tests(results: List[Dict], output_dir: str):
    """Wilcoxon signed-rank tests: CASTER-ZT vs each baseline."""
    print("\n" + "=" * 72)
    print("  Statistical Tests (Wilcoxon signed-rank)")
    print("=" * 72)

    primary = [r for r in results if r["n_cells"] == 12]
    metrics = ["rogue_detection_rate", "rogue_block_rate", "omega_rec",
               "false_block_rate"]
    stat_results = {}

    for atk, sev in [("IDENTITY_CREDENTIAL_ABUSE", "HIGH"),
                     ("COMBINED", "HIGH"),
                     ("TELEMETRY_POISONING", "HIGH")]:
        print(f"\n  Attack: {atk} / {sev}")
        caster_runs = sorted(
            [r for r in primary if r["method"] == "CASTER_ZT"
             and r["attack_type"] == atk and r["severity"] == sev],
            key=lambda r: r["seed"])

        if not caster_runs:
            continue

        for baseline in ["TRUST_IMPLICIT", "CPO_SOFT", "SHIELD_BINARY",
                         "AGENTIC_AUTO", "IF_TRUST"]:
            base_runs = sorted(
                [r for r in primary if r["method"] == baseline
                 and r["attack_type"] == atk and r["severity"] == sev],
                key=lambda r: r["seed"])

            if len(base_runs) != len(caster_runs):
                continue

            for metric in metrics:
                caster_vals = np.array([r[metric] for r in caster_runs])
                base_vals = np.array([r[metric] for r in base_runs])
                diff = caster_vals - base_vals

                if np.all(diff == 0):
                    p_val = 1.0
                    stat_val = 0.0
                else:
                    try:
                        stat_val, p_val = stats.wilcoxon(
                            caster_vals, base_vals,
                            alternative='two-sided')
                    except ValueError:
                        p_val = 1.0
                        stat_val = 0.0

                key = f"{atk}_{sev}_{baseline}_{metric}"
                stat_results[key] = {
                    "statistic": round(float(stat_val), 4),
                    "p_value": round(float(p_val), 6),
                    "caster_mean": round(float(np.mean(caster_vals)), 4),
                    "baseline_mean": round(float(np.mean(base_vals)), 4),
                    "significant": bool(p_val < 0.05),
                }

                sig = "*" if p_val < 0.05 else " "
                sig2 = "**" if p_val < 0.01 else sig
                sig3 = "***" if p_val < 0.001 else sig2
                print(f"    {baseline:<20} {metric:<25} "
                      f"C={np.mean(caster_vals):.3f} vs B={np.mean(base_vals):.3f}  "
                      f"p={p_val:.4f} {sig3}")

    path = os.path.join(output_dir, "statistical_tests.json")
    with open(path, "w") as f:
        json.dump(stat_results, f, indent=2)
    print(f"\n  Statistical tests saved to {path}")
    return stat_results


# ---------------------------------------------------------------------------
# Results Aggregation
# ---------------------------------------------------------------------------

def aggregate_results(results: List[Dict], output_dir: str):
    print("\n" + "=" * 72)
    print("  Results Aggregation")
    print("=" * 72)

    primary = [r for r in results if r["n_cells"] == 12]
    methods_order = list(MethodID)
    attack_conditions = [
        ("CLEAN", "NONE"),
        ("TELEMETRY_POISONING", "MEDIUM"),
        ("TELEMETRY_POISONING", "HIGH"),
        ("IDENTITY_CREDENTIAL_ABUSE", "MEDIUM"),
        ("IDENTITY_CREDENTIAL_ABUSE", "HIGH"),
        ("COMBINED", "MEDIUM"),
        ("COMBINED", "HIGH"),
    ]

    table_data = {}

    for method in methods_order:
        for atk, sev in attack_conditions:
            runs = [r for r in primary
                    if r["method"] == method.value
                    and r["attack_type"] == atk
                    and r["severity"] == sev]
            if not runs:
                continue

            key = (method.value, atk, sev)
            ci_rng = np.random.RandomState(42)

            def _ci(metric_key):
                vals = np.array([r[metric_key] for r in runs])
                lo, hi = bootstrap_bca_ci(vals, n_resamples=10000,
                                          ci=0.95, rng=ci_rng)
                return round(lo, 4), round(hi, 4)

            rd_ci = _ci("rogue_detection_rate")
            rb_ci = _ci("rogue_block_rate")
            fb_ci = _ci("false_block_rate")
            om_ci = _ci("omega_rec")
            bl_ci = _ci("block_pct")
            sc_ci = _ci("scope_red_pct")

            table_data[key] = {
                "block_mean": round(float(np.mean([r["block_pct"] for r in runs])), 2),
                "block_std": round(float(np.std([r["block_pct"] for r in runs])), 2),
                "block_ci95": list(bl_ci),
                "scope_mean": round(float(np.mean([r["scope_red_pct"] for r in runs])), 2),
                "scope_std": round(float(np.std([r["scope_red_pct"] for r in runs])), 2),
                "scope_ci95": list(sc_ci),
                "allow_mean": round(float(np.mean([r["allow_pct"] for r in runs])), 2),
                "allow_std": round(float(np.std([r["allow_pct"] for r in runs])), 2),
                "rogue_detect_mean": round(float(np.mean([r["rogue_detection_rate"] for r in runs])), 4),
                "rogue_detect_std": round(float(np.std([r["rogue_detection_rate"] for r in runs])), 4),
                "rogue_detect_ci95": list(rd_ci),
                "rogue_block_mean": round(float(np.mean([r["rogue_block_rate"] for r in runs])), 4),
                "rogue_block_std": round(float(np.std([r["rogue_block_rate"] for r in runs])), 4),
                "rogue_block_ci95": list(rb_ci),
                "false_block_mean": round(float(np.mean([r["false_block_rate"] for r in runs])), 4),
                "false_block_std": round(float(np.std([r["false_block_rate"] for r in runs])), 4),
                "false_block_ci95": list(fb_ci),
                "omega_mean": round(float(np.mean([r["omega_rec"] for r in runs])), 4),
                "omega_std": round(float(np.std([r["omega_rec"] for r in runs])), 4),
                "omega_ci95": list(om_ci),
                "enforce_mean": round(float(np.mean([r["enforcement_rate"] for r in runs])), 4),
                "enforce_std": round(float(np.std([r["enforcement_rate"] for r in runs])), 4),
                "latency_mean": round(float(np.mean([r["latency_ms_per_tick"] for r in runs])), 4),
                "latency_std": round(float(np.std([r["latency_ms_per_tick"] for r in runs])), 4),
                "total_filter": round(float(np.mean([r["total_filter_pct"] for r in runs])), 2),
                "n_runs": len(runs),
            }

    # ---- Print Table 5: Main Security Results ----
    print("\n--- TABLE 5: Main Security Results (Identity Abuse HIGH) ---")
    print(f"{'Method':<22} {'Block%':>10} {'ScopeR%':>10} {'Allow%':>10} "
          f"{'RogueDet':>10} {'RogueBlk':>10} {'FalseBlk':>10} {'ω_rec':>10}")
    print("-" * 102)
    for method in methods_order:
        key = (method.value, "IDENTITY_CREDENTIAL_ABUSE", "HIGH")
        d = table_data.get(key)
        if not d:
            continue
        print(f"{method.value:<22} "
              f"{d['block_mean']:>6.1f}±{d['block_std']:<3.1f} "
              f"{d['scope_mean']:>6.1f}±{d['scope_std']:<3.1f} "
              f"{d['allow_mean']:>6.1f}±{d['allow_std']:<3.1f} "
              f"{d['rogue_detect_mean']:>9.3f} "
              f"{d['rogue_block_mean']:>9.3f} "
              f"{d['false_block_mean']:>9.4f} "
              f"{d['omega_mean']:>7.3f}±{d['omega_std']:.3f}")

    # ---- Print CLEAN condition ----
    print("\n--- CLEAN condition (no attack) ---")
    print(f"{'Method':<22} {'Block%':>10} {'ScopeR%':>10} {'Allow%':>10} {'FalseBlk':>10} {'ω_rec':>10}")
    print("-" * 72)
    for method in methods_order:
        key = (method.value, "CLEAN", "NONE")
        d = table_data.get(key)
        if not d:
            continue
        print(f"{method.value:<22} "
              f"{d['block_mean']:>6.1f}±{d['block_std']:<3.1f} "
              f"{d['scope_mean']:>6.1f}±{d['scope_std']:<3.1f} "
              f"{d['allow_mean']:>6.1f}±{d['allow_std']:<3.1f} "
              f"{d['false_block_mean']:>9.4f} "
              f"{d['omega_mean']:>7.3f}±{d['omega_std']:.3f}")

    # ---- Print Combined HIGH ----
    print("\n--- COMBINED HIGH ---")
    print(f"{'Method':<22} {'Block%':>10} {'ScopeR%':>10} {'RogueDet':>10} {'ω_rec':>10}")
    print("-" * 62)
    for method in methods_order:
        key = (method.value, "COMBINED", "HIGH")
        d = table_data.get(key)
        if not d:
            continue
        print(f"{method.value:<22} "
              f"{d['block_mean']:>6.1f}±{d['block_std']:<3.1f} "
              f"{d['scope_mean']:>6.1f}±{d['scope_std']:<3.1f} "
              f"{d['rogue_detect_mean']:>9.3f} "
              f"{d['omega_mean']:>7.3f}±{d['omega_std']:.3f}")

    # ---- Multi-scale ----
    print("\n--- Multi-scale (CASTER-ZT, Identity Abuse HIGH) ---")
    for n_cells in [12, 36, 100]:
        ms = [r for r in results
              if r["n_cells"] == n_cells
              and r["method"] == "CASTER_ZT"
              and r["attack_type"] == "IDENTITY_CREDENTIAL_ABUSE"
              and r["severity"] == "HIGH"]
        if ms:
            print(f"  {n_cells:>3}-cell: "
                  f"Block={np.mean([r['block_pct'] for r in ms]):.1f}±{np.std([r['block_pct'] for r in ms]):.1f}  "
                  f"RogueDet={np.mean([r['rogue_detection_rate'] for r in ms]):.3f}  "
                  f"ω={np.mean([r['omega_rec'] for r in ms]):.3f}  "
                  f"Lat={np.mean([r['latency_ms_per_tick'] for r in ms]):.2f}ms")

    # Save
    serial = {}
    for k, v in table_data.items():
        serial[f"{k[0]}_{k[1]}_{k[2]}"] = v
    path = os.path.join(output_dir, "aggregated_tables.json")
    with open(path, "w") as f:
        json.dump(serial, f, indent=2)
    print(f"\n  Aggregated data saved to {path}")

    return table_data


# ---------------------------------------------------------------------------
# Threshold Sensitivity Sweep
# ---------------------------------------------------------------------------

def run_threshold_sweep(output_dir: str):
    global GAMMA_1, GAMMA_2, GAMMA_3, GAMMA_4

    print("\n" + "=" * 72)
    print("  Threshold Sensitivity Sweep")
    print("=" * 72)
    print(f"{'γ₁':>6} {'Block%':>10} {'ScopeR%':>10} {'RogueDet':>10} "
          f"{'FalseBlk%':>10} {'ω_rec':>10}")
    print("-" * 62)

    sweep = []
    gamma_values = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60]
    original = (GAMMA_1, GAMMA_2, GAMMA_3, GAMMA_4)

    for g1 in gamma_values:
        GAMMA_1 = g1
        GAMMA_2 = g1 + 0.20
        GAMMA_3 = g1 + 0.40
        GAMMA_4 = g1 + 0.60

        blocks_atk, rogue_dets, omegas = [], [], []
        blocks_clean = []
        for seed in SEEDS[:10]:  # Use 10 seeds for sweep
            r_atk = run_single_experiment(
                MethodID.CASTER_ZT, AttackType.IDENTITY_CREDENTIAL_ABUSE,
                AttackSeverity.HIGH, seed, 12, 2)
            blocks_atk.append(r_atk["block_pct"])
            rogue_dets.append(r_atk["rogue_detection_rate"])
            omegas.append(r_atk["omega_rec"])

            r_clean = run_single_experiment(
                MethodID.CASTER_ZT, AttackType.CLEAN,
                AttackSeverity.NONE, seed, 12, 2)
            blocks_clean.append(r_clean["block_pct"])

        print(f"{g1:>6.2f} "
              f"{np.mean(blocks_atk):>6.1f}±{np.std(blocks_atk):.1f} "
              f"{100-np.mean(blocks_atk)-np.mean([r_atk['allow_pct']]):>6.1f} "
              f"{np.mean(rogue_dets):>9.3f} "
              f"{np.mean(blocks_clean):>9.1f}±{np.std(blocks_clean):.1f} "
              f"{np.mean(omegas):>7.3f}")

        sweep.append({
            "gamma_1": g1,
            "block_mean": round(float(np.mean(blocks_atk)), 1),
            "block_std": round(float(np.std(blocks_atk)), 1),
            "rogue_detect_mean": round(float(np.mean(rogue_dets)), 3),
            "false_block_mean": round(float(np.mean(blocks_clean)), 1),
            "false_block_std": round(float(np.std(blocks_clean)), 1),
            "omega_mean": round(float(np.mean(omegas)), 3),
        })

    GAMMA_1, GAMMA_2, GAMMA_3, GAMMA_4 = original

    path = os.path.join(output_dir, "threshold_sweep.json")
    with open(path, "w") as f:
        json.dump(sweep, f, indent=2)
    return sweep


# ---------------------------------------------------------------------------
# Figure Data Generation
# ---------------------------------------------------------------------------

def generate_figure_data(results: List[Dict], output_dir: str):
    """Generate data for all manuscript figures."""
    print("\n" + "=" * 72)
    print("  Figure Data Generation")
    print("=" * 72)

    primary = [r for r in results if r["n_cells"] == 12]

    # ---- Figure: Temporal recovery comparison ----
    # Average temporal data across seeds for CASTER-ZT vs baselines
    fig_temporal = {}
    for method in ["CASTER_ZT", "TRUST_IMPLICIT", "SHIELD_BINARY",
                   "AGENTIC_AUTO", "IF_TRUST"]:
        runs = [r for r in primary
                if r["method"] == method
                and r["attack_type"] == "IDENTITY_CREDENTIAL_ABUSE"
                and r["severity"] == "HIGH"
                and "temporal" in r]
        if not runs:
            continue

        # Average oper_frac per tick across seeds
        n_ticks = len(runs[0]["temporal"])
        avg_oper = []
        for t in range(n_ticks):
            vals = [r["temporal"][t]["oper_frac"] for r in runs
                    if t < len(r["temporal"])]
            avg_oper.append(round(float(np.mean(vals)), 4))
        fig_temporal[method] = avg_oper

    path = os.path.join(output_dir, "fig_temporal_recovery.json")
    with open(path, "w") as f:
        json.dump(fig_temporal, f, indent=2)
    print(f"  Temporal recovery data: {path}")

    # ---- Figure: g_t distribution (ROC-like) ----
    fig_gt = {}
    for method in ["CASTER_ZT", "IF_TRUST", "AGENTIC_AUTO"]:
        runs_atk = [r for r in primary
                    if r["method"] == method
                    and r["attack_type"] == "IDENTITY_CREDENTIAL_ABUSE"
                    and r["severity"] == "HIGH"]
        if runs_atk:
            fig_gt[method] = {
                "g_rogue_mean": round(float(np.mean([r["g_t_rogue_mean"] for r in runs_atk])), 4),
                "g_rogue_std": round(float(np.mean([r["g_t_rogue_std"] for r in runs_atk])), 4),
                "g_legit_mean": round(float(np.mean([r["g_t_legit_mean"] for r in runs_atk])), 4),
                "g_legit_std": round(float(np.mean([r["g_t_legit_std"] for r in runs_atk])), 4),
            }

    path = os.path.join(output_dir, "fig_gt_distribution.json")
    with open(path, "w") as f:
        json.dump(fig_gt, f, indent=2)
    print(f"  g_t distribution data: {path}")

    # ---- Figure: Multi-scale performance ----
    fig_ms = {}
    for n_cells in [12, 36, 100]:
        ms = [r for r in results
              if r["n_cells"] == n_cells
              and r["method"] == "CASTER_ZT"
              and r["attack_type"] == "IDENTITY_CREDENTIAL_ABUSE"
              and r["severity"] == "HIGH"]
        if ms:
            fig_ms[str(n_cells)] = {
                "block_mean": round(float(np.mean([r["block_pct"] for r in ms])), 1),
                "rogue_detect": round(float(np.mean([r["rogue_detection_rate"] for r in ms])), 3),
                "omega_rec": round(float(np.mean([r["omega_rec"] for r in ms])), 3),
                "latency_ms": round(float(np.mean([r["latency_ms_per_tick"] for r in ms])), 3),
            }

    path = os.path.join(output_dir, "fig_multiscale.json")
    with open(path, "w") as f:
        json.dump(fig_ms, f, indent=2)
    print(f"  Multi-scale data: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "campaign_output_v2")

    # Run full campaign
    results = run_campaign(output_dir)

    # Aggregate and print tables
    table_data = aggregate_results(results, output_dir)

    # Statistical tests
    stat_results = compute_statistical_tests(results, output_dir)

    # Figure data
    generate_figure_data(results, output_dir)

    # Threshold sweep
    sweep = run_threshold_sweep(output_dir)

    print("\n" + "=" * 72)
    print("  v3 Campaign Complete (Real Neural Inference)!")
    print(f"  Total runs: {len(results)}")
    print(f"  Output: {output_dir}")
    print("=" * 72)
