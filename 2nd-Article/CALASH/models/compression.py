"""
Compressive Sensing for Carbon-Aware Data Reduction (CADR)
==========================================================
Implements compressive sensing with a novel carbon-adaptive compression
ratio rho(t) that dynamically trades data fidelity for energy/carbon savings.

CADR formula (our contribution -- novel to CALASH):
    rho(t) = rho_max - (rho_max - rho_min) * (CI(t) - CI_min) / (CI_max - CI_min)

    When CI is HIGH -> rho -> rho_min (max compression, fewer Tx bits, lower carbon)
    When CI is LOW  -> rho -> rho_max (min compression, best data fidelity)

Compressive sensing pipeline:
    1. Measurement: y = Phi @ x, where Phi is m x n Gaussian random matrix,
       m = ceil(rho(t) * n), and x in R^n is s-sparse (or approx. sparse).
       Gaussian matrices satisfy the RIP with overwhelming probability [2].
    2. Reconstruction: Orthogonal Matching Pursuit (OMP) [3] recovers
       x_hat from y using at most s greedy iterations.
    3. Fidelity metric: NMSE = ||x - x_hat||^2 / ||x||^2.

Real-data support:
    When ``signal_source='real_intel_lab'``, signals are loaded from the
    Intel Berkeley Lab deployment [5] (54 Mica2 motes, temperature readings,
    Feb-Apr 2004). These are reconstructed in the DCT domain because real
    sensor signals are approximately 1-sparse in the DCT basis.

Theoretical guarantee (RIP, [1]):
    If Phi satisfies the Restricted Isometry Property of order 2s with
    constant delta_2s < sqrt(2) - 1, then OMP recovery satisfies:
        ||x - x_hat||_2 <= C * ||x - x_s||_1 / sqrt(s)
    where x_s is the best s-term approximation.

References
----------
[1] Candes, E.J., Romberg, J. & Tao, T. "Robust Uncertainty Principles:
    Exact Signal Reconstruction from Highly Incomplete Frequency Information."
    IEEE Trans. Information Theory, 52(2), pp. 489-509, 2006.
    DOI: 10.1109/TIT.2005.862083

[2] Baraniuk, R.G. "Compressive Sensing." IEEE Signal Processing
    Magazine, 24(4), pp. 118-121, 2007. DOI: 10.1109/MSP.2007.4286571

[3] Tropp, J.A. & Gilbert, A.C. "Signal Recovery From Random Measurements
    Via Orthogonal Matching Pursuit." IEEE Trans. Information Theory,
    53(12), pp. 4655-4666, 2007. DOI: 10.1109/TIT.2007.909108

[4] Haupt, J., Bajwa, W.U., Rabbat, M. & Nowak, R. "Compressed Sensing
    for Networked Data." IEEE Signal Processing Magazine, 25(2), 2008.
    DOI: 10.1109/MSP.2007.914732

[5] Madden, S. "Intel Lab Data." MIT CSAIL, 2004.
    http://db.csail.mit.edu/labdata/labdata.html
    (54 Mica2 motes, temperature/humidity/light/voltage, Feb-Apr 2004.)
"""

import numpy as np
from typing import Tuple, Optional
import warnings


