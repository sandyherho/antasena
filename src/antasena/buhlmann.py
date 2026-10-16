"""Buhlmann ZH-L16C nitrogen model with gradient factors, solved exactly.

Tissue kinetics
---------------
Each compartment ``i`` is a perfusion-limited, well-stirred tank:

    dP_i/dt = k_i (P_alv(t) - P_i),     k_i = ln 2 / tau_i,

driven by the alveolar inert pressure ``P_alv = (P_amb - p_H2O) fN2``. For a
segment of constant gas and linearly varying depth, ``P_alv(t) = P_alv0 + R t``
and the linear ODE has the closed-form (Schreiner) solution

    P_i(t) = P_alv0 + R (t - 1/k_i) - (P_alv0 - P_i0 - R/k_i) exp(-k_i t).

``R = 0`` reduces it to the Haldane equation. No time stepping is used.

Tolerance
---------
Buhlmann's tolerated ambient pressure for tension ``P`` is
``P_tol = (P - a) b``, i.e. the M-value line ``M(P_amb) = a + P_amb / b``.
A gradient factor ``g`` scales the allowed supersaturation,
``P <= P_amb + g (M(P_amb) - P_amb)``, giving the ceiling

    P_ceil = (P - a g) / (g / b + 1 - g).

No-decompression limit
----------------------
At constant depth the tension relaxes monotonically to ``P_alv``. The surface
condition ``P_i <= M_g(P_surf)`` is first violated at

    t_i = -ln[(P_alv - M_g) / (P_alv - P_i0)] / k_i     (P_alv > M_g > P_i0),

and the NDL is ``min_i t_i``. This is exact, not a search.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .constants import FN2_AIR, P_H2O_ALV

__all__ = ["ZHL16C_N2", "Compartment", "TissueState", "schreiner", "haldane",
           "ceiling_pressure", "ndl_constant_depth", "LN2"]

LN2 = math.log(2.0)


@dataclass(frozen=True)
class Compartment:
    half_time: float   # minutes
    a: float           # bar
    b: float           # dimensionless

    @property
    def k(self) -> float:
        return LN2 / self.half_time

    def m_value(self, p_amb: float) -> float:
        return self.a + p_amb / self.b

    def tolerated(self, tension: float, gf: float = 1.0) -> float:
        """Lowest ambient pressure at which ``tension`` is allowed under ``gf``."""
        return (tension - self.a * gf) / (gf / self.b + 1.0 - gf)

    def max_tension(self, p_amb: float, gf: float = 1.0) -> float:
        """Largest tension allowed at ambient ``p_amb`` under ``gf`` (inverse of tolerated)."""
        return p_amb + gf * (self.m_value(p_amb) - p_amb)


#: ZH-L16C nitrogen coefficients (compartment 1b), Buhlmann 1995/2002.
ZHL16C_N2 = tuple(Compartment(t, a, b) for t, a, b in (
    (5.0, 1.1696, 0.5578), (8.0, 1.0000, 0.6514), (12.5, 0.8618, 0.7222),
    (18.5, 0.7562, 0.7825), (27.0, 0.6200, 0.8126), (38.3, 0.5043, 0.8434),
    (54.3, 0.4410, 0.8693), (77.0, 0.4000, 0.8910), (109.0, 0.3750, 0.9092),
    (146.0, 0.3500, 0.9222), (187.0, 0.3295, 0.9319), (239.0, 0.3065, 0.9403),
    (305.0, 0.2835, 0.9477), (390.0, 0.2610, 0.9544), (498.0, 0.2480, 0.9602),
    (635.0, 0.2327, 0.9653),
))


def _g(x: float) -> float:
    """g(x) = 1 - (1 - e^-x) / x, evaluated without cancellation."""
    if x < 0.05:
        # alternating series sum_{n>=1} (-1)^(n+1) x^n / (n+1)!, truncated at n = 10
        term, total, n = 1.0, 0.0, 1
        while n <= 10:
            term *= x / (n + 1) if n > 1 else x / 2.0
            total += term if n % 2 else -term
            n += 1
        return total
    return 1.0 + math.expm1(-x) / x


def schreiner(p0: float, p_alv0: float, rate: float, k: float, t: float) -> float:
    """Exact tension after ``t`` min with alveolar pressure ``p_alv0 + rate t``.

    Algebraically identical to the textbook form
    ``P_alv0 + R (t - 1/k) - (P_alv0 - P_0 - R/k) e^(-k t)`` but written as

        P(t) = P_0 + (P_alv0 - P_0)(1 - e^(-kt)) + R t g(kt),
        g(x) = 1 - (1 - e^(-x)) / x,

    which avoids the cancellation between ``R t`` and ``R/k`` terms that costs
    the textbook form several digits for fast tissues on short, steep ramps.
    """
    x = k * t
    return p0 + (p_alv0 - p0) * -math.expm1(-x) + rate * t * _g(x)


def haldane(p0: float, p_alv: float, k: float, t: float) -> float:
    return p_alv + (p0 - p_alv) * math.exp(-k * t)


def alveolar(p_amb: float, fn2: float, p_h2o: float = P_H2O_ALV) -> float:
    return max(0.0, p_amb - p_h2o) * fn2


@dataclass
class TissueState:
    """Inert-gas tensions (bar) of all compartments."""

    tensions: list[float]
    compartments: tuple[Compartment, ...] = field(default=ZHL16C_N2, repr=False)
    p_h2o: float = P_H2O_ALV

    @classmethod
    def surface_equilibrium(cls, p_surface: float, compartments=ZHL16C_N2,
                            p_h2o: float = P_H2O_ALV) -> "TissueState":
        p = alveolar(p_surface, FN2_AIR, p_h2o)
        return cls([p] * len(compartments), compartments, p_h2o)

    def copy(self) -> "TissueState":
        return TissueState(list(self.tensions), self.compartments, self.p_h2o)

    def expose(self, p_start: float, p_end: float, minutes: float, fn2: float) -> None:
        """Advance in place through a linear ambient-pressure ramp on one gas."""
        if minutes < 0:
            raise ValueError("duration must be non-negative")
        if minutes == 0:
            return
        pa0 = alveolar(p_start, fn2, self.p_h2o)
        pa1 = alveolar(p_end, fn2, self.p_h2o)
        rate = (pa1 - pa0) / minutes
        self.tensions = [schreiner(p, pa0, rate, c.k, minutes)
                         for p, c in zip(self.tensions, self.compartments)]

    def ceiling(self, gf: float = 1.0) -> float:
        """Tolerated ambient pressure (bar): the maximum over compartments."""
        return max(c.tolerated(p, gf) for p, c in zip(self.tensions, self.compartments))

    def leading(self, gf: float = 1.0) -> int:
        vals = [c.tolerated(p, gf) for p, c in zip(self.tensions, self.compartments)]
        return max(range(len(vals)), key=vals.__getitem__)

    def gf_now(self, p_amb: float) -> float:
        """Current supersaturation as a fraction of the M-value gradient (max over tissues).

        ``(P_i - P_amb) / (M_i(P_amb) - P_amb)``; values above 1 exceed the
        unmodified Buhlmann limit.
        """
        return max((p - p_amb) / (c.m_value(p_amb) - p_amb)
                   for p, c in zip(self.tensions, self.compartments))

    def saturation(self, p_amb: float) -> list[float]:
        """Per-compartment tension as a fraction of its M-value at ``p_amb``."""
        return [p / c.m_value(p_amb) for p, c in zip(self.tensions, self.compartments)]


def ndl_constant_depth(state: TissueState, p_amb: float, fn2: float,
                       p_surface: float, gf_high: float = 1.0) -> float:
    """Exact no-decompression time (min) at constant ``p_amb`` from ``state``.

    Returns ``math.inf`` if no compartment can ever reach its surfacing
    limit, and ``0.0`` if a direct ascent is already disallowed.
    """
    p_alv = alveolar(p_amb, fn2, state.p_h2o)
    best = math.inf
    for p0, c in zip(state.tensions, state.compartments):
        m = c.max_tension(p_surface, gf_high)
        if p0 >= m:
            return 0.0
        if p_alv <= m:
            continue
        best = min(best, -math.log((p_alv - m) / (p_alv - p0)) / c.k)
    return best
