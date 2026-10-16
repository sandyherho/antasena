"""Hydrostatics: the map between depth and absolute ambient pressure.

The ambient pressure at depth ``d`` is

    P(d) = P_surf + rho g d / 1e5        [bar]

with ``P_surf`` the surface pressure (altitude dependent) and ``rho`` the
water density. Because the map is affine, every depth limit in diving is the
pre-image of a pressure limit, which is how MOD, EAD and END are computed.

Two conventions are offered:

* ``Environment()`` (physical): rho from :data:`WATER_DENSITY`, ``g = g0``,
  ``P_surf`` from the International Standard Atmosphere.
* ``Environment.training_tables()``: 1 bar at the surface and exactly
  10 m per bar, the rounded convention behind most agency nitrox tables.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import G0, P_ATM, PA_PER_BAR, WATER_DENSITY

__all__ = ["Environment", "surface_pressure_isa"]


def surface_pressure_isa(altitude_m: float) -> float:
    """Surface pressure (bar) at ``altitude_m`` in the ISA troposphere.

    ``P = P0 (1 - L h / T0)^(g M / (R L))`` with ``L = 0.0065 K/m``,
    ``T0 = 288.15 K``; valid below 11 km.
    """
    if not -500.0 <= altitude_m <= 11000.0:
        raise ValueError("altitude must lie in [-500, 11000] m")
    L, T0, M, R = 0.0065, 288.15, 0.0289644, 8.3144598
    return P_ATM * (1.0 - L * altitude_m / T0) ** (G0 * M / (R * L))


@dataclass(frozen=True)
class Environment:
    """Water and atmosphere conditions of a dive site."""

    water: str = "salt"
    altitude_m: float = 0.0
    density: float | None = None
    surface_pressure: float | None = None
    gravity: float = G0

    def __post_init__(self) -> None:
        if self.density is None:
            if self.water not in WATER_DENSITY:
                raise ValueError(f"unknown water type {self.water!r}; "
                                 f"choose from {sorted(WATER_DENSITY)}")
            object.__setattr__(self, "density", WATER_DENSITY[self.water])
        if self.surface_pressure is None:
            object.__setattr__(self, "surface_pressure",
                               surface_pressure_isa(self.altitude_m))
        if not (self.density > 0 and self.surface_pressure > 0 and self.gravity > 0):
            raise ValueError("density, surface pressure and gravity must be positive")

    @classmethod
    def training_tables(cls) -> "Environment":
        """1 bar surface, 10 m/bar: reproduces rounded agency tables."""
        return cls(water="salt", density=1.0e4 / G0, surface_pressure=1.0)

    @property
    def bar_per_meter(self) -> float:
        """Hydrostatic gradient rho g / 1e5, bar per meter."""
        return self.density * self.gravity / PA_PER_BAR

    def pressure(self, depth_m: float) -> float:
        """Absolute ambient pressure (bar) at ``depth_m``."""
        if depth_m < 0 or not math.isfinite(depth_m):
            raise ValueError("depth must be finite and non-negative")
        return self.surface_pressure + self.bar_per_meter * depth_m

    def depth(self, pressure_bar: float) -> float:
        """Depth (m) at which the ambient pressure equals ``pressure_bar``.

        Negative results (pressure below surface pressure) are returned as is;
        callers interpret them as "not reachable underwater".
        """
        return (pressure_bar - self.surface_pressure) / self.bar_per_meter
