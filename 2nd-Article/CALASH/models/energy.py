"""
First-Order Radio Energy Dissipation Model
==========================================
The standard radio model for WSN energy analysis, universally adopted
in clustering protocol research since its introduction in 2000.

All energy values returned in Joules.

Transmission energy (Eqs. 1-2 of [1]):
    E_Tx(l, d) = l * E_elec + l * eps_fs * d^2       if d < d0
               = l * E_elec + l * eps_mp * d^4       if d >= d0

Reception energy (Eq. 3 of [1]):
    E_Rx(l)    = l * E_elec

where:
    E_elec  = 50 nJ/bit      (transmitter/receiver electronics)
    eps_fs  = 10 pJ/bit/m^2  (free-space Friis model, d^2 path loss)
    eps_mp  = 0.0013 pJ/bit/m^4  (two-ray ground-reflection, d^4 path loss)
    d0      = sqrt(eps_fs / eps_mp) ≈ 87.7 m  (crossover distance)

This model is used by ALL protocols in the framework to ensure fair
comparison — only the routing/clustering logic differs across protocols.

References
----------
[1] Heinzelman, W.R., Chandrakasan, A.P. & Balakrishnan, H.
    "Energy-Efficient Communication Protocol for Wireless Microsensor
    Networks." Proc. 33rd Annual Hawaii Int. Conf. on System Sciences
    (HICSS), 2000, pp. 3005-3014. DOI: 10.1109/HICSS.2000.926982

[2] Heinzelman, W.B., Chandrakasan, A.P. & Balakrishnan, H.
    "An Application-Specific Protocol Architecture for Wireless
    Microsensor Networks." IEEE Trans. Wireless Communications,
    vol. 1, no. 4, pp. 660-670, Oct. 2002. DOI: 10.1109/TWC.2002.804190

[3] Rappaport, T.S. "Wireless Communications: Principles and Practice."
    2nd ed., Prentice Hall, 2002. (free-space / two-ray propagation)
"""

import numpy as np


class EnergyModel:
    """Static energy calculation methods for WSN radio model."""

    def __init__(self, config):
        self.E_elec = config.E_elec
        self.eps_fs = config.eps_fs
        self.eps_mp = config.eps_mp
        self.E_DA = config.E_DA
        self.E_sense = config.E_sense
        self.d0 = config.d0

    def tx_energy(self, num_bits: int, distance: float) -> float:
        """
        Compute transmission energy in Joules.

        Parameters
        ----------
        num_bits : int
            Number of bits to transmit.
        distance : float
            Distance to receiver in meters.

        Returns
        -------
        float
            Energy consumed in Joules.
        """
        electronics = num_bits * self.E_elec
        if distance < self.d0:
            amplifier = num_bits * self.eps_fs * distance ** 2
        else:
            amplifier = num_bits * self.eps_mp * distance ** 4
        return electronics + amplifier

    def rx_energy(self, num_bits: int) -> float:
        """
        Compute reception energy in Joules.

        Parameters
        ----------
        num_bits : int
            Number of bits received.

        Returns
        -------
        float
            Energy consumed in Joules.
        """
        return num_bits * self.E_elec

    def da_energy(self, num_bits: int, num_signals: int) -> float:
        """
        Compute data aggregation energy at cluster head.

        Parameters
        ----------
        num_bits : int
            Bits per signal.
        num_signals : int
            Number of signals aggregated.

        Returns
        -------
        float
            Energy consumed in Joules.
        """
        return num_bits * num_signals * self.E_DA

    def sense_energy(self, num_bits: int) -> float:
        """
        Compute sensing energy.

        Parameters
        ----------
        num_bits : int
            Number of bits sensed.

        Returns
        -------
        float
            Energy consumed in Joules.
        """
        return num_bits * self.E_sense

    def total_member_cost(self, num_bits: int, dist_to_ch: float) -> float:
        """
        Total energy cost for a cluster member in one round:
        sense + transmit to CH.

        Parameters
        ----------
        num_bits : int
            Packet size in bits.
        dist_to_ch : float
            Distance to cluster head in meters.

        Returns
        -------
        float
            Total energy in Joules.
        """
        return self.sense_energy(num_bits) + self.tx_energy(num_bits, dist_to_ch)

    def total_ch_cost(self, num_bits: int, num_members: int,
                      dist_to_next: float) -> float:
        """
        Total energy cost for a cluster head in one round:
        receive from all members + aggregate + transmit to next hop.

        Parameters
        ----------
        num_bits : int
            Packet size in bits.
        num_members : int
            Number of cluster members.
        dist_to_next : float
            Distance to next hop (another CH or BS) in meters.

        Returns
        -------
        float
            Total energy in Joules.
        """
        rx_cost = num_members * self.rx_energy(num_bits)
        agg_cost = self.da_energy(num_bits, num_members)
        tx_cost = self.tx_energy(num_bits, dist_to_next)
        return rx_cost + agg_cost + tx_cost
