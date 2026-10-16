"""Nitrox mixtures and the depth limits derived from Dalton's law.

For a mixture with O2 fraction ``f`` breathed at ambient pressure ``P``,
Dalton's law gives the partial pressures ``PO2 = f P`` and
``PN2 = (1 - f) P`` (argon lumped with nitrogen). Every quantity here
follows from these two lines plus the affine depth map of
:class:`~antasena.environment.Environment`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import FN2_AIR, FO2_AIR, P_H2O_ALV
from .environment import Environment

__all__ = ["Nitrox", "AIR", "OXYGEN", "po2", "mod", "best_mix", "ead",
           "ead_exact", "end", "ppo2_at", "hypoxic_floor"]


@dataclass(frozen=True)
class Nitrox:
    """An O2/N2 breathing gas specified by its O2 mole fraction."""

    fo2: float

    def __post_init__(self) -> None:
        if not (0.0 < self.fo2 <= 1.0) or not math.isfinite(self.fo2):
            raise ValueError("fo2 must lie in (0, 1]")

    @classmethod
    def ean(cls, percent: float) -> "Nitrox":
        """``Nitrox.ean(32)`` is EAN32."""
        return cls(percent / 100.0)

    @property
    def fn2(self) -> float:
        """Inert (N2 + Ar) fraction."""
        return 1.0 - self.fo2

    @property
    def name(self) -> str:
        if abs(self.fo2 - FO2_AIR) < 5e-4:
            return "Air"
        if self.fo2 >= 0.995:
            return "O2"
        return f"EAN{100 * self.fo2:.0f}" if abs(100 * self.fo2 - round(100 * self.fo2)) < 1e-6 \
            else f"EAN{100 * self.fo2:.1f}"

    def __str__(self) -> str:
        return self.name


AIR = Nitrox(FO2_AIR)
OXYGEN = Nitrox(1.0)

_DEFAULT_ENV = Environment()


def po2(gas: Nitrox, depth_m: float, env: Environment = _DEFAULT_ENV) -> float:
    """Inspired O2 partial pressure (bar), ``f P(d)``."""
    return gas.fo2 * env.pressure(depth_m)


ppo2_at = po2


def mod(gas: Nitrox, po2_max: float = 1.4, env: Environment = _DEFAULT_ENV) -> float:
    """Maximum operating depth (m): the depth at which ``PO2 = po2_max``.

    ``MOD = (po2_max / f - P_surf) / (rho g)``. Returns 0 if the limit is
    already exceeded at the surface.
    """
    if po2_max <= 0:
        raise ValueError("po2_max must be positive")
    return max(0.0, env.depth(po2_max / gas.fo2))


def best_mix(depth_m: float, po2_max: float = 1.4, env: Environment = _DEFAULT_ENV,
             step: float = 0.01) -> Nitrox:
    """Richest nitrox whose PO2 at ``depth_m`` does not exceed ``po2_max``.

    The continuous optimum ``f* = po2_max / P(d)`` maximizes the O2 fraction,
    hence minimizes the inert-gas load, subject to the oxygen limit. It is
    rounded *down* to ``step`` (1 % by default), never up, and capped at
    pure oxygen.
    """
    f = min(1.0, po2_max / env.pressure(depth_m))
    if step > 0:
        f = math.floor(f / step + 1e-9) * step
    if f <= 0:
        raise ValueError("no oxygen fraction satisfies the limit at this depth")
    return Nitrox(round(f, 10))


def ead(gas: Nitrox, depth_m: float, env: Environment = _DEFAULT_ENV) -> float:
    """Classical equivalent air depth (m).

    Equates inspired *ambient* N2 partial pressures:
    ``P_ead fN2_air = P(d) fN2``. This ignores alveolar water vapor.
    """
    return env.depth(env.pressure(depth_m) * gas.fn2 / FN2_AIR)


def ead_exact(gas: Nitrox, depth_m: float, env: Environment = _DEFAULT_ENV,
              p_h2o: float = P_H2O_ALV) -> float:
    """Equivalent air depth that is exact for Buhlmann-type tissue models.

    Tissue inert-gas loading is driven by the *alveolar* pressure
    ``(P - p_H2O) fN2``. Equating that, not the ambient value, gives

        P_ead = (P(d) - p_H2O) fN2 / fN2_air + p_H2O.

    Because the map P -> P_ead is affine, an entire nitrox profile is
    equivalent (tissue by tissue, at every instant) to the air profile whose
    pressures are mapped this way. The classical EAD differs by
    ``p_H2O (1 - fN2 / fN2_air)`` bar, which is always on the shallow,
    non-conservative side for nitrox.
    """
    p = (env.pressure(depth_m) - p_h2o) * gas.fn2 / FN2_AIR + p_h2o
    return env.depth(p)


def end(gas: Nitrox, depth_m: float, env: Environment = _DEFAULT_ENV,
        o2_narcotic: bool = True) -> float:
    """Equivalent narcotic depth (m).

    If O2 is treated as narcotic (the common conservative convention), every
    O2/N2 mix is as narcotic as air at the same depth and END equals the
    depth. Otherwise END reduces to the classical EAD.
    """
    return depth_m if o2_narcotic else ead(gas, depth_m, env)


def hypoxic_floor(gas: Nitrox, po2_min: float = 0.16, env: Environment = _DEFAULT_ENV) -> float:
    """Shallowest depth (m) at which the gas supplies at least ``po2_min``.

    Zero for every nitrox at sea level; relevant only at altitude.
    """
    return max(0.0, env.depth(po2_min / gas.fo2))
