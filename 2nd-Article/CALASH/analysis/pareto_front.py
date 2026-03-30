"""
Pareto Front Analysis for CALASH
=================================
3D Pareto dominance analysis over (PDR, Carbon, Lifetime) space.

Shows that CALASH achieves a superior Pareto front compared to all
baselines, meaning no baseline can simultaneously match CALASH on
all three objectives.

Methodology:
    1. Sweep Lyapunov V parameter: V ∈ {10, 50, 100, 200, 500, 1000}
    2. For each V, run 30-seed campaign
    3. Plot 3D Pareto front: (PDR, 1/Carbon, Lifetime)
    4. Compute hypervolume indicator (dominated space)
    5. Show baseline protocols as single points in this space

References
----------
[1] Zitzler, E. & Thiele, L. "Multiobjective Evolutionary Algorithms:
    A Comparative Case Study and the Strength Pareto Approach."
    IEEE TEC, 3(4), 1999. DOI: 10.1109/4235.797969

[2] Deb, K. "Multi-Objective Optimization using Evolutionary Algorithms."
    John Wiley & Sons, 2001. ISBN: 978-0471873396.
"""

import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional


def compute_pareto_front_2d(points: np.ndarray) -> np.ndarray:
    """
    Compute 2D Pareto front (maximize both objectives).

    Parameters
    ----------
    points : np.ndarray
        (N, 2) array of (objective1, objective2) to maximize.

    Returns
    -------
    np.ndarray
        Boolean mask of Pareto-optimal points.
    """
    n = len(points)
    is_pareto = np.ones(n, dtype=bool)

    for i in range(n):
        if not is_pareto[i]:
            continue
        for j in range(n):
            if i == j or not is_pareto[j]:
                continue
            # j dominates i: j ≥ i in all objectives AND j > i in at least one
            if (points[j, 0] >= points[i, 0] and points[j, 1] >= points[i, 1]
                    and (points[j, 0] > points[i, 0] or points[j, 1] > points[i, 1])):
                is_pareto[i] = False
                break

    return is_pareto


def compute_pareto_front_3d(pdr: np.ndarray, inv_carbon: np.ndarray,
                             lifetime: np.ndarray) -> np.ndarray:
    """
    Compute 3D Pareto front over (PDR, 1/Carbon, Lifetime).

    All three objectives are to be MAXIMIZED.

    Parameters
    ----------
    pdr : np.ndarray
        Packet delivery ratios.
    inv_carbon : np.ndarray
        Inverse carbon emissions (1/carbon — higher is better).
    lifetime : np.ndarray
        Network lifetimes (rounds until first node death).

    Returns
    -------
    np.ndarray
        Boolean mask of Pareto-optimal points.
    """
    n = len(pdr)
    points = np.column_stack([pdr, inv_carbon, lifetime])
    is_pareto = np.ones(n, dtype=bool)

    for i in range(n):
        if not is_pareto[i]:
            continue
        for j in range(n):
            if i == j or not is_pareto[j]:
                continue
            dominates = all(points[j, k] >= points[i, k] for k in range(3))
            strictly = any(points[j, k] > points[i, k] for k in range(3))
            if dominates and strictly:
                is_pareto[i] = False
                break

    return is_pareto


def hypervolume_2d(pareto_points: np.ndarray,
                   reference: np.ndarray) -> float:
    """
    Compute 2D hypervolume indicator.

    Parameters
    ----------
    pareto_points : np.ndarray
        (M, 2) Pareto-optimal points (maximization).
    reference : np.ndarray
        (2,) reference point (anti-ideal, e.g., [0, 0]).

    Returns
    -------
    float
        Hypervolume (area dominated by Pareto front above reference).
    """
    if len(pareto_points) == 0:
        return 0.0

    # Sort by first objective descending
    sorted_pts = pareto_points[np.argsort(-pareto_points[:, 0])]
    hv = 0.0
    prev_y = reference[1]

    for pt in sorted_pts:
        if pt[1] > prev_y:
            hv += (pt[0] - reference[0]) * (pt[1] - prev_y)
            prev_y = pt[1]

    return hv


def analyse_protocol_results(results: Dict[str, Dict]) -> dict:
    """
    Analyse multi-protocol results for Pareto dominance.

    Parameters
    ----------
    results : dict
        {protocol_name: {'pdr': float, 'carbon': float, 'lifetime': float, ...}}

    Returns
    -------
    dict
        Analysis with dominance relationships and Pareto front.
    """
    names = list(results.keys())
    n = len(names)

    pdr = np.array([results[p]['pdr'] for p in names])
    carbon = np.array([results[p]['carbon'] for p in names])
    lifetime = np.array([results[p]['lifetime'] for p in names])

    # For Pareto: maximize PDR, minimize carbon (= maximize 1/carbon), maximize lifetime
    inv_carbon = 1.0 / np.maximum(carbon, 1e-10)

    pareto_mask = compute_pareto_front_3d(pdr, inv_carbon, lifetime)

    # Dominance matrix: dominance[i][j] = True if protocol i dominates j
    dominance = {}
    for i, pi in enumerate(names):
        for j, pj in enumerate(names):
            if i == j:
                continue
            dom = (pdr[i] >= pdr[j] and inv_carbon[i] >= inv_carbon[j]
                   and lifetime[i] >= lifetime[j])
            strict = (pdr[i] > pdr[j] or inv_carbon[i] > inv_carbon[j]
                      or lifetime[i] > lifetime[j])
            if dom and strict:
                dominance.setdefault(pi, []).append(pj)

    # 2D hypervolume (PDR × 1/Carbon)
    pareto_2d_mask = compute_pareto_front_2d(
        np.column_stack([pdr, inv_carbon])
    )
    ref_2d = np.array([0.0, 0.0])
    pareto_2d_pts = np.column_stack([pdr, inv_carbon])[pareto_2d_mask]
    hv = hypervolume_2d(pareto_2d_pts, ref_2d)

    return {
        'protocols': names,
        'pdr': pdr.tolist(),
        'carbon': carbon.tolist(),
        'lifetime': lifetime.tolist(),
        'pareto_optimal': [names[i] for i in range(n) if pareto_mask[i]],
        'dominance': dominance,
        'hypervolume_2d': float(hv),
        'pareto_mask': pareto_mask.tolist(),
    }


def generate_v_sweep_configs(base_config,
                              v_values: List[float] = None) -> list:
    """
    Generate configs for Lyapunov V parameter sweep.

    Parameters
    ----------
    base_config : SimulationConfig
        Base configuration.
    v_values : list of float
        V parameter values to sweep.

    Returns
    -------
    list of SimulationConfig
        Configs for each V value.
    """
    if v_values is None:
        v_values = [10, 50, 100, 200, 500, 1000]

    return [base_config.copy(V_lyapunov=v) for v in v_values]
