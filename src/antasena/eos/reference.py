"""Reference-quality Z(T, P, x_O2) by tensor-product cubic interpolation.

The table in :mod:`._zdata` holds Z on a uniform grid

    T   = 253.15 ... 353.15 K   (step 5 K)
    P   = 0 ... 400 bar         (step 10 bar)
    x   = 0 ... 1               (step 0.05)

generated from the multiparameter Helmholtz mixture model (see
``tools/generate_z_table.py``). Along each axis Z is interpolated with the
four-point Lagrange polynomial through the nearest nodes (shifted inward at
the grid edges). Z is analytic in all three variables in the supercritical
gas region, so the interpolation error scales as h^4 times the fourth
derivative; the test suite measures it against off-grid reference points.
"""
from __future__ import annotations

from . import _zdata as D

__all__ = ["z_reference", "T_RANGE", "P_MAX"]

T_RANGE = (D.T_MIN, D.T_MIN + D.T_STEP * (D.NT - 1))
P_MAX = D.P_MIN + D.P_STEP * (D.NP - 1)
_Z = D.Z
_NT, _NP = D.NT, D.NP


def _stencil(u: float, n: int) -> tuple[int, tuple[float, float, float, float]]:
    """First node index and Lagrange weights for fractional grid position u."""
    i0 = int(u) - 1
    i0 = max(0, min(n - 4, i0))
    t = u - i0  # position relative to node i0, nominally in [1, 2]
    w0 = -(t - 1.0) * (t - 2.0) * (t - 3.0) / 6.0
    w1 = t * (t - 2.0) * (t - 3.0) / 2.0
    w2 = -t * (t - 1.0) * (t - 3.0) / 2.0
    w3 = t * (t - 1.0) * (t - 2.0) / 6.0
    return i0, (w0, w1, w2, w3)


def z_reference(T: float, p_bar: float, x_o2: float) -> float:
    if not (T_RANGE[0] - 1e-9 <= T <= T_RANGE[1] + 1e-9):
        raise ValueError(f"temperature {T:.2f} K outside reference table "
                         f"[{T_RANGE[0]}, {T_RANGE[1]}] K")
    if not (0.0 <= p_bar <= P_MAX + 1e-9):
        raise ValueError(f"pressure {p_bar:.1f} bar outside reference table [0, {P_MAX}] bar")
    if p_bar == 0.0:
        return 1.0
    it, wt = _stencil((T - D.T_MIN) / D.T_STEP, _NT)
    ip, wp = _stencil((p_bar - D.P_MIN) / D.P_STEP, _NP)
    ix, wx = _stencil((x_o2 - D.X_MIN) / D.X_STEP, D.NX)
    total = 0.0
    for a in range(4):
        sx = 0.0
        for b in range(4):
            base = ((ix + a) * _NT + it + b) * _NP + ip
            sx += wt[b] * (wp[0] * _Z[base] + wp[1] * _Z[base + 1]
                           + wp[2] * _Z[base + 2] + wp[3] * _Z[base + 3])
        total += wx[a] * sx
    return total
