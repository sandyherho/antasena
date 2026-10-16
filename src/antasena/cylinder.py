"""Cylinder contents: how much gas a pressure reading really represents.

A cylinder of water volume ``V`` at absolute pressure ``P`` and temperature
``T`` holds ``n = P V / (Z R T)`` mol. Divers plan with "free liters"
``P V`` (ideal gas), which overstates the contents whenever ``Z > 1``: for
air at 300 bar and 20 degC, Z is about 1.10, so roughly one liter in eleven
of the ideal estimate does not exist.

Two common questions follow directly from conserving ``n``:

* Cooling after a hot fill (isochoric): ``P2 = n R T2 Z(T2, P2) / V``.
* Pressure remaining after breathing ``G`` free liters: ``n2 = n - G p_atm / (R T)``.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import eos
from .constants import P_ATM, PA_PER_BAR, R_GAS, T0_C

__all__ = ["Cylinder", "settled_pressure", "free_gas", "pressure_after_use"]


@dataclass(frozen=True)
class Cylinder:
    """A cylinder by water volume (liters) and rated working pressure (bar gauge)."""

    volume_l: float = 12.0
    working_pressure: float = 232.0
    name: str = ""

    def __post_init__(self) -> None:
        if self.volume_l <= 0 or self.working_pressure <= 0:
            raise ValueError("volume and working pressure must be positive")


def settled_pressure(p_hot: float, t_hot_c: float, t_cold_c: float, fo2: float, *,
                     volume_l: float = 12.0, model: str = "reference",
                     gauge: bool = True, p_atm: float = P_ATM) -> float:
    """Pressure after the cylinder cools (or warms) from ``t_hot_c`` to ``t_cold_c``."""
    off = p_atm if gauge else 0.0
    n = eos.moles(p_hot + off, volume_l, t_hot_c + T0_C, fo2, model)
    return eos.pressure_from_moles(n, volume_l, t_cold_c + T0_C, fo2, model) - off


def free_gas(pressure: float, fo2: float, *, volume_l: float = 12.0,
             temperature_c: float = 20.0, model: str = "reference",
             gauge: bool = True, p_atm: float = P_ATM) -> float:
    """Usable free gas (surface liters at ``p_atm`` and the same temperature).

    With ``gauge=True`` the gas that remains in the cylinder at 0 bar gauge
    is excluded, because it cannot be breathed.
    """
    T = temperature_c + T0_C
    off = p_atm if gauge else 0.0
    n = eos.moles(pressure + off, volume_l, T, fo2, model)
    n_left = eos.moles(off, volume_l, T, fo2, model) if gauge else 0.0
    return (n - n_left) * R_GAS * T / (p_atm * PA_PER_BAR) * 1e3


def pressure_after_use(pressure: float, used_liters: float, fo2: float, *,
                       volume_l: float = 12.0, temperature_c: float = 20.0,
                       model: str = "reference", gauge: bool = True,
                       p_atm: float = P_ATM) -> float:
    """Gauge (or absolute) pressure after ``used_liters`` of free gas are breathed."""
    T = temperature_c + T0_C
    off = p_atm if gauge else 0.0
    n = eos.moles(pressure + off, volume_l, T, fo2, model)
    n2 = n - used_liters * 1e-3 * p_atm * PA_PER_BAR / (R_GAS * T)
    if n2 <= 0:
        return -off
    return eos.pressure_from_moles(n2, volume_l, T, fo2, model) - off
