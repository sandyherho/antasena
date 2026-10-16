"""Oxygen toxicity bookkeeping with exact integrals over linear segments.

Both indices are integrals of a rate over the PO2 history. On a dive plan
PO2 is piecewise linear in time (constant gas, linear depth change), so the
integrals are evaluated in closed form rather than by quadrature.

CNS clock
---------
``CNS = integral dt / T_lim(PO2(t))`` with ``T_lim`` the NOAA single-exposure
limits, linearly interpolated in PO2 between table nodes. On a node interval
``T_lim(p) = T_i + s (p - p_i)`` and ``p(t) = p_a + k t``, so

    integral dt / T_lim = ln(T_lim(p_b) / T_lim(p_a)) / (k s)      (k s != 0)
                        = dt / T_lim                               (k s == 0).

Conventions below 0.6 bar follow Baker's "Oxygen toxicity calculations": no
accrual for PO2 <= 0.5 bar, and on 0.5 < PO2 <= 0.6 the limit continues
linearly to 900 min at 0.5 bar (T = 1800 - 1800 PO2), so the clock starts at
1/900 per minute just above 0.5 bar. Above 1.6 bar the NOAA table gives no
limit and :class:`OxygenLimitError` is raised. Surface elimination uses a
90-minute half-time.

Pulmonary (OTU / UPTD)
----------------------
``OTU = integral ((PO2 - 0.5) / 0.5)^(5/6) dt`` for PO2 > 0.5 bar
(Lambertsen dose-response as linearized by Hamilton). With ``u = (p - 0.5)/0.5``
and ``dp = k dt``,

    OTU = (3 / 11) dt / (p_b - p_a) [u_b^(11/6) - u_a^(11/6)]     (p_b != p_a).
"""
from __future__ import annotations

import math

__all__ = ["NOAA_SINGLE", "NOAA_DAILY", "cns_limit", "cns_rate", "cns_segment",
           "otu_segment", "cns_after_surface_interval", "OxygenLimitError"]

#: NOAA single-exposure oxygen limits, (PO2 [bar], minutes).
NOAA_SINGLE = ((0.6, 720.0), (0.7, 570.0), (0.8, 450.0), (0.9, 360.0), (1.0, 300.0),
               (1.1, 240.0), (1.2, 210.0), (1.3, 180.0), (1.4, 150.0), (1.5, 120.0),
               (1.6, 45.0))

#: NOAA 24-hour oxygen limits, (PO2 [bar], minutes).
NOAA_DAILY = ((0.6, 720.0), (0.7, 570.0), (0.8, 450.0), (0.9, 360.0), (1.0, 300.0),
              (1.1, 270.0), (1.2, 240.0), (1.3, 210.0), (1.4, 180.0), (1.5, 180.0),
              (1.6, 150.0))

CNS_HALF_TIME = 90.0
_TOL = 1e-9


class OxygenLimitError(ValueError):
    """PO2 above the range covered by the NOAA limits."""


#: Limit nodes used for interpolation: Baker's (0.5, 900) extension plus NOAA.
_NODES = ((0.5, 900.0),) + NOAA_SINGLE


def cns_limit(p: float) -> float:
    """Single-exposure limit (min) at PO2 ``p`` in [0.5, 1.6], linear between nodes."""
    if p < 0.5 - _TOL or p > 1.6 + _TOL:
        raise ValueError("CNS limits are defined for 0.5 <= PO2 <= 1.6 bar")
    p = min(max(p, 0.5), 1.6)
    for (p0, t0), (p1, t1) in zip(_NODES, _NODES[1:]):
        if p <= p1 + 1e-12:
            return t0 + (t1 - t0) * (p - p0) / (p1 - p0)
    return NOAA_SINGLE[-1][1]


def cns_rate(p: float) -> float:
    """CNS accrual rate (fraction per minute) at PO2 ``p``."""
    if p > 1.6 + _TOL:
        raise OxygenLimitError(f"PO2 {p:.3f} bar exceeds 1.6 bar")
    if p <= 0.5:
        return 0.0
    return 1.0 / cns_limit(p)


# Breakpoints at which the integrand changes formula.
_BREAKS = (0.5, 0.6) + tuple(p for p, _ in NOAA_SINGLE[1:])


def cns_segment(p_start: float, p_end: float, minutes: float) -> float:
    """CNS fraction (1.0 = 100 %) accrued while PO2 moves linearly over ``minutes``."""
    if minutes < 0:
        raise ValueError("duration must be non-negative")
    if minutes == 0:
        return 0.0
    if max(p_start, p_end) > 1.6 + _TOL:
        raise OxygenLimitError(f"PO2 {max(p_start, p_end):.3f} bar exceeds 1.6 bar")
    if abs(p_end - p_start) < 1e-12:
        return minutes * cns_rate(p_start)
    k = (p_end - p_start) / minutes            # bar per minute
    lo, hi = sorted((p_start, p_end))
    pts = [lo] + [b for b in _BREAKS if lo < b < hi] + [hi]
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        dt = (b - a) / abs(k)
        mid = 0.5 * (a + b)
        if mid <= 0.5:
            continue
        ta, tb = cns_limit(a), cns_limit(b)
        if abs(tb - ta) < 1e-12:
            total += dt / ta
        else:
            # integral over p of dp / T(p), divided by |k|; T linear in p
            s = (tb - ta) / (b - a)
            total += math.log(tb / ta) / (s * abs(k))
    return total


def otu_segment(p_start: float, p_end: float, minutes: float) -> float:
    """Oxygen tolerance units accrued while PO2 moves linearly over ``minutes``."""
    if minutes < 0:
        raise ValueError("duration must be non-negative")
    if minutes == 0:
        return 0.0

    def u(p: float) -> float:
        return max(0.0, (p - 0.5) / 0.5)

    if abs(p_end - p_start) < 1e-12:
        return minutes * u(p_start) ** (5.0 / 6.0)
    return (3.0 / 11.0) * minutes / (p_end - p_start) * (
        u(p_end) ** (11.0 / 6.0) - u(p_start) ** (11.0 / 6.0))


def cns_after_surface_interval(cns: float, minutes: float,
                               half_time: float = CNS_HALF_TIME) -> float:
    """Exponential surface elimination of the CNS clock."""
    if minutes < 0:
        raise ValueError("duration must be non-negative")
    return cns * 0.5 ** (minutes / half_time)
