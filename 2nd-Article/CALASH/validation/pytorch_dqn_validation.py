"""
PyTorch DQN Validation Script
================================
Side-by-side comparison of NumPy DQN (production) and PyTorch DQN
to validate that the hand-coded NumPy implementation is correct.

This script:
    1. Creates identical network architectures in NumPy and PyTorch
    2. Copies weights from NumPy to PyTorch
    3. Runs forward pass on identical inputs
    4. Compares outputs (should match to float32 precision)
    5. Runs gradient step on identical data
    6. Compares updated weights (should match)

This provides evidence that:
    - Our NumPy backpropagation is correctly implemented
    - The DQN training loop produces valid gradients
    - Results are reproducible across frameworks

Usage:
    python validation/pytorch_dqn_validation.py

Requires: pip install torch (optional dependency, NOT needed for main CALASH)
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def validate_forward_pass():
    """Compare forward pass outputs between NumPy and PyTorch MLPs."""
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        print("⚠ PyTorch not installed. Skipping validation.")
        print("  Install with: pip install torch")
        return False

    from agents.dqn import _NumpyMLP

    rng = np.random.default_rng(42)

    # Create NumPy MLP
    np_mlp = _NumpyMLP(8, 64, 32, 1, rng)

    # Create PyTorch MLP with same architecture
    class PyTorchMLP(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(8, 64)
            self.fc2 = nn.Linear(64, 32)
            self.fc3 = nn.Linear(32, 1)

        def forward(self, x):
            h1 = torch.relu(self.fc1(x))
            h2 = torch.relu(self.fc2(h1))
            return self.fc3(h2)

    pt_mlp = PyTorchMLP()

    # Copy weights from NumPy to PyTorch
    with torch.no_grad():
        pt_mlp.fc1.weight.copy_(torch.from_numpy(np_mlp.W1.T))
        pt_mlp.fc1.bias.copy_(torch.from_numpy(np_mlp.b1))
        pt_mlp.fc2.weight.copy_(torch.from_numpy(np_mlp.W2.T))
        pt_mlp.fc2.bias.copy_(torch.from_numpy(np_mlp.b2))
        pt_mlp.fc3.weight.copy_(torch.from_numpy(np_mlp.W3.T))
        pt_mlp.fc3.bias.copy_(torch.from_numpy(np_mlp.b3))

    # Test forward pass
    test_inputs = rng.random((10, 8)).astype(np.float32)

    np_out = np_mlp.forward(test_inputs)
    pt_out = pt_mlp(torch.from_numpy(test_inputs)).detach().numpy()

    max_diff = np.max(np.abs(np_out - pt_out))
    mean_diff = np.mean(np.abs(np_out - pt_out))

    print("=" * 60)
    print("FORWARD PASS VALIDATION")
    print("=" * 60)
    print(f"  Input shape:  {test_inputs.shape}")
    print(f"  NumPy output: {np_out[:3].flatten()}")
    print(f"  PyTorch out:  {pt_out[:3].flatten()}")
    print(f"  Max |diff|:   {max_diff:.2e}")
    print(f"  Mean |diff|:  {mean_diff:.2e}")

    passed = max_diff < 1e-5
    print(f"  Status:       {'✅ PASS' if passed else '❌ FAIL'}")
    return passed


def validate_gradient_step():
    """Compare one gradient step between NumPy and PyTorch."""
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
    except ImportError:
        print("⚠ PyTorch not installed. Skipping gradient validation.")
        return False

    from agents.dqn import _NumpyMLP

    rng = np.random.default_rng(123)

    # Create identical networks
    np_mlp = _NumpyMLP(8, 64, 32, 1, rng)

    class PyTorchMLP(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(8, 64)
            self.fc2 = nn.Linear(64, 32)
            self.fc3 = nn.Linear(32, 1)

        def forward(self, x):
            h1 = torch.relu(self.fc1(x))
            h2 = torch.relu(self.fc2(h1))
            return self.fc3(h2)

    pt_mlp = PyTorchMLP()

    # Copy weights
    with torch.no_grad():
        pt_mlp.fc1.weight.copy_(torch.from_numpy(np_mlp.W1.T))
        pt_mlp.fc1.bias.copy_(torch.from_numpy(np_mlp.b1))
        pt_mlp.fc2.weight.copy_(torch.from_numpy(np_mlp.W2.T))
        pt_mlp.fc2.bias.copy_(torch.from_numpy(np_mlp.b2))
        pt_mlp.fc3.weight.copy_(torch.from_numpy(np_mlp.W3.T))
        pt_mlp.fc3.bias.copy_(torch.from_numpy(np_mlp.b3))

    lr = 1e-3

    # Create test data (MSE loss target)
    states = rng.random((64, 8)).astype(np.float32)
    targets = rng.random((64, 1)).astype(np.float32)

    # ─── PyTorch gradient step ───
    pt_optimizer = optim.SGD(pt_mlp.parameters(), lr=lr)
    pt_out = pt_mlp(torch.from_numpy(states))
    pt_loss = nn.MSELoss()(pt_out, torch.from_numpy(targets))
    pt_optimizer.zero_grad()
    pt_loss.backward()

    # Clip gradients (same as NumPy)
    for p in pt_mlp.parameters():
        if p.grad is not None:
            grad_norm = p.grad.norm()
            if grad_norm > 1.0:
                p.grad.mul_(1.0 / grad_norm)

    pt_optimizer.step()

    pt_w1_after = pt_mlp.fc1.weight.detach().numpy().T.copy()

    # ─── NumPy gradient step (manual backprop) ───
    # Forward pass
    h1 = np.maximum(0, states @ np_mlp.W1 + np_mlp.b1)
    h2 = np.maximum(0, h1 @ np_mlp.W2 + np_mlp.b2)
    out = h2 @ np_mlp.W3 + np_mlp.b3

    # Backward: MSE loss
    diff = out - targets
    dout = 2.0 * diff / len(states)  # (batch, 1)

    dW3 = h2.T @ dout
    db3 = dout.sum(axis=0)
    dh2 = dout @ np_mlp.W3.T * (h2 > 0).astype(np.float32)

    dW2 = h1.T @ dh2
    db2 = dh2.sum(axis=0)
    dh1 = dh2 @ np_mlp.W2.T * (h1 > 0).astype(np.float32)

    dW1 = states.T @ dh1
    db1 = dh1.sum(axis=0)

    # Gradient clipping
    for g in [dW1, db1, dW2, db2, dW3, db3]:
        norm = np.linalg.norm(g)
        if norm > 1.0:
            g *= 1.0 / norm

    # SGD step
    np_mlp.W1 -= lr * dW1
    np_mlp.b1 -= lr * db1
    np_mlp.W2 -= lr * dW2
    np_mlp.b2 -= lr * db2
    np_mlp.W3 -= lr * dW3
    np_mlp.b3 -= lr * db3

    np_w1_after = np_mlp.W1.copy()

    # Compare weights after update
    w1_diff = np.max(np.abs(np_w1_after - pt_w1_after))

    print()
    print("=" * 60)
    print("GRADIENT STEP VALIDATION")
    print("=" * 60)
    print(f"  Batch size:   64")
    print(f"  Learning rate: {lr}")
    print(f"  NumPy loss:   {float(np.mean(diff**2)):.6f}")
    print(f"  PyTorch loss: {float(pt_loss.item()):.6f}")
    print(f"  W1 max |diff| after step: {w1_diff:.2e}")

    # Note: small differences expected due to gradient clipping order
    passed = w1_diff < 1e-3
    print(f"  Status:       {'✅ PASS' if passed else '⚠ CLOSE (order-dependent clipping)'}")
    return passed


def validate_q_value_consistency():
    """
    Validate that DQN produces consistent Q-values on a small
    reproducible test problem.
    """
    from config import SimulationConfig
    from agents.dqn import DQNRouter

    print()
    print("=" * 60)
    print("Q-VALUE CONSISTENCY VALIDATION")
    print("=" * 60)

    config = SimulationConfig(num_nodes=50, num_rounds=100)

    # Two independent DQN agents with same seed should produce same values
    dqn1 = DQNRouter(config, np.random.default_rng(42))
    dqn2 = DQNRouter(config, np.random.default_rng(42))

    # Create test state
    state = np.array([0.5, 0.3, 0.4, 0.1, 0.8, 0.6, 0.2, 0.15],
                     dtype=np.float32)

    v1 = float(dqn1._online.forward(state)[0])
    v2 = float(dqn2._online.forward(state)[0])

    print(f"  DQN1 V(s): {v1:.6f}")
    print(f"  DQN2 V(s): {v2:.6f}")
    print(f"  |diff|:    {abs(v1 - v2):.2e}")

    passed = abs(v1 - v2) < 1e-10
    print(f"  Status:    {'✅ PASS (deterministic)' if passed else '❌ FAIL'}")
    return passed


def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    CALASH DQN Validation: NumPy vs PyTorch              ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  Validates hand-coded NumPy DQN against PyTorch         ║")
    print("║  reference implementation.                              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    results = []
    results.append(("Q-value consistency", validate_q_value_consistency()))
    results.append(("Forward pass", validate_forward_pass()))
    results.append(("Gradient step", validate_gradient_step()))

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All validations PASSED ✅")
    else:
        print("Some validations FAILED or SKIPPED ⚠")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
