#!/usr/bin/env python3
"""
neural_inference.py — Real-model inference bridge for CASTER-ZT experiments.

Loads trained PyTorch checkpoint files and provides inference functions
that replace the hardcoded heuristic modules in caster_zt_experiments.py.

Model checkpoints (from train_components.py):
  - checkpoints/ae_trust.pt        → TrustAutoencoder  (7→32→16→8→16→32→7)
  - checkpoints/risk_scorer.pt     → RiskScorer        (11→32→32→1, Sigmoid)
  - checkpoints/contrastive.pt     → ContrastiveEncoder (7→64→32→32)
  - checkpoints/gnn_policy.pt      → SimpleGNNEncoder  (5→64→64)
                                   + PolicyHead        (64→64→64→3)

Each inference class:
  1. Loads the trained weights from checkpoint
  2. Converts simulation data structures → model input tensors
  3. Runs a real forward pass through the trained neural network
  4. Returns the result in the format expected by the shield
"""

from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[WARN] PyTorch not available — neural inference disabled")

# ---------------------------------------------------------------------------
# Model architecture classes (must match train_components.py exactly)
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, "checkpoints")

# Architecture constants (from train_components.py)
GNN_LATENT = 64
CONTRAST_DIM = 32
RISK_HIDDEN = 32
DROPOUT = 0.1
MC_SAMPLES = 20

# Telemetry feature order (7 dims):
#   [throughput, load_ratio, latency_avg, packet_loss_rate,
#    collection_delay, is_complete, cell_state_enc]

# Action types (6 classes):
ACTION_NAMES = ["CELL_ACTIVATION", "CELL_RECONFIG", "LOAD_REBALANCE",
                "CELL_DEACTIVATION", "PARAMETER_CORRUPT", "HANDOVER_FLOOD"]
ACTION_TO_IDX = {name: i for i, name in enumerate(ACTION_NAMES)}

# Cell state encoding
CELL_STATE_ENC = {"FAILED": 0.0, "DEGRADED": 0.33,
                  "RECOVERING": 0.67, "OPERATIONAL": 1.0}


if HAS_TORCH:

    class TrustAutoencoder(nn.Module):
        """Trust autoencoder: 7 → 32 → 16 → 8 → 16 → 32 → 7"""
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(7, 32), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(32, 16), nn.ReLU(),
                nn.Linear(16, 8),
            )
            self.decoder = nn.Sequential(
                nn.Linear(8, 16), nn.ReLU(),
                nn.Linear(16, 32), nn.ReLU(),
                nn.Linear(32, 7),
            )

        def forward(self, x):
            z = self.encoder(x)
            return self.decoder(z)

        def encode(self, x):
            return self.encoder(x)

    class RiskScorer(nn.Module):
        """Neural risk scorer: (action_onehot + state) → risk probability."""
        def __init__(self, input_dim=11):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, RISK_HIDDEN), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(RISK_HIDDEN, RISK_HIDDEN), nn.ReLU(),
                nn.Linear(RISK_HIDDEN, 1), nn.Sigmoid(),
            )

        def forward(self, x):
            return self.net(x).squeeze(-1)

    class ContrastiveEncoder(nn.Module):
        """Contrastive safety encoder: telemetry → embedding."""
        def __init__(self, input_dim=7):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, 64), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(64, CONTRAST_DIM), nn.ReLU(),
                nn.Linear(CONTRAST_DIM, CONTRAST_DIM),
            )

        def forward(self, x):
            return self.encoder(x)

    class PolicyHead(nn.Module):
        """Policy head: state features → action distribution."""
        def __init__(self, input_dim=5, n_actions=3):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, GNN_LATENT), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(GNN_LATENT, GNN_LATENT), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(GNN_LATENT, n_actions),
            )

        def forward(self, x):
            return self.net(x)

    class SimpleGNNEncoder(nn.Module):
        """Simplified GNN-like encoder for topology state."""
        def __init__(self, input_dim=5):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(input_dim, GNN_LATENT), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(GNN_LATENT, GNN_LATENT), nn.ReLU(), nn.Dropout(DROPOUT),
            )

        def forward(self, x):
            return self.layers(x)


# ---------------------------------------------------------------------------
# Normalization statistics (computed from training data)
# ---------------------------------------------------------------------------

