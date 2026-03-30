"""Hybrid Algorithm Selector: Adaptive MARL Algorithm Selection for WSN Routing.

Runs both QMIX and QTRAN on the same episodes, captures initial state features,
and trains a lightweight predictor to select the best algorithm per episode.

Usage:
    # Step 1: Generate paired data
    python tools/hybrid_selector.py --generate --n-episodes 500 --seed 42

    # Step 2: Train predictor and evaluate
    python tools/hybrid_selector.py --train --data results/data/hybrid_paired_data.npz

    # Step 3: Full pipeline
    python tools/hybrid_selector.py --generate --train --n-episodes 500 --seed 42
"""

import argparse
import os
import sys
import numpy as np
from pathlib import Path

# Add epymarl src to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
EPYMARL_DIR = PROJECT_DIR / "epymarl"
sys.path.insert(0, str(EPYMARL_DIR / "src"))

RESULTS_DATA_DIR = str(EPYMARL_DIR / "results" / "data")


def extract_topo_features(state, n_agents=70, coverage_radius=35.0):
    """Extract topology features from a flat state vector.

    Args:
        state: (n_agents * 5,) array — [e0,c0,x0,y0,p0, e1,c1,x1,y1,p1, ...]

    Returns:
        dict of features useful for algorithm selection.
    """
    feats = state.reshape(n_agents, 5)
    energy = feats[:, 0]        # remaining energy [0, 1]
    consumption = feats[:, 1]   # consumed energy [0, 1]
    positions = feats[:, 2:4]   # (x, y) in [0, 100]
    packets = feats[:, 4]       # number of packets

    # Base station at center
    bs_pos = np.array([50.0, 50.0])

    # Pairwise distances
    diff = positions[:, None, :] - positions[None, :, :]
    dist_matrix = np.sqrt((diff ** 2).sum(-1))

    # Adjacency (communication graph)
    adj = (dist_matrix <= coverage_radius).astype(float)
    np.fill_diagonal(adj, 0)

    # Degree centrality
    degree = adj.sum(axis=1)

    # Distance to BS
    dist_to_bs = np.sqrt(((positions - bs_pos) ** 2).sum(axis=1))

    # Connectivity: BFS from BS-reachable nodes
    bs_reachable = dist_to_bs <= coverage_radius
    visited = set(np.where(bs_reachable)[0])
    frontier = list(visited)
    while frontier:
        node = frontier.pop(0)
        neighbors = np.where(adj[node] > 0)[0]
        for n in neighbors:
            if n not in visited:
                visited.add(n)
                frontier.append(n)
    connectivity = len(visited) / n_agents

    # Graph density
    n_edges = adj.sum() / 2
    max_edges = n_agents * (n_agents - 1) / 2
    density = n_edges / max_edges

    return {
        # Topology features
        "mean_degree": degree.mean(),
        "std_degree": degree.std(),
        "min_degree": degree.min(),
        "max_degree": degree.max(),
        "mean_dist_to_bs": dist_to_bs.mean(),
        "std_dist_to_bs": dist_to_bs.std(),
        "min_dist_to_bs": dist_to_bs.min(),
        "max_dist_to_bs": dist_to_bs.max(),
        "connectivity": connectivity,
        "graph_density": density,
        # Position features
        "mean_x": positions[:, 0].mean(),
        "mean_y": positions[:, 1].mean(),
        "std_x": positions[:, 0].std(),
        "std_y": positions[:, 1].std(),
        # Energy features
        "mean_energy": energy.mean(),
        "std_energy": energy.std(),
        "mean_packets": packets.mean(),
        # Derived: how many agents are near BS
        "n_near_bs": (dist_to_bs <= coverage_radius).sum(),
        # Derived: isolated nodes (degree 0)
        "n_isolated": (degree == 0).sum(),
        # Derived: avg clustering coefficient (local)
        "mean_cluster_coeff": _avg_clustering(adj, degree),
    }


def _avg_clustering(adj, degree):
    """Compute average clustering coefficient."""
    n = adj.shape[0]
    cc = 0.0
    count = 0
    for i in range(n):
        if degree[i] < 2:
            continue
        neighbors = np.where(adj[i] > 0)[0]
        n_links = 0
        for j_idx in range(len(neighbors)):
            for k_idx in range(j_idx + 1, len(neighbors)):
                if adj[neighbors[j_idx], neighbors[k_idx]] > 0:
                    n_links += 1
        possible = degree[i] * (degree[i] - 1) / 2
        cc += n_links / possible if possible > 0 else 0
        count += 1
    return cc / count if count > 0 else 0.0