class CompressiveSensing:
    """
    Compressive sensing encoder/decoder with carbon-adaptive compression.

    Uses Gaussian random measurement matrices and OMP reconstruction.
    Supports both synthetic sparse signals and real Intel Lab traces.
    """

    def __init__(self, config, rng: np.random.Generator = None,
                 signal_source: str = None):
        """
        Initialize compressive sensing module.

        Parameters
        ----------
        config : SimulationConfig
            Simulation configuration.
        rng : np.random.Generator
            Random number generator.
        signal_source : str, optional
            Override signal source: 'synthetic' or 'real_intel_lab'.
            If None, reads from config.signal_source.
        """
        self.n = config.signal_dim        # signal dimension
        self.s = config.sparsity          # sparsity level
        self.rho_min = config.rho_min     # minimum ratio (max compression)
        self.rho_max = config.rho_max     # maximum ratio (min compression)
        self.ci_min = config.ci_min
        self.ci_max = config.ci_max
        self.ci_base = getattr(config, 'ci_base', 200.0)  # reference CI
        self.rng = rng if rng is not None else np.random.default_rng(42)

        self.signal_source = signal_source or getattr(
            config, 'signal_source', 'synthetic'
        )
        self._real_loader = None  # lazy-loaded

        # Precompute NMSE lookup table for fast fidelity estimation
        if self.signal_source == 'real_intel_lab':
            self._nmse_lut = self._build_nmse_lookup_real(num_trials=20)
        else:
            self._nmse_lut = self._build_nmse_lookup(num_trials=20)

    def adaptive_compression_ratio(self, ci: float,
                                   is_critical: bool = False) -> float:
        """
        Compute carbon-adaptive compression ratio.

        HIGH CI → LOW ρ (more compression to save energy/carbon)
        LOW CI  → HIGH ρ (less compression for better fidelity)

        Uses reference-point mapping: ρ_mid = (ρ_min + ρ_max)/2
        occurs exactly at CI = ci_base (the grid's average intensity).
        This prevents systematic ρ inflation when ci_base is below
        the midpoint of [ci_min, ci_max].

        For critical disaster data: always use ρ_max (minimal compression).

        Parameters
        ----------
        ci : float
            Current carbon intensity (gCO2eq/kWh).
        is_critical : bool
            Whether this is critical disaster alert data.

        Returns
        -------
        float
            Compression ratio ρ = m/n in [ρ_min, ρ_max].
        """
        if is_critical:
            return self.rho_max  # minimal compression for critical data

        # Reference-point normalization: ci_base → 0.5, so ρ_mid at average CI
        rho_mid = (self.rho_min + self.rho_max) / 2.0
        if ci <= self.ci_base:
            # Below baseline: interpolate [ci_min, ci_base] → [rho_max, rho_mid]
            t = np.clip(
                (ci - self.ci_min) / max(self.ci_base - self.ci_min, 1.0), 0, 1
            )
            rho = self.rho_max - (self.rho_max - rho_mid) * t
        else:
            # Above baseline: interpolate [ci_base, ci_max] → [rho_mid, rho_min]
            t = np.clip(
                (ci - self.ci_base) / max(self.ci_max - self.ci_base, 1.0), 0, 1
            )
            rho = rho_mid - (rho_mid - self.rho_min) * t
        return rho

    def _build_nmse_lookup(self, num_trials: int = 20) -> dict:
        """
        Precompute average NMSE for discrete rho values.

        Runs OMP on random sparse signals to build a lookup table,
        eliminating the need for per-packet OMP during simulation.

        Returns
        -------
        dict
            {rho_quantized: mean_nmse}
        """
        lut = {}
        rho_values = np.arange(0.05, 1.01, 0.05)  # 5% steps
        trial_rng = np.random.default_rng(12345)  # fixed seed for reproducibility

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for rho in rho_values:
                m = max(1, int(rho * self.n))
                nmses = []
                for _ in range(num_trials):
                    # Generate random sparse signal
                    x = np.zeros(self.n)
                    support = trial_rng.choice(self.n, size=self.s, replace=False)
                    x[support] = trial_rng.standard_normal(self.s) * 10

                    # Encode + decode
                    Phi = trial_rng.standard_normal((m, self.n)) / np.sqrt(m)
                    y = Phi @ x
                    x_hat = self._fast_omp(y, Phi, self.s)
                    nmse = self.nmse(x, x_hat)
                    if not np.isnan(nmse) and not np.isinf(nmse):
                        nmses.append(nmse)

                lut[round(rho, 2)] = float(np.mean(nmses)) if nmses else 1.0

        return lut

    def _get_real_loader(self):
        """Lazy-load the RealIntelLabLoader."""
        if self._real_loader is None:
            from data.real_intel_lab import RealIntelLabLoader
            self._real_loader = RealIntelLabLoader(
                signal_dim=self.n, rng=self.rng
            )
        return self._real_loader

    def _build_nmse_lookup_real(self, num_trials: int = 20) -> dict:
        """
        Build NMSE lookup table using REAL Intel Lab temperature signals.

        Uses DCT sparsity basis (real environmental signals are sparse in
        the DCT domain, not the canonical basis). This is the standard
        approach in compressive sensing for sensor networks (Candes & Tao,
        2006; Haupt et al., 2008).

        The sensing matrix is Φ (random Gaussian), and the sparsity basis
        is the DCT matrix Ψ. We measure y = Φ·x, then recover the DCT
        coefficients θ = Ψ·x via OMP on the effective matrix Φ·Ψ^T,
        and reconstruct x = Ψ^T·θ.

        Parameters
        ----------
        num_trials : int
            Number of real signals to test per rho value.

        Returns
        -------
        dict
            {rho_quantized: mean_nmse}
        """
        loader = self._get_real_loader()
        lut = {}
        rho_values = np.arange(0.05, 1.01, 0.05)
        trial_rng = np.random.default_rng(12345)

        # DCT basis matrix (orthonormal): Ψ such that θ = Ψ @ x
        Psi = self._dct_matrix(self.n)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for rho in rho_values:
                m = max(1, int(rho * self.n))
                nmses = []
                for trial_i in range(num_trials):
                    # Get a REAL temperature signal from Intel Lab
                    x = loader.get_signal(sim_node_id=trial_i)

                    # Sensing: y = Φ · x
                    Phi = trial_rng.standard_normal((m, self.n)) / np.sqrt(m)
                    y = Phi @ x

                    # Effective matrix for DCT-domain OMP: A = Φ · Ψ^T
                    A = Phi @ Psi.T

                    # Recover DCT coefficients via OMP
                    theta_hat = self._fast_omp(y, A, self.s)

                    # Reconstruct signal: x_hat = Ψ^T · θ_hat
                    x_hat = Psi.T @ theta_hat

                    nmse = self.nmse(x, x_hat)
                    if not np.isnan(nmse) and not np.isinf(nmse):
                        nmses.append(nmse)

                lut[round(rho, 2)] = float(np.mean(nmses)) if nmses else 1.0

        return lut

    @staticmethod
    def _dct_matrix(n: int) -> np.ndarray:
        """
        Build orthonormal Type-II DCT matrix of size n×n.

        Avoids scipy dependency — pure NumPy implementation.
        Ψ[k,j] = α_k * cos(π·k·(2j+1) / (2n))
        """
        Psi = np.zeros((n, n))
        for k in range(n):
            for j in range(n):
                Psi[k, j] = np.cos(np.pi * k * (2 * j + 1) / (2 * n))
            if k == 0:
                Psi[k] *= np.sqrt(1.0 / n)
            else:
                Psi[k] *= np.sqrt(2.0 / n)
        return Psi

    def get_signal(self, sim_node_id: int = None,
                   hour: float = 12.0) -> np.ndarray:
        """
        Get a signal vector based on configured signal_source.

        Parameters
        ----------
        sim_node_id : int, optional
            Node ID for deterministic mapping to real data.
        hour : float
            Hour of day (for synthetic Intel Lab mode).

        Returns
        -------
        np.ndarray
            Signal of shape (signal_dim,).
        """
        if self.signal_source == 'real_intel_lab':
            loader = self._get_real_loader()
            return loader.get_signal(sim_node_id=sim_node_id)
        elif self.signal_source == 'intel_lab':
            return self.generate_intel_lab_signal(hour=hour)
        else:
            return self.generate_sparse_signal()

    def _fast_omp(self, y, Phi, sparsity):
        """Minimal OMP without warnings handling (for LUT building)."""
        m, n = Phi.shape
        sparsity = min(sparsity, m)
        residual = y.copy()
        support = []
        x_hat = np.zeros(n)

        for _ in range(sparsity):
            correlations = np.abs(Phi.T @ residual)
            for idx in support:
                correlations[idx] = -1
            best_idx = np.argmax(correlations)
            support.append(best_idx)

            Phi_s = Phi[:, support]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(Phi_s, y, rcond=None)
            except np.linalg.LinAlgError:
                break
            residual = y - Phi_s @ coeffs
            if np.linalg.norm(residual) < 1e-10:
                break

        if support:
            Phi_s = Phi[:, support]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(Phi_s, y, rcond=None)
                x_hat[support] = coeffs
            except np.linalg.LinAlgError:
                pass
        return x_hat

    def lookup_nmse(self, rho: float) -> float:
        """
        Fast NMSE lookup from precomputed table (O(1) instead of OMP).

        Parameters
        ----------
        rho : float
            Compression ratio.

        Returns
        -------
        float
            Expected NMSE for this compression ratio.
        """
        # Quantize to nearest 5%
        rho_q = round(round(rho / 0.05) * 0.05, 2)
        rho_q = max(0.05, min(1.0, rho_q))
        return self._nmse_lut.get(rho_q, 0.5)

    def generate_sparse_signal(self) -> np.ndarray:
        """
        Generate a random s-sparse signal of dimension n.
        Used for testing; real deployment uses actual sensor readings.

        Returns
        -------
        np.ndarray
            Sparse signal of shape (n,).
        """
        x = np.zeros(self.n)
        support = self.rng.choice(self.n, size=self.s, replace=False)
        x[support] = self.rng.standard_normal(self.s) * 10  # scale for realism
        return x

    def generate_realistic_signal(self, base_temp: float = 22.0,
                                  noise_std: float = 0.5) -> np.ndarray:
        """
        Generate a realistic environmental sensor signal.
        Approximately sparse in DCT domain (as real temp/humidity data is).

        Parameters
        ----------
        base_temp : float
            Base temperature value.
        noise_std : float
            Noise standard deviation.

        Returns
        -------
        np.ndarray
            Sensor signal of shape (n,).
        """
        t = np.linspace(0, 2 * np.pi, self.n)
        # Slow-varying temperature with a few harmonics (sparse in frequency)
        signal = base_temp + 3.0 * np.sin(t) + 1.5 * np.sin(2 * t)
        signal += 0.8 * np.sin(5 * t)
        signal += self.rng.normal(0, noise_std, self.n)
        return signal

    def generate_intel_lab_signal(self, modality: str = 'temperature',
                                  hour: float = 12.0) -> np.ndarray:
        """
        Generate a signal matching Intel Lab dataset statistics.

        Uses the IntelLabDataset generator for realistic sensor signals
        that are approximately sparse in DCT domain (~15-20%).

        Parameters
        ----------
        modality : str
            'temperature', 'humidity', 'light', or 'voltage'.
        hour : float
            Hour of day [0, 24) for diurnal pattern.

        Returns
        -------
        np.ndarray
            Sensor signal of shape (n,).
        """
        from data.intel_lab import IntelLabDataset
        dataset = IntelLabDataset(rng=self.rng)
        return dataset.generate_signal_vector(
            signal_dim=self.n, modality=modality, hour=hour
        )

    def encode(self, x: np.ndarray, rho: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compress signal using random Gaussian measurement matrix.

        y = Φ · x  where Φ ∈ R^{m×n}, m = ⌊ρ·n⌋

        Parameters
        ----------
        x : np.ndarray
            Original signal of shape (n,).
        rho : float
            Compression ratio (m/n).

        Returns
        -------
        y : np.ndarray
            Compressed measurements of shape (m,).
        Phi : np.ndarray
            Measurement matrix of shape (m, n).
        """
        m = max(1, int(rho * self.n))
        # Gaussian random measurement matrix (satisfies RIP with high probability)
        Phi = self.rng.standard_normal((m, self.n)) / np.sqrt(m)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            y = Phi @ x
        # Numerical safety: replace any NaN/Inf with zero
        y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        return y, Phi

    def decode_omp(self, y: np.ndarray, Phi: np.ndarray,
                   sparsity: int = None) -> np.ndarray:
        """
        Reconstruct signal using Orthogonal Matching Pursuit (OMP).

        Parameters
        ----------
        y : np.ndarray
            Compressed measurements of shape (m,).
        Phi : np.ndarray
            Measurement matrix of shape (m, n).
        sparsity : int, optional
            Assumed sparsity level. Default: self.s.

        Returns
        -------
        np.ndarray
            Reconstructed signal of shape (n,).
        """
        if sparsity is None:
            sparsity = self.s

        m, n = Phi.shape
        sparsity = min(sparsity, m)  # can't recover more than m components

        residual = y.copy()
        support = []
        x_hat = np.zeros(n)

        for _ in range(sparsity):
            # Find column most correlated with residual
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                correlations = np.abs(Phi.T @ residual)
            # Numerical safety
            correlations = np.nan_to_num(correlations, nan=0.0, posinf=0.0, neginf=0.0)
            # Exclude already selected
            for idx in support:
                correlations[idx] = -1
            best_idx = np.argmax(correlations)
            support.append(best_idx)

            # Solve least squares on selected support
            Phi_s = Phi[:, support]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(Phi_s, y, rcond=None)
            except np.linalg.LinAlgError:
                break

            # Update residual
            residual = y - Phi_s @ coeffs

            # Early stopping if residual is small
            if np.linalg.norm(residual) < 1e-10:
                break

        # Final reconstruction
        if support:
            Phi_s = Phi[:, support]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(Phi_s, y, rcond=None)
                x_hat[support] = coeffs
            except np.linalg.LinAlgError:
                pass

        return x_hat

    @staticmethod
    def nmse(x_original: np.ndarray, x_reconstructed: np.ndarray) -> float:
        """
        Normalized Mean Squared Error.

        NMSE = ||x - x̂||² / ||x||²

        Parameters
        ----------
        x_original : np.ndarray
            Original signal.
        x_reconstructed : np.ndarray
            Reconstructed signal.

        Returns
        -------
        float
            NMSE value (lower is better, 0 = perfect).
        """
        norm_orig = np.linalg.norm(x_original)
        if norm_orig < 1e-15:
            return 0.0
        return float(np.linalg.norm(x_original - x_reconstructed) ** 2
                      / norm_orig ** 2)

    def compressed_packet_bits(self, rho: float) -> int:
        """
        Number of bits in the compressed packet.

        Parameters
        ----------
        rho : float
            Compression ratio.

        Returns
        -------
        int
            Packet size after compression (bits).
            Assumes each measurement is 32-bit float.
        """
        m = max(1, int(rho * self.n))
        return m * 32  # 32 bits per float measurement