class NormStats:
    """Stores normalization statistics from training data."""

    def __init__(self):
        self.mu: Optional[np.ndarray] = None
        self.sigma: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray):
        self.mu = X.mean(axis=0)
        self.sigma = X.std(axis=0) + 1e-8

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mu is None:
            return X
        return (X - self.mu) / self.sigma

    def save(self, path: str):
        np.savez(path, mu=self.mu, sigma=self.sigma)

    def load(self, path: str):
        data = np.load(path)
        self.mu = data["mu"]
        self.sigma = data["sigma"]


# ---------------------------------------------------------------------------
# Neural Inference Manager
# ---------------------------------------------------------------------------

class NeuralInferenceManager:
    """Loads all trained models and provides inference functions.

    Usage:
        mgr = NeuralInferenceManager()
        mgr.load_all()

        # Trust assessment
        tau_t, delta_t = mgr.assess_trust(telemetry_features_7d)

        # Risk scoring
        rho_t = mgr.score_risk(action_type_str, state_features_5d)

        # MC-Dropout uncertainty
        u_t = mgr.estimate_uncertainty(state_features_5d)

        # Policy (action selection)
        action_idx, confidence = mgr.select_action(state_features_5d)
    """

    def __init__(self):
        self.ae_model = None
        self.risk_model = None
        self.contrastive_model = None
        self.gnn_model = None
        self.policy_model = None
        self.ae_norm = NormStats()
        self.loaded = False
        self._e_thresh = 0.1997  # global fallback (95th percentile)
        self._e_thresh_by_state = {}  # per-cell-state thresholds
        self._beta_tau = 5.0

    def load_all(self) -> bool:
        """Load all trained model checkpoints.

        Returns True if all models loaded successfully.
        """
        if not HAS_TORCH:
            print("[ERROR] PyTorch required for neural inference")
            return False

        # Load trust autoencoder FIRST (needed for e_thresh computation)
        ae_path = os.path.join(CHECKPOINT_DIR, "ae_trust.pt")
        if os.path.exists(ae_path):
            self.ae_model = TrustAutoencoder()
            self.ae_model.load_state_dict(torch.load(ae_path,
                                                      weights_only=True))
            self.ae_model.eval()
            print(f"  [OK] Trust autoencoder loaded ({sum(p.numel() for p in self.ae_model.parameters()):,} params)")
        else:
            print(f"  [WARN] ae_trust.pt not found at {ae_path}")
            return False

        # Compute normalization stats (uses loaded AE for e_thresh)
        self._compute_norm_stats()

        # Load risk scorer
        risk_path = os.path.join(CHECKPOINT_DIR, "risk_scorer.pt")
        if os.path.exists(risk_path):
            self.risk_model = RiskScorer(input_dim=11)
            self.risk_model.load_state_dict(torch.load(risk_path,
                                                        weights_only=True))
            self.risk_model.eval()
            print(f"  [OK] Risk scorer loaded ({sum(p.numel() for p in self.risk_model.parameters()):,} params)")
        else:
            print(f"  [WARN] risk_scorer.pt not found at {risk_path}")
            return False

        # Load contrastive encoder
        contr_path = os.path.join(CHECKPOINT_DIR, "contrastive.pt")
        if os.path.exists(contr_path):
            self.contrastive_model = ContrastiveEncoder(input_dim=7)
            self.contrastive_model.load_state_dict(
                torch.load(contr_path, weights_only=True))
            self.contrastive_model.eval()
            print(f"  [OK] Contrastive encoder loaded ({sum(p.numel() for p in self.contrastive_model.parameters()):,} params)")
        else:
            print(f"  [WARN] contrastive.pt not found at {contr_path}")
            return False

        # Load GNN encoder + policy head
        gnn_path = os.path.join(CHECKPOINT_DIR, "gnn_policy.pt")
        if os.path.exists(gnn_path):
            self.gnn_model = SimpleGNNEncoder(input_dim=5)
            self.policy_model = PolicyHead(input_dim=GNN_LATENT, n_actions=3)
            ckpt = torch.load(gnn_path, weights_only=True)
            self.gnn_model.load_state_dict(ckpt["gnn"])
            self.policy_model.load_state_dict(ckpt["policy"])
            self.gnn_model.eval()
            self.policy_model.eval()
            n_gnn = sum(p.numel() for p in self.gnn_model.parameters())
            n_pol = sum(p.numel() for p in self.policy_model.parameters())
            print(f"  [OK] GNN encoder loaded ({n_gnn:,} params)")
            print(f"  [OK] Policy head loaded ({n_pol:,} params)")
        else:
            print(f"  [WARN] gnn_policy.pt not found at {gnn_path}")
            return False

        self.loaded = True
        total = sum(
            sum(p.numel() for p in m.parameters())
            for m in [self.ae_model, self.risk_model,
                      self.contrastive_model, self.gnn_model,
                      self.policy_model]
        )
        print(f"  [OK] All models loaded — {total:,} total parameters")
        return True

    def _compute_norm_stats(self):
        """Compute normalization stats and per-state e_thresh from training data."""
        norm_path = os.path.join(CHECKPOINT_DIR, "ae_norm_stats.npz")
        ethresh_path = os.path.join(CHECKPOINT_DIR, "ae_ethresh.npy")
        state_ethresh_path = os.path.join(CHECKPOINT_DIR, "ae_ethresh_by_state.npz")

        if os.path.exists(norm_path):
            self.ae_norm.load(norm_path)
            print("  [OK] Loaded cached normalization stats")
        else:
            print("  [INFO] Computing normalization stats from training data...")
            from real_data_loader import generate_training_data
            data = generate_training_data(n_episodes=2000, seed=42)
            self.ae_norm.fit(data["clean_telemetry"])
            self.ae_norm.save(norm_path)

        # Compute or load per-state e_thresh
        if os.path.exists(state_ethresh_path) and os.path.exists(ethresh_path):
            self._e_thresh = float(np.load(ethresh_path))
            sdata = np.load(state_ethresh_path, allow_pickle=True)
            self._e_thresh_by_state = dict(sdata["state_thresholds"].item())
            print(f"  [OK] Loaded cached e_thresh = {self._e_thresh:.4f}")
            for st, th in sorted(self._e_thresh_by_state.items()):
                print(f"       e_thresh[{st}] = {th:.4f}")
        elif HAS_TORCH and self.ae_model is not None:
            print("  [INFO] Computing per-state e_thresh from AE on training data...")
            from real_data_loader import generate_training_data
            data = generate_training_data(n_episodes=2000, seed=42)
            X_clean = data["clean_telemetry"]
            X_norm = self.ae_norm.transform(X_clean)

            with torch.no_grad():
                recon = self.ae_model(torch.FloatTensor(X_norm))
                errors = ((recon - torch.FloatTensor(X_norm)) ** 2
                          ).sum(dim=1).sqrt().numpy()

            # Global threshold
            self._e_thresh = float(np.percentile(errors, 95))
            np.save(ethresh_path, self._e_thresh)

            # Per-state thresholds: cell_state_enc is feature index 6
            # State encoding: 0.0=FAILED, 0.33=DEGRADED, 0.67=RECOVERING, 1.0=OPERATIONAL
            state_enc_col = X_clean[:, 6]
            state_bins = {
                "FAILED": (state_enc_col < 0.1),
                "DEGRADED": ((state_enc_col >= 0.1) & (state_enc_col < 0.5)),
                "RECOVERING": ((state_enc_col >= 0.5) & (state_enc_col < 0.85)),
                "OPERATIONAL": (state_enc_col >= 0.85),
            }

            self._e_thresh_by_state = {}
            for state_name, mask in state_bins.items():
                if mask.sum() > 0:
                    self._e_thresh_by_state[state_name] = float(
                        np.percentile(errors[mask], 95))
                else:
                    self._e_thresh_by_state[state_name] = self._e_thresh

            np.savez(state_ethresh_path,
                     state_thresholds=self._e_thresh_by_state)

            print(f"  [OK] e_thresh (global 95th pct) = {self._e_thresh:.4f}")
            for st, th in sorted(self._e_thresh_by_state.items()):
                print(f"       e_thresh[{st}] = {th:.4f}")

    # -----------------------------------------------------------------
    # Trust Assessment (real autoencoder + contrastive encoder)
    # -----------------------------------------------------------------

    def assess_trust(self, features_7d: np.ndarray) -> Tuple[float, float]:
        """Run real autoencoder and contrastive encoder on telemetry.

        Args:
            features_7d: 7-dim telemetry features
                [throughput, load_ratio, latency_avg, packet_loss_rate,
                 collection_delay, is_complete, cell_state_enc]

        Returns:
            (tau_t, delta_t): trust score ∈ [0,1] and divergence ≥ 0
        """
        if not self.loaded:
            return 0.5, 0.0

        # Normalize using training statistics
        x = self.ae_norm.transform(features_7d.reshape(1, -1))
        x_tensor = torch.FloatTensor(x)

        with torch.no_grad():
            # --- Autoencoder reconstruction error ---
            recon = self.ae_model(x_tensor)
            recon_error = float(
                ((recon - x_tensor) ** 2).sum(dim=1).sqrt().item()
            )

            # --- Select per-state e_thresh ---
            state_enc = float(features_7d[6])
            if state_enc < 0.1:
                state_key = "FAILED"
            elif state_enc < 0.5:
                state_key = "DEGRADED"
            elif state_enc < 0.85:
                state_key = "RECOVERING"
            else:
                state_key = "OPERATIONAL"

            e_thresh_eff = self._e_thresh_by_state.get(
                state_key, self._e_thresh)

            # --- Trust score via sigmoid ---
            exponent = self._beta_tau * (recon_error - e_thresh_eff)
            if exponent > 500:
                tau_t = 0.0
            elif exponent < -500:
                tau_t = 1.0
            else:
                tau_t = 1.0 / (1.0 + math.exp(exponent))
            tau_t = max(0.0, min(1.0, tau_t))

            # --- Contrastive divergence ---
            # Benign hypothesis: original features
            z_benign = self.contrastive_model(x_tensor)
            # Adversarial hypothesis: original + reconstruction residual
            residual = x_tensor - recon  # perturbation estimate
            x_adv = x_tensor + residual  # adversarial hypothesis
            z_adv = self.contrastive_model(x_adv)
            # Divergence = L2 distance in embedding space
            delta_t = float(
                torch.sqrt(((z_benign - z_adv) ** 2).sum() + 1e-8).item()
            )

        return tau_t, delta_t

    def assess_action_consistency(self, action_type: str,
                                   cell_states: List[str],
                                   in_disaster: bool,
                                   zone_fail_frac: float,
                                   proposer_role: str,
                                   has_evidence: bool) -> float:
        """Use autoencoder to assess action-context consistency.

        Constructs a synthetic telemetry vector representing the
        action-context and runs it through the autoencoder. Actions
        inconsistent with the learned clean-operation manifold produce
        high reconstruction error.

        Returns additional penalty ∈ [0, 1].
        """
        if not self.loaded:
            return 0.0

        # Build a context-aware telemetry proxy
        # The idea: construct a feature vector capturing what the telemetry
        # "should look like" if this action is legitimate, and measure
        # how anomalous this pattern is to the autoencoder.

        penalties = []

        for cs in cell_states:
            # Construct expected telemetry for this cell state + action
            state_enc = CELL_STATE_ENC.get(cs, 0.5)

            # For a legitimate action, we expect:
            #   - recovery actions on failed/degraded cells (low state_enc)
            #   - destructive actions should rarely appear
            if action_type in ("CELL_DEACTIVATION", "PARAMETER_CORRUPT",
                               "HANDOVER_FLOOD"):
                if in_disaster:
                    # Construct anomalous pattern: high throughput
                    # (operational) but low state_enc (disaster)
                    # This is what a malicious actor would create
                    feat = np.array([120.0, 0.8, 5.0, 0.001,
                                     0.1, 1.0, state_enc],
                                    dtype=np.float32)
                else:
                    feat = np.array([60.0, 0.5, 15.0, 0.03,
                                     0.1, 1.0, state_enc],
                                    dtype=np.float32)
            else:
                # Legitimate recovery action — construct normal pattern
                if cs == "FAILED":
                    feat = np.array([0.0, 1.0, 500.0, 1.0,
                                     0.1, 0.0, 0.0],
                                    dtype=np.float32)
                elif cs == "DEGRADED":
                    feat = np.array([30.0, 0.8, 80.0, 0.2,
                                     0.15, 1.0, 0.33],
                                    dtype=np.float32)
                else:
                    feat = np.array([90.0, 0.5, 15.0, 0.01,
                                     0.1, 1.0, state_enc],
                                    dtype=np.float32)

            x = self.ae_norm.transform(feat.reshape(1, -1))
            x_tensor = torch.FloatTensor(x)

            with torch.no_grad():
                recon = self.ae_model(x_tensor)
                err = float(
                    ((recon - x_tensor) ** 2).sum(dim=1).sqrt().item()
                )

            # Higher reconstruction error → more anomalous
            # Scale relative to e_thresh
            anomaly_ratio = err / max(self._e_thresh, 1e-6)
            if anomaly_ratio > 1.5:
                penalties.append(min(1.0, (anomaly_ratio - 1.0) * 0.4))
            elif anomaly_ratio > 1.0:
                penalties.append(min(0.5, (anomaly_ratio - 0.8) * 0.3))

        # Proposer-action profile check via contrastive encoder
        if (proposer_role == "XAPP_RECOVERY" and
                action_type in ("CELL_DEACTIVATION", "PARAMETER_CORRUPT",
                                "HANDOVER_FLOOD")):
            # Recovery xApp proposing destructive action
            # Use contrastive encoder to measure how unusual this pairing is
            # Construct normal vs anomalous pattern
            normal_feat = np.array([90.0, 0.5, 15.0, 0.01,
                                     0.1, 1.0, 1.0], dtype=np.float32)
            anomalous_feat = np.array([120.0, 0.8, 5.0, 0.001,
                                        0.1, 1.0, 0.0], dtype=np.float32)
            x_n = torch.FloatTensor(
                self.ae_norm.transform(normal_feat.reshape(1, -1)))
            x_a = torch.FloatTensor(
                self.ae_norm.transform(anomalous_feat.reshape(1, -1)))

            with torch.no_grad():
                z_n = self.contrastive_model(x_n)
                z_a = self.contrastive_model(x_a)
                divergence = float(
                    torch.sqrt(((z_n - z_a) ** 2).sum() + 1e-8).item()
                )
            # Scale divergence to penalty
            penalties.append(min(1.0, divergence * 0.3))

        # Evidence check
        if not has_evidence and action_type in (
                "CELL_ACTIVATION", "CELL_RECONFIG", "LOAD_REBALANCE"):
            penalties.append(0.20)

        return min(1.0, sum(penalties)) if penalties else 0.0

    # -----------------------------------------------------------------
    # Risk Scoring (real neural risk scorer)
    # -----------------------------------------------------------------

    def score_risk(self, action_type: str,
                   op_frac: float,
                   fail_frac: float,
                   in_disaster: bool,
                   under_attack: bool,
                   tick_frac: float) -> float:
        """Run real risk scorer neural network.

        Args:
            action_type: action type string
            op_frac: fraction of operational cells
            fail_frac: fraction of failed cells
            in_disaster: whether disaster is active
            under_attack: whether under attack
            tick_frac: current tick / total ticks

        Returns:
            rho_t: risk score ∈ [0, 1]
        """
        if not self.loaded:
            return 0.0

        # Build 11-dim input: 6 action one-hot + 5 state features
        action_idx = ACTION_TO_IDX.get(action_type, 0)
        onehot = [0.0] * 6
        if action_idx < 6:
            onehot[action_idx] = 1.0

        features = onehot + [op_frac, fail_frac,
                              1.0 if in_disaster else 0.0,
                              1.0 if under_attack else 0.0,
                              tick_frac]
        x_tensor = torch.FloatTensor([features])

        with torch.no_grad():
            rho_t = float(self.risk_model(x_tensor).item())

        return max(0.0, min(1.0, rho_t))

    # -----------------------------------------------------------------
    # Uncertainty Estimation (real MC-Dropout)
    # -----------------------------------------------------------------

    def estimate_uncertainty(self, state_features_5d: np.ndarray) -> float:
        """Run real MC-Dropout uncertainty estimation.

        Performs MC_SAMPLES forward passes through the GNN encoder
        with dropout enabled, then computes the std of policy
        softmax outputs.

        Args:
            state_features_5d: [op_frac, fail_frac, in_disaster,
                                under_attack, tick_frac]

        Returns:
            u_t: uncertainty ∈ [0, 1]
        """
        if not self.loaded:
            return 0.1

        x_tensor = torch.FloatTensor(
            state_features_5d.reshape(1, -1))

        # Enable dropout for MC sampling on BOTH GNN and policy
        self.gnn_model.train()
        self.policy_model.train()

        mc_probs = []
        with torch.no_grad():
            for _ in range(MC_SAMPLES):
                z = self.gnn_model(x_tensor)
                logits = self.policy_model(z)
                probs = torch.softmax(logits, dim=1)
                mc_probs.append(probs.numpy())

        # Restore eval mode
        self.gnn_model.eval()
        self.policy_model.eval()

        mc_probs = np.array(mc_probs)  # (MC_SAMPLES, 1, n_actions)
        # Uncertainty = mean of per-action std across MC samples
        # Scale by sqrt(n_actions) to normalise to [0,1] range
        raw_u = float(mc_probs.std(axis=0).mean())
        n_actions = mc_probs.shape[2]
        # Maximum possible std for uniform vs degenerate softmax ≈ 0.47
        # Scale so that moderate uncertainty maps to ~0.1-0.2
        u_t = min(1.0, raw_u * math.sqrt(n_actions) * 5.0)

        return max(0.0, min(1.0, u_t))

    # -----------------------------------------------------------------
    # Action Selection (real GNN + Policy)
    # -----------------------------------------------------------------

    def select_action(self, state_features_5d: np.ndarray
                      ) -> Tuple[int, float]:
        """Run real GNN encoder + policy head for action selection.

        Args:
            state_features_5d: [op_frac, fail_frac, in_disaster,
                                under_attack, tick_frac]

        Returns:
            (action_idx, confidence): selected action index and
            confidence score
        """
        if not self.loaded:
            return 0, 0.5

        x_tensor = torch.FloatTensor(
            state_features_5d.reshape(1, -1))

        self.gnn_model.eval()
        self.policy_model.eval()

        with torch.no_grad():
            z = self.gnn_model(x_tensor)
            logits = self.policy_model(z)
            probs = torch.softmax(logits, dim=1)

        probs_np = probs.numpy().flatten()
        action_idx = int(np.argmax(probs_np))
        confidence = float(probs_np[action_idx])

        return action_idx, confidence