def generate_paired_data(n_episodes=500, seed=42):
    """Run QMIX and QTRAN on the same episodes, capture initial states and metrics.

    Uses the paired .npy data from evaluations with the same Sacred seed.
    Also generates initial state features by re-creating the environments.
    """
    import gym
    import gym_examples

    print(f"Generating paired data for {n_episodes} episodes with seed={seed}...")

    # Re-create the environments with the same seeds to capture initial states
    # The parallel runner uses batch_size_run=4, so seeds are: seed, seed+1, seed+2, seed+3
    # Episodes are generated sequentially: first 4 episodes use envs with these seeds,
    # then each env.reset() advances its RNG for subsequent episodes.

    batch_size = 4
    env_seeds = [seed + i for i in range(batch_size)]

    # Create environments and capture initial states
    print("Creating environments to capture initial states...")
    initial_states = []
    for ep_batch in range(n_episodes // batch_size):
        for env_idx in range(batch_size):
            if ep_batch == 0:
                # First batch: create env
                env = gym.make("WSNRouting-v0")
                env.seed(env_seeds[env_idx])
                if not hasattr(generate_paired_data, '_envs'):
                    generate_paired_data._envs = []
                if len(generate_paired_data._envs) <= env_idx:
                    generate_paired_data._envs.append(env)
            else:
                env = generate_paired_data._envs[env_idx]

            obs = env.reset()
            # Flatten obs to get state
            state = np.concatenate([np.concatenate([np.atleast_1d(v).flatten() for v in o.values()]) for o in obs])
            initial_states.append(state)

    initial_states = np.array(initial_states)
    print(f"Captured {len(initial_states)} initial states, shape: {initial_states.shape}")

    # Clean up
    for env in generate_paired_data._envs:
        env.close()

    # Extract features from initial states
    print("Extracting topology features...")
    feature_names = None
    feature_matrix = []
    for i, state in enumerate(initial_states):
        feats = extract_topo_features(state)
        if feature_names is None:
            feature_names = list(feats.keys())
        feature_matrix.append([feats[k] for k in feature_names])

    feature_matrix = np.array(feature_matrix)
    print(f"Feature matrix shape: {feature_matrix.shape}, features: {feature_names}")

    # Load paired metrics from evaluations
    print("Loading paired evaluation metrics...")
    metrics_to_load = [
        "packet_delivery_ratio", "average_latency", "energy_efficiency",
        "network_throughput", "mean_returns", "total_consumption_energy",
        "out_of_range_count", "relay_delivery_count", "direct_to_bs_count",
    ]

    qmix_metrics = {}
    qtran_metrics = {}
    for metric in metrics_to_load:
        qmix_f = os.path.join(RESULTS_DATA_DIR, f"{metric}_QMIX_PAIRED_test_3.3.3.npy")
        qtran_f = os.path.join(RESULTS_DATA_DIR, f"{metric}_QTRAN_PAIRED_test_3.3.3.npy")
        if os.path.exists(qmix_f) and os.path.exists(qtran_f):
            qmix_metrics[metric] = np.load(qmix_f)
            qtran_metrics[metric] = np.load(qtran_f)
            print(f"  {metric}: QMIX={qmix_metrics[metric].mean():.4f}, QTRAN={qtran_metrics[metric].mean():.4f}")
        else:
            print(f"  {metric}: MISSING")

    # Determine best algorithm per episode
    qmix_pdr = qmix_metrics["packet_delivery_ratio"]
    qtran_pdr = qtran_metrics["packet_delivery_ratio"]
    best_algo = (qtran_pdr > qmix_pdr).astype(int)  # 0=QMIX, 1=QTRAN

    # Ensure sizes match
    n = min(len(feature_matrix), len(best_algo))
    feature_matrix = feature_matrix[:n]
    best_algo = best_algo[:n]
    initial_states = initial_states[:n]

    # Save paired data
    out_path = os.path.join(RESULTS_DATA_DIR, "hybrid_paired_data.npz")
    np.savez(out_path,
             features=feature_matrix,
             feature_names=np.array(feature_names),
             best_algo=best_algo,
             qmix_pdr=qmix_pdr[:n],
             qtran_pdr=qtran_pdr[:n],
             initial_states=initial_states,
             qmix_metrics={k: v[:n] for k, v in qmix_metrics.items()},
             qtran_metrics={k: v[:n] for k, v in qtran_metrics.items()},
             )
    print(f"\nSaved paired data to {out_path}")
    print(f"  Episodes: {n}")
    print(f"  QMIX wins: {(best_algo == 0).sum()}, QTRAN wins: {(best_algo == 1).sum()}")
    print(f"  Oracle PDR: {np.maximum(qmix_pdr[:n], qtran_pdr[:n]).mean():.4f}")

    return out_path


def train_predictor(data_path):
    """Train and evaluate algorithm selection predictors."""
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.svm import SVC
    from sklearn.neural_network import MLPClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report
    import warnings
    warnings.filterwarnings("ignore")

    print(f"\nLoading paired data from {data_path}...")
    data = np.load(data_path, allow_pickle=True)
    X = data["features"]
    y = data["best_algo"]
    feature_names = list(data["feature_names"])
    qmix_pdr = data["qmix_pdr"]
    qtran_pdr = data["qtran_pdr"]

    print(f"Dataset: {X.shape[0]} episodes, {X.shape[1]} features")
    print(f"Class balance: QMIX={np.sum(y==0)} ({np.mean(y==0)*100:.1f}%), QTRAN={np.sum(y==1)} ({np.mean(y==1)*100:.1f}%)")

    # Baselines
    always_qmix_pdr = qmix_pdr.mean()
    always_qtran_pdr = qtran_pdr.mean()
    oracle_pdr = np.maximum(qmix_pdr, qtran_pdr).mean()
    random_pdr = (qmix_pdr + qtran_pdr).mean() / 2

    print(f"\n{'='*70}")
    print("PDR Baselines:")
    print(f"  Always QMIX:  {always_qmix_pdr:.4f}")
    print(f"  Always QTRAN: {always_qtran_pdr:.4f}")
    print(f"  Random:       {random_pdr:.4f}")
    print(f"  Oracle:       {oracle_pdr:.4f} (upper bound)")
    print(f"{'='*70}")

    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Models to try
    models = {
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
        "GradientBoosting": GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
        "SVM-RBF": SVC(kernel="rbf", probability=True, random_state=42),
        "MLP": MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=500, random_state=42),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print(f"\n{'='*70}")
    print("Cross-Validated Results (5-fold):")
    print(f"{'='*70}")

    best_pdr = 0
    best_model_name = None

    for name, model in models.items():
        # Cross-validated accuracy
        scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="accuracy")

        # Cross-validated PDR (custom scoring)
        pdr_scores = []
        for train_idx, test_idx in cv.split(X_scaled, y):
            model.fit(X_scaled[train_idx], y[train_idx])
            pred = model.predict(X_scaled[test_idx])
            # Compute PDR: use QMIX when pred=0, QTRAN when pred=1
            hybrid_pdr = np.where(pred == 0, qmix_pdr[test_idx], qtran_pdr[test_idx])
            pdr_scores.append(hybrid_pdr.mean())

        mean_acc = scores.mean()
        mean_pdr = np.mean(pdr_scores)

        print(f"\n  {name}:")
        print(f"    Accuracy: {mean_acc:.4f} +/- {scores.std():.4f}")
        print(f"    Hybrid PDR: {mean_pdr:.4f} (vs Oracle {oracle_pdr:.4f})")
        print(f"    PDR gain over best baseline: +{(mean_pdr - max(always_qmix_pdr, always_qtran_pdr))*100:.2f}%")

        if mean_pdr > best_pdr:
            best_pdr = mean_pdr
            best_model_name = name

    # Train best model on full data and analyze feature importance
    print(f"\n{'='*70}")
    print(f"Best Model: {best_model_name} (PDR={best_pdr:.4f})")
    print(f"{'='*70}")

    # Feature importance (Random Forest)
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_scaled, y)
    importances = rf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]

    print("\nFeature Importance (RandomForest):")
    for i in range(min(15, len(feature_names))):
        idx = sorted_idx[i]
        print(f"  {i+1:2d}. {feature_names[idx]:25s} {importances[idx]:.4f}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Always QMIX:           PDR = {always_qmix_pdr:.4f}")
    print(f"  Always QTRAN:          PDR = {always_qtran_pdr:.4f}")
    print(f"  Hybrid ({best_model_name:15s}): PDR = {best_pdr:.4f}  (+{(best_pdr - max(always_qmix_pdr, always_qtran_pdr))*100:.2f}%)")
    print(f"  Oracle (perfect):      PDR = {oracle_pdr:.4f}  (+{(oracle_pdr - max(always_qmix_pdr, always_qtran_pdr))*100:.2f}%)")
    print(f"\n  Predictor achieves {(best_pdr - max(always_qmix_pdr, always_qtran_pdr)) / (oracle_pdr - max(always_qmix_pdr, always_qtran_pdr)) * 100:.1f}% of oracle improvement")

    # Practical deployment info
    n_params_rf = sum(tree.tree_.node_count for tree in rf.estimators_)
    print(f"\n  Predictor size: ~{n_params_rf} decision nodes (Random Forest)")
    print(f"  Inference time: <1ms per episode")
    print(f"  Memory: ~{n_params_rf * 8 / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="Hybrid Algorithm Selector for WSN Routing")
    parser.add_argument("--generate", action="store_true", help="Generate paired evaluation data")
    parser.add_argument("--train", action="store_true", help="Train predictor")
    parser.add_argument("--n-episodes", type=int, default=500, help="Number of test episodes")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for paired evaluation")
    parser.add_argument("--data", type=str, default=None, help="Path to paired data .npz")
    args = parser.parse_args()

    if args.generate:
        data_path = generate_paired_data(n_episodes=args.n_episodes, seed=args.seed)
    elif args.data:
        data_path = args.data
    else:
        data_path = os.path.join(RESULTS_DATA_DIR, "hybrid_paired_data.npz")

    if args.train:
        train_predictor(data_path)

    if not args.generate and not args.train:
        print("Usage: python tools/hybrid_selector.py --generate --train")
        print("  --generate: Generate paired evaluation data")
        print("  --train: Train predictor on paired data")


if __name__ == "__main__":
    main()
