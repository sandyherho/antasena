"""Guaranteed bounds under measurement uncertainty.

An O2 analyzer reading ``f`` with accuracy ``+/- df`` means the true fraction
lies in ``[f - df, f + df]``. Many diving quantities are monotone in their
inputs, so their exact range over the input box is attained at the box
corners: for a function increasing in ``x`` and decreasing in ``y`` the range
is ``[g(x_lo, y_hi), g(x_hi, y_lo)]``. This module uses that fact, with the
monotonicity of each function proved in its docstring and checked by
property-based tests, to report *guaranteed* rather than nominal limits.

``Interval`` implements outward-free (exact real) interval arithmetic for
the four basic operations, which suffices for the closed-form expressions in
:mod:`antasena.gas`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .buhlmann import TissueState, ndl_constant_depth
from .environment import Environment
from .gas import Nitrox, mod

__all__ = ["Interval", "mod_bounds", "ndl_bounds", "po2_bounds"]


@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            raise ValueError("interval lower bound exceeds upper bound")

    @classmethod
    def around(cls, x: float, dx: float) -> "Interval":
        return cls(x - abs(dx), x + abs(dx))

    @property
    def mid(self) -> float:
        return 0.5 * (self.lo + self.hi)

    @property
    def width(self) -> float:
        return self.hi - self.lo

    def __contains__(self, x: float) -> bool:
        return self.lo <= x <= self.hi

    def _o(self, o):
        return o if isinstance(o, Interval) else Interval(o, o)

    def __add__(self, o):
        o = self._o(o)
        return Interval(self.lo + o.lo, self.hi + o.hi)

    __radd__ = __add__

    def __sub__(self, o):
        o = self._o(o)
        return Interval(self.lo - o.hi, self.hi - o.lo)

    def __rsub__(self, o):
        return self._o(o) - self

    def __mul__(self, o):
        o = self._o(o)
        p = (self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi)
        return Interval(min(p), max(p))

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = self._o(o)
        if o.lo <= 0 <= o.hi:
            raise ZeroDivisionError("interval divisor contains zero")
        return self * Interval(1.0 / o.hi, 1.0 / o.lo)

    def __rtruediv__(self, o):
        return self._o(o) / self

    def __repr__(self) -> str:
        return f"[{self.lo:.6g}, {self.hi:.6g}]"


def po2_bounds(fo2: Interval, depth: Interval, env: Environment = Environment()) -> Interval:
    """Exact PO2 range: increasing in both fraction and depth."""
    return Interval(fo2.lo * env.pressure(max(0.0, depth.lo)),
                    fo2.hi * env.pressure(depth.hi))


def mod_bounds(fo2: float, dfo2: float, po2_max: float = 1.4,
               env: Environment = Environment(), depth_error: float = 0.0) -> Interval:
    """Range of the MOD given analyzer error ``dfo2`` and gauge error ``depth_error``.

    MOD is strictly decreasing in ``fo2`` (``d MOD / d f = -po2_max / (f^2 rho g) < 0``),
    so ``MOD_lo = MOD(f + df)``. A depth gauge that may read ``depth_error``
    shallow reduces the depth a diver can safely *read* by the same amount.
    The lower end is the guaranteed MOD.
    """
    hi_f = min(1.0, fo2 + abs(dfo2))
    lo_f = max(1e-6, fo2 - abs(dfo2))
    return Interval(max(0.0, mod(Nitrox(hi_f), po2_max, env) - abs(depth_error)),
                    mod(Nitrox(lo_f), po2_max, env))


def ndl_bounds(fo2: float, dfo2: float, depth: float, gf_high: float = 1.0,
               env: Environment = Environment(), depth_error: float = 0.0,
               state: TissueState | None = None) -> Interval:
    """Range of the (instantaneous-descent) NDL.

    For every compartment ``t_i = ln[(P_alv - P_0)/(P_alv - M)]/k`` is strictly
    decreasing in ``P_alv = (P - p_H2O) fN2`` when ``P_alv > M > P_0``, and
    ``P_alv`` increases with depth and with ``fN2 = 1 - fO2``. The minimum over
    compartments preserves monotonicity, so the guaranteed (shortest) NDL is
    obtained at the deepest depth and leanest mix.
    """
    st = state or TissueState.surface_equilibrium(env.surface_pressure)
    lean = Nitrox(max(1e-6, fo2 - abs(dfo2)))
    rich = Nitrox(min(1.0, fo2 + abs(dfo2)))
    d_hi = depth + abs(depth_error)
    d_lo = max(0.0, depth - abs(depth_error))
    lo = ndl_constant_depth(st, env.pressure(d_hi), lean.fn2, env.surface_pressure, gf_high)
    hi = ndl_constant_depth(st, env.pressure(d_lo), rich.fn2, env.surface_pressure, gf_high)
    return Interval(lo, hi if hi >= lo else lo) if math.isfinite(lo) else Interval(lo, math.inf)