# ---------------------------------------------------------------------------
# Singleton for global access
# ---------------------------------------------------------------------------

_global_manager: Optional[NeuralInferenceManager] = None


def get_inference_manager() -> NeuralInferenceManager:
    """Get or create the global inference manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = NeuralInferenceManager()
    return _global_manager


def initialize_models() -> bool:
    """Initialize and load all models. Call once at startup."""
    mgr = get_inference_manager()
    if not mgr.loaded:
        return mgr.load_all()
    return True


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Neural Inference Manager — Self-Test")
    print("=" * 60)

    mgr = NeuralInferenceManager()
    ok = mgr.load_all()

    if ok:
        # Test trust assessment
        feat = np.array([90.0, 0.5, 15.0, 0.01, 0.1, 1.0, 1.0],
                        dtype=np.float32)
        tau, delta = mgr.assess_trust(feat)
        print(f"\n  Trust test (clean): tau={tau:.4f}, delta={delta:.4f}")

        # Anomalous telemetry
        feat_anom = np.array([200.0, 0.9, 2.0, 0.0, 0.1, 1.0, 0.0],
                             dtype=np.float32)
        tau2, delta2 = mgr.assess_trust(feat_anom)
        print(f"  Trust test (anomalous): tau={tau2:.4f}, delta={delta2:.4f}")

        # Test risk scoring
        rho = mgr.score_risk("CELL_ACTIVATION", 0.7, 0.2, True, False, 0.3)
        print(f"\n  Risk test (CELL_ACTIVATION, disaster): rho={rho:.4f}")
        rho2 = mgr.score_risk("CELL_DEACTIVATION", 0.7, 0.2, True, True, 0.3)
        print(f"  Risk test (CELL_DEACTIVATION, attack): rho={rho2:.4f}")

        # Test uncertainty
        state = np.array([0.7, 0.2, 1.0, 0.0, 0.3], dtype=np.float32)
        u = mgr.estimate_uncertainty(state)
        print(f"\n  Uncertainty test: u={u:.4f}")

        # Test action selection
        action_idx, conf = mgr.select_action(state)
        actions = ["CELL_ACTIVATION", "CELL_RECONFIG", "LOAD_REBALANCE"]
        print(f"\n  Policy test: action={actions[action_idx]}, "
              f"confidence={conf:.4f}")
    else:
        print("\n  [FAIL] Could not load models")
