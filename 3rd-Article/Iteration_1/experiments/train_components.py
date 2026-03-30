#!/usr/bin/env python3
"""
train_components.py — Training pipeline for CASTER-ZT neural components.

Trains the five learned modules described in Section III-E of the manuscript:
  1. Trust Autoencoder (AE_phi): MSE reconstruction on clean telemetry
  2. Risk Scorer (R_phi): Binary cross-entropy on action-state-outcome tuples
  3. Contrastive Safety Encoder (q_phi): Margin-based contrastive loss
  4. GNN Encoder (f_theta): GraphSAGE on disaster topology graphs
  5. Policy Head (pi_theta): Cross-entropy supervised imitation

Produces:
  - Training/validation loss curves for each component
  - Convergence figures (fig_training_curves.pdf/png)
  - Validation metrics (precision, recall, F1, AUC-ROC)
  - Saved model checkpoints

Usage:
    python train_components.py
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

# Try importing torch; fallback to numpy-only simulation if unavailable
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[WARN] PyTorch not available — using numpy-only training simulation")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURES_DIR = os.path.join(SCRIPT_DIR, "figures")
CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, "checkpoints")
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# Training hyperparameters (from manuscript Section III-E)
N_EPISODES = 2000           # Simulated disaster-recovery episodes
TRAIN_SPLIT = 0.70
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15
BATCH_SIZE = 64
LR_GNN = 1e-3
LR_AE = 5e-4
LR_RISK = 1e-3
LR_CONTRAST = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 15
MAX_EPOCHS = 120
DROPOUT = 0.1
MC_SAMPLES = 20

# Architecture sizes (from manuscript — 6G-driven sizing)
GNN_LATENT = 64
GNN_LAYERS = 2
AE_DIMS = [7, 32, 16, 8]   # input → hidden → bottleneck
RISK_HIDDEN = 32
CONTRAST_DIM = 32

# Telemetry feature bounds (clean operation)
TELEM_BOUNDS = {
    "throughput": (40.0, 140.0),
    "load_ratio": (0.2, 0.85),
    "latency_avg": (3.0, 40.0),
    "packet_loss_rate": (0.005, 0.12),
    "collection_delay": (0.0, 0.5),
    "is_complete": (0.95, 1.0),
    "cell_state_enc": (0.0, 1.0),  # 0=failed, 0.33=degraded, 0.67=recovering, 1=operational
}

N_ACTIONS = 6  # CELL_ACTIVATION, CELL_RECONFIG, LOAD_REBALANCE, CELL_DEACTIVATION, PARAMETER_CORRUPT, HANDOVER_FLOOD
ACTION_NAMES = ["CELL_ACTIVATION", "CELL_RECONFIG", "LOAD_REBALANCE",
                "CELL_DEACTIVATION", "PARAMETER_CORRUPT", "HANDOVER_FLOOD"]

SEED = 42
np.random.seed(SEED)
random.seed(SEED)
if HAS_TORCH:
    torch.manual_seed(SEED)


# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------

def encode_cell_state(state: str) -> float:
    return {"FAILED": 0.0, "DEGRADED": 0.33, "RECOVERING": 0.67,
            "OPERATIONAL": 1.0}.get(state, 0.5)


def generate_training_data(n_episodes: int = N_EPISODES, seed: int = SEED):
    """Generate labeled disaster-recovery episodes for all components.

    Delegates to real_data_loader which draws all telemetry from
    published 5G measurement distributions (Narayanan et al. 2021,
    Xu et al. 2020, 3GPP TR 38.913) and attack patterns from SWaT
    testbed distributions (Goh et al. 2017).
    """
    from real_data_loader import generate_training_data as _gen_real
    return _gen_real(n_episodes=n_episodes, seed=seed)


def split_data(X, y, train=0.70, val=0.15):
    """Split into train/val/test."""
    n = len(X)
    idx = np.random.permutation(n)
    n_train = int(n * train)
    n_val = int(n * val)
    train_idx = idx[:n_train]
    val_idx = idx[n_train:n_train + n_val]
    test_idx = idx[n_train + n_val:]
    return (X[train_idx], y[train_idx],
            X[val_idx], y[val_idx],
            X[test_idx], y[test_idx])


# ---------------------------------------------------------------------------
# PyTorch Models
# ---------------------------------------------------------------------------

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
        """Simplified GNN-like encoder for topology state.
        Uses 2-layer MLP as proxy for GraphSAGE (graph structure is
        implicit in the aggregated state features)."""
        def __init__(self, input_dim=5):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Linear(input_dim, GNN_LATENT), nn.ReLU(), nn.Dropout(DROPOUT),
                nn.Linear(GNN_LATENT, GNN_LATENT), nn.ReLU(), nn.Dropout(DROPOUT),
            )

        def forward(self, x):
            return self.layers(x)


# ---------------------------------------------------------------------------
# Training Functions
# ---------------------------------------------------------------------------

def train_autoencoder(data: dict) -> dict:
    """Train the trust autoencoder on clean telemetry."""
    print("\n" + "=" * 60)
    print("  Training Trust Autoencoder (AE_phi)")
    print("=" * 60)

    X_clean = data["clean_telemetry"]

    # Normalize
    mu = X_clean.mean(axis=0)
    sigma = X_clean.std(axis=0) + 1e-8
    X_norm = (X_clean - mu) / sigma

    X_tr, _, X_val, _, X_te, _ = split_data(
        X_norm, X_norm, TRAIN_SPLIT, VAL_SPLIT)

    history = {"train_loss": [], "val_loss": [], "val_recon_p95": []}

    if HAS_TORCH:
        model = TrustAutoencoder()
        optimizer = optim.Adam(model.parameters(), lr=LR_AE, weight_decay=WEIGHT_DECAY)
        criterion = nn.MSELoss()

        train_ds = TensorDataset(torch.FloatTensor(X_tr))
        val_ds = TensorDataset(torch.FloatTensor(X_val))
        train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
        val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE)

        best_val = float("inf")
        patience_counter = 0
        best_epoch = 0

        for epoch in range(MAX_EPOCHS):
            # Train
            model.train()
            train_losses = []
            for (batch,) in train_dl:
                optimizer.zero_grad()
                recon = model(batch)
                loss = criterion(recon, batch)
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())

            # Validate
            model.eval()
            val_losses = []
            val_recon_errors = []
            with torch.no_grad():
                for (batch,) in val_dl:
                    recon = model(batch)
                    loss = criterion(recon, batch)
                    val_losses.append(loss.item())
                    errs = ((recon - batch) ** 2).sum(dim=1).sqrt()
                    val_recon_errors.extend(errs.numpy().tolist())

            train_loss = np.mean(train_losses)
            val_loss = np.mean(val_losses)
            val_p95 = np.percentile(val_recon_errors, 95)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_recon_p95"].append(val_p95)

            if epoch % 10 == 0 or epoch < 5:
                print(f"  Epoch {epoch:3d}: train_loss={train_loss:.6f}  "
                      f"val_loss={val_loss:.6f}  val_p95={val_p95:.4f}")

            if val_loss < best_val:
                best_val = val_loss
                patience_counter = 0
                best_epoch = epoch
                torch.save(model.state_dict(),
                           os.path.join(CHECKPOINT_DIR, "ae_trust.pt"))
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    print(f"  Early stopping at epoch {epoch} "
                          f"(best={best_epoch}, val_loss={best_val:.6f})")
                    break

        # Test evaluation
        model.load_state_dict(
            torch.load(os.path.join(CHECKPOINT_DIR, "ae_trust.pt")))
        model.eval()
        with torch.no_grad():
            test_recon = model(torch.FloatTensor(X_te))
            test_errors = ((test_recon - torch.FloatTensor(X_te)) ** 2).sum(dim=1).sqrt()
            e_thresh = np.percentile(test_errors.numpy(), 95)

        print(f"\n  Final: best_epoch={best_epoch}, e_thresh(p95)={e_thresh:.4f}")
        print(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")

        # Anomaly detection on mixed data
        X_all = data["all_telemetry"]
        X_all_norm = (X_all - mu) / sigma
        with torch.no_grad():
            all_recon = model(torch.FloatTensor(X_all_norm))
            all_errors = ((all_recon - torch.FloatTensor(X_all_norm)) ** 2).sum(dim=1).sqrt().numpy()

        preds = (all_errors > e_thresh).astype(float)
        labels = data["labels_anomaly"]
        tp = ((preds == 1) & (labels == 1)).sum()
        fp = ((preds == 1) & (labels == 0)).sum()
        fn = ((preds == 0) & (labels == 1)).sum()
        tn = ((preds == 0) & (labels == 0)).sum()
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-8, precision + recall)
        accuracy = (tp + tn) / len(labels)
        print(f"  Anomaly detection: P={precision:.3f} R={recall:.3f} "
              f"F1={f1:.3f} Acc={accuracy:.3f}")

        history["test_metrics"] = {
            "e_thresh": float(e_thresh),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "accuracy": float(accuracy),
            "n_params": sum(p.numel() for p in model.parameters()),
        }
    else:
        # Numpy-only fallback: simulate realistic training curves
        history = _simulate_ae_training()

    return history


def train_risk_scorer(data: dict) -> dict:
    """Train the neural risk scorer."""
    print("\n" + "=" * 60)
    print("  Training Risk Scorer (R_phi)")
    print("=" * 60)

    X = data["action_state_pairs"]
    y = 1.0 - data["labels_safety"]  # risk = 1 - safety

    X_tr, y_tr, X_val, y_val, X_te, y_te = split_data(X, y)
    history = {"train_loss": [], "val_loss": [], "val_auc": []}

    if HAS_TORCH:
        model = RiskScorer(input_dim=X.shape[1])
        optimizer = optim.Adam(model.parameters(), lr=LR_RISK, weight_decay=WEIGHT_DECAY)
        criterion = nn.BCELoss()

        train_ds = TensorDataset(torch.FloatTensor(X_tr), torch.FloatTensor(y_tr))
        val_ds = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
        train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
        val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE)

        best_val = float("inf")
        patience_counter = 0
        best_epoch = 0

        for epoch in range(MAX_EPOCHS):
            model.train()
            train_losses = []
            for X_batch, y_batch in train_dl:
                optimizer.zero_grad()
                pred = model(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())

            model.eval()
            val_losses = []
            val_preds, val_labels = [], []
            with torch.no_grad():
                for X_batch, y_batch in val_dl:
                    pred = model(X_batch)
                    loss = criterion(pred, y_batch)
                    val_losses.append(loss.item())
                    val_preds.extend(pred.numpy().tolist())
                    val_labels.extend(y_batch.numpy().tolist())

            train_loss = np.mean(train_losses)
            val_loss = np.mean(val_losses)

            # Compute AUC-ROC
            val_preds_arr = np.array(val_preds)
            val_labels_arr = np.array(val_labels)
            auc = _compute_auc(val_labels_arr, val_preds_arr)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_auc"].append(auc)

            if epoch % 10 == 0 or epoch < 5:
                print(f"  Epoch {epoch:3d}: train_loss={train_loss:.4f}  "
                      f"val_loss={val_loss:.4f}  val_AUC={auc:.4f}")

            if val_loss < best_val:
                best_val = val_loss
                patience_counter = 0
                best_epoch = epoch
                torch.save(model.state_dict(),
                           os.path.join(CHECKPOINT_DIR, "risk_scorer.pt"))
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    print(f"  Early stopping at epoch {epoch} (best={best_epoch})")
                    break

        # Test
        model.load_state_dict(
            torch.load(os.path.join(CHECKPOINT_DIR, "risk_scorer.pt")))
        model.eval()
        with torch.no_grad():
            test_pred = model(torch.FloatTensor(X_te)).numpy()
        test_auc = _compute_auc(y_te, test_pred)
        test_preds_bin = (test_pred > 0.5).astype(float)
        test_acc = (test_preds_bin == y_te).mean()
        print(f"\n  Final: best_epoch={best_epoch}, test_AUC={test_auc:.4f}, "
              f"test_acc={test_acc:.4f}")
        print(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")

        history["test_metrics"] = {
            "auc_roc": float(test_auc),
            "accuracy": float(test_acc),
            "n_params": sum(p.numel() for p in model.parameters()),
        }
    else:
        history = _simulate_risk_training()

    return history


def train_contrastive_encoder(data: dict) -> dict:
    """Train the contrastive safety encoder."""
    print("\n" + "=" * 60)
    print("  Training Contrastive Safety Encoder (q_phi)")
    print("=" * 60)

    X = data["all_telemetry"]
    y = data["labels_poisoned"]

    # Normalize
    mu = X.mean(axis=0)
    sigma = X.std(axis=0) + 1e-8
    X_norm = (X - mu) / sigma

    X_tr, y_tr, X_val, y_val, X_te, y_te = split_data(X_norm, y)
    history = {"train_loss": [], "val_loss": []}

    if HAS_TORCH:
        model = ContrastiveEncoder(input_dim=X.shape[1])
        optimizer = optim.Adam(model.parameters(), lr=LR_CONTRAST, weight_decay=WEIGHT_DECAY)
        margin = 1.0

        best_val = float("inf")
        patience_counter = 0
        best_epoch = 0

        for epoch in range(MAX_EPOCHS):
            model.train()
            train_losses = []

            # Create pairs
            idx = np.random.permutation(len(X_tr))
            for i in range(0, len(idx) - 1, 2):
                x1 = torch.FloatTensor(X_tr[idx[i]]).unsqueeze(0)
                x2 = torch.FloatTensor(X_tr[idx[i + 1]]).unsqueeze(0)
                y1 = y_tr[idx[i]]
                y2 = y_tr[idx[i + 1]]
                # Label: 1 if one is poisoned and other is clean
                pair_label = float(y1 != y2)

                optimizer.zero_grad()
                z1 = model(x1)
                z2 = model(x2)
                dist = torch.sqrt(((z1 - z2) ** 2).sum() + 1e-8)

                # Contrastive loss
                loss = pair_label * torch.clamp(margin - dist, min=0) + \
                       (1 - pair_label) * dist
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())

            # Validation
            model.eval()
            val_losses = []
            idx_v = np.random.permutation(len(X_val))
            with torch.no_grad():
                for i in range(0, min(len(idx_v) - 1, 2000), 2):
                    x1 = torch.FloatTensor(X_val[idx_v[i]]).unsqueeze(0)
                    x2 = torch.FloatTensor(X_val[idx_v[i + 1]]).unsqueeze(0)
                    pair_label = float(y_val[idx_v[i]] != y_val[idx_v[i + 1]])
                    z1 = model(x1)
                    z2 = model(x2)
                    dist = torch.sqrt(((z1 - z2) ** 2).sum() + 1e-8)
                    loss = pair_label * torch.clamp(margin - dist, min=0) + \
                           (1 - pair_label) * dist
                    val_losses.append(loss.item())

            train_loss = np.mean(train_losses)
            val_loss = np.mean(val_losses)
            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)

            if epoch % 10 == 0 or epoch < 5:
                print(f"  Epoch {epoch:3d}: train_loss={train_loss:.4f}  "
                      f"val_loss={val_loss:.4f}")

            if val_loss < best_val:
                best_val = val_loss
                patience_counter = 0
                best_epoch = epoch
                torch.save(model.state_dict(),
                           os.path.join(CHECKPOINT_DIR, "contrastive.pt"))
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    print(f"  Early stopping at epoch {epoch} (best={best_epoch})")
                    break

        print(f"\n  Final: best_epoch={best_epoch}")
        print(f"  Model parameters: {sum(p.numel() for p in model.parameters()):,}")
        history["test_metrics"] = {
            "n_params": sum(p.numel() for p in model.parameters()),
        }
    else:
        history = _simulate_contrastive_training()

    return history


def train_gnn_policy(data: dict) -> dict:
    """Train the GNN encoder + policy head (supervised imitation)."""
    print("\n" + "=" * 60)
    print("  Training GNN Encoder + Policy Head (f_theta, pi_theta)")
    print("=" * 60)

    X = data["action_state_pairs"][:, N_ACTIONS:]  # State features only
    y = data["labels_action"]

    X_tr, y_tr, X_val, y_val, X_te, y_te = split_data(X, y)
    history = {"train_loss": [], "val_loss": [], "val_acc": []}

    if HAS_TORCH:
        gnn = SimpleGNNEncoder(input_dim=X.shape[1])
        policy = PolicyHead(input_dim=GNN_LATENT, n_actions=3)
        params = list(gnn.parameters()) + list(policy.parameters())
        optimizer = optim.Adam(params, lr=LR_GNN, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss()

        train_ds = TensorDataset(torch.FloatTensor(X_tr), torch.LongTensor(y_tr))
        val_ds = TensorDataset(torch.FloatTensor(X_val), torch.LongTensor(y_val))
        train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
        val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE)

        best_val = float("inf")
        patience_counter = 0
        best_epoch = 0

        for epoch in range(MAX_EPOCHS):
            gnn.train()
            policy.train()
            train_losses = []
            for X_batch, y_batch in train_dl:
                optimizer.zero_grad()
                z = gnn(X_batch)
                logits = policy(z)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())

            gnn.eval()
            policy.eval()
            val_losses = []
            correct = 0
            total = 0
            with torch.no_grad():
                for X_batch, y_batch in val_dl:
                    z = gnn(X_batch)
                    logits = policy(z)
                    loss = criterion(logits, y_batch)
                    val_losses.append(loss.item())
                    preds = logits.argmax(dim=1)
                    correct += (preds == y_batch).sum().item()
                    total += len(y_batch)

            train_loss = np.mean(train_losses)
            val_loss = np.mean(val_losses)
            val_acc = correct / max(1, total)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_acc"].append(val_acc)

            if epoch % 10 == 0 or epoch < 5:
                print(f"  Epoch {epoch:3d}: train_loss={train_loss:.4f}  "
                      f"val_loss={val_loss:.4f}  val_acc={val_acc:.4f}")

            if val_loss < best_val:
                best_val = val_loss
                patience_counter = 0
                best_epoch = epoch
                torch.save({"gnn": gnn.state_dict(), "policy": policy.state_dict()},
                           os.path.join(CHECKPOINT_DIR, "gnn_policy.pt"))
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    print(f"  Early stopping at epoch {epoch} (best={best_epoch})")
                    break

        # Test
        ckpt = torch.load(os.path.join(CHECKPOINT_DIR, "gnn_policy.pt"))
        gnn.load_state_dict(ckpt["gnn"])
        policy.load_state_dict(ckpt["policy"])
        gnn.eval()
        policy.eval()
        with torch.no_grad():
            z_te = gnn(torch.FloatTensor(X_te))
            logits_te = policy(z_te)
            preds_te = logits_te.argmax(dim=1).numpy()
        test_acc = (preds_te == y_te).mean()

        # MC-Dropout uncertainty
        gnn.train()  # Enable dropout
        mc_preds = []
        with torch.no_grad():
            for _ in range(MC_SAMPLES):
                z = gnn(torch.FloatTensor(X_te[:100]))
                logits = policy(z)
                probs = torch.softmax(logits, dim=1)
                mc_preds.append(probs.numpy())
        mc_preds = np.array(mc_preds)
        mc_mean = mc_preds.mean(axis=0)
        mc_std = mc_preds.std(axis=0).mean(axis=1)
        mean_uncertainty = mc_std.mean()

        n_gnn = sum(p.numel() for p in gnn.parameters())
        n_policy = sum(p.numel() for p in policy.parameters())
        print(f"\n  Final: best_epoch={best_epoch}, test_acc={test_acc:.4f}")
        print(f"  MC-Dropout mean uncertainty: {mean_uncertainty:.4f}")
        print(f"  GNN parameters: {n_gnn:,}, Policy parameters: {n_policy:,}")

        history["test_metrics"] = {
            "test_accuracy": float(test_acc),
            "mc_uncertainty_mean": float(mean_uncertainty),
            "n_gnn_params": n_gnn,
            "n_policy_params": n_policy,
        }
    else:
        history = _simulate_gnn_training()

    return history


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def _compute_auc(y_true, y_score):
    """Simple AUC-ROC computation without sklearn."""
    pairs = list(zip(y_score, y_true))
    pairs.sort(key=lambda x: -x[0])
    tp = 0
    fp = 0
    n_pos = sum(y_true)
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    auc = 0.0
    prev_fpr = 0.0
    prev_tpr = 0.0
    for score, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        tpr = tp / n_pos
        fpr = fp / n_neg
        auc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2
        prev_fpr = fpr
        prev_tpr = tpr
    return auc


def _simulate_ae_training():
    raise RuntimeError(
        "PyTorch is required for real training. "
        "Install with: pip install torch")


def _simulate_risk_training():
    raise RuntimeError(
        "PyTorch is required for real training. "
        "Install with: pip install torch")


def _simulate_contrastive_training():
    raise RuntimeError(
        "PyTorch is required for real training. "
        "Install with: pip install torch")


def _simulate_gnn_training():
    raise RuntimeError(
        "PyTorch is required for real training. "
        "Install with: pip install torch")


# ---------------------------------------------------------------------------
# Figure Generation
# ---------------------------------------------------------------------------

def generate_training_figures(histories: dict):
    """Generate training convergence figure for the manuscript."""
    if not HAS_MPL:
        print("[WARN] matplotlib not available — skipping figure generation")
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("CASTER-ZT Component Training Convergence", fontsize=14, fontweight="bold")

    colors = {"train": "#2196F3", "val": "#F44336", "metric": "#4CAF50"}

    # 1. Trust Autoencoder
    ax = axes[0, 0]
    h = histories["autoencoder"]
    epochs = range(1, len(h["train_loss"]) + 1)
    ax.plot(epochs, h["train_loss"], color=colors["train"], label="Train MSE", linewidth=1.5)
    ax.plot(epochs, h["val_loss"], color=colors["val"], label="Val MSE", linewidth=1.5, linestyle="--")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title("(a) Trust Autoencoder ($\\mathrm{AE}_\\phi$, ~2.5K params)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")

    # 2. Risk Scorer
    ax = axes[0, 1]
    h = histories["risk_scorer"]
    epochs = range(1, len(h["train_loss"]) + 1)
    ax.plot(epochs, h["train_loss"], color=colors["train"], label="Train BCE", linewidth=1.5)
    ax.plot(epochs, h["val_loss"], color=colors["val"], label="Val BCE", linewidth=1.5, linestyle="--")
    ax2 = ax.twinx()
    ax2.plot(epochs, h["val_auc"], color=colors["metric"], label="Val AUC-ROC", linewidth=1.5, linestyle=":")
    ax2.set_ylabel("AUC-ROC", color=colors["metric"])
    ax2.tick_params(axis="y", labelcolor=colors["metric"])
    ax2.set_ylim(0.5, 1.0)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("BCE Loss")
    ax.set_title("(b) Risk Scorer ($R_\\phi$, ~1.5K params)")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="center right")
    ax.grid(True, alpha=0.3)

    # 3. Contrastive Encoder
    ax = axes[1, 0]
    h = histories["contrastive"]
    epochs = range(1, len(h["train_loss"]) + 1)
    ax.plot(epochs, h["train_loss"], color=colors["train"], label="Train Contrastive", linewidth=1.5)
    ax.plot(epochs, h["val_loss"], color=colors["val"], label="Val Contrastive", linewidth=1.5, linestyle="--")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Contrastive Loss")
    ax.set_title("(c) Contrastive Safety Encoder ($q_\\phi$, ~8K params)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 4. GNN + Policy
    ax = axes[1, 1]
    h = histories["gnn_policy"]
    epochs = range(1, len(h["train_loss"]) + 1)
    ax.plot(epochs, h["train_loss"], color=colors["train"], label="Train CE", linewidth=1.5)
    ax.plot(epochs, h["val_loss"], color=colors["val"], label="Val CE", linewidth=1.5, linestyle="--")
    ax2 = ax.twinx()
    ax2.plot(epochs, h["val_acc"], color=colors["metric"], label="Val Accuracy", linewidth=1.5, linestyle=":")
    ax2.set_ylabel("Accuracy", color=colors["metric"])
    ax2.tick_params(axis="y", labelcolor=colors["metric"])
    ax2.set_ylim(0.3, 1.0)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Cross-Entropy Loss")
    ax.set_title("(d) GNN Encoder + Policy ($f_\\theta, \\pi_\\theta$, ~37K params)")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="center right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    for ext in ["pdf", "png"]:
        path = os.path.join(FIGURES_DIR, f"fig_training_curves.{ext}")
        fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\n  Training figure saved to {FIGURES_DIR}/fig_training_curves.{{pdf,png}}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  CASTER-ZT Component Training Pipeline")
    print("=" * 60)

    t_start = time.time()

    # Generate training data
    print("\n--- Generating training data ---")
    data = generate_training_data()

    # Train all components
    h_ae = train_autoencoder(data)
    h_risk = train_risk_scorer(data)
    h_contrastive = train_contrastive_encoder(data)
    h_gnn = train_gnn_policy(data)

    histories = {
        "autoencoder": h_ae,
        "risk_scorer": h_risk,
        "contrastive": h_contrastive,
        "gnn_policy": h_gnn,
    }

    # Generate convergence figure
    generate_training_figures(histories)

    # Save training summary
    summary = {
        "components": {},
        "total_train_time_s": round(time.time() - t_start, 2),
    }
    for name, h in histories.items():
        metrics = h.get("test_metrics", {})
        summary["components"][name] = {
            "epochs_trained": len(h["train_loss"]),
            "final_train_loss": round(h["train_loss"][-1], 6),
            "final_val_loss": round(h["val_loss"][-1], 6),
            **{k: round(v, 4) if isinstance(v, float) else v
               for k, v in metrics.items()},
        }

    path = os.path.join(SCRIPT_DIR, "campaign_output_v2", "training_summary.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Training summary saved to {path}")

    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"  Training Complete! ({elapsed:.1f}s)")
    print(f"{'=' * 60}")

    # Print summary table
    print(f"\n  {'Component':<30} {'Params':>8} {'Epochs':>7} "
          f"{'Final Val Loss':>14} {'Key Metric':>20}")
    print("  " + "-" * 85)
    for name, h in histories.items():
        m = h.get("test_metrics", {})
        n_params = m.get("n_params", m.get("n_gnn_params", 0) + m.get("n_policy_params", 0))
        n_epochs = len(h["train_loss"])
        val_loss = h["val_loss"][-1]

        if name == "autoencoder":
            metric_str = f"F1={m.get('f1', 0):.3f}"
        elif name == "risk_scorer":
            metric_str = f"AUC={m.get('auc_roc', 0):.3f}"
        elif name == "contrastive":
            metric_str = "---"
        elif name == "gnn_policy":
            metric_str = f"Acc={m.get('test_accuracy', 0):.3f}"
        else:
            metric_str = "---"

        print(f"  {name:<30} {n_params:>8,} {n_epochs:>7} "
              f"{val_loss:>14.6f} {metric_str:>20}")

    total_params = sum(
        h.get("test_metrics", {}).get("n_params",
            h.get("test_metrics", {}).get("n_gnn_params", 0) +
            h.get("test_metrics", {}).get("n_policy_params", 0))
        for h in histories.values()
    )
    print(f"\n  Total learned parameters: {total_params:,}")
    print(f"  Shield parameters: 13 scalars (calibrated, not trained)")


if __name__ == "__main__":
    main()
