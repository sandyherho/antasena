"""Peng-Robinson (1976) cubic equation of state for O2/N2 mixtures.

    P = R T / (v - b) - a(T) / (v^2 + 2 b v - b^2)

Pure-component parameters

    a_i = 0.45724 R^2 Tc_i^2 / Pc_i * [1 + k_i (1 - sqrt(T / Tc_i))]^2
    b_i = 0.07780 R Tc_i / Pc_i
    k_i = 0.37464 + 1.54226 w_i - 0.26992 w_i^2

van der Waals one-fluid mixing: ``a = sum_ij x_i x_j sqrt(a_i a_j)(1 - k_ij)``,
``b = sum_i x_i b_i``. In terms of ``A = a P / (R T)^2`` and ``B = b P / (R T)``
the compressibility factor is the largest real root of

    Z^3 - (1 - B) Z^2 + (A - 3 B^2 - 2 B) Z - (A B - B^2 - B^3) = 0.

Above the critical temperatures of both components (the case for all diving
conditions) the cubic has a single real root, found here by Newton's method
started from the ideal-gas value with a bracketing fallback.
"""
from __future__ import annotations

import math

from ..constants import PA_PER_BAR, R_GAS
from ..roots import brentq

__all__ = ["CRITICAL", "z_pr", "pr_parameters"]

#: (Tc [K], Pc [Pa], acentric factor) from the reference equations of state.
CRITICAL = {
    "O2": (154.581, 5.0430e6, 0.0222),
    "N2": (126.192, 3.3958e6, 0.0372),
}

K_IJ = 0.0


def _pure(T: float, comp: str) -> tuple[float, float]:
    Tc, Pc, w = CRITICAL[comp]
    k = 0.37464 + 1.54226 * w - 0.26992 * w * w
    alpha = (1.0 + k * (1.0 - math.sqrt(T / Tc))) ** 2
    a = 0.45724 * R_GAS ** 2 * Tc ** 2 / Pc * alpha
    b = 0.07780 * R_GAS * Tc / Pc
    return a, b


def pr_parameters(T: float, x_o2: float) -> tuple[float, float]:
    """Mixture ``a`` (Pa m^6 mol^-2) and ``b`` (m^3 mol^-1)."""
    a1, b1 = _pure(T, "O2")
    a2, b2 = _pure(T, "N2")
    x1, x2 = x_o2, 1.0 - x_o2
    a12 = math.sqrt(a1 * a2) * (1.0 - K_IJ)
    a = x1 * x1 * a1 + 2.0 * x1 * x2 * a12 + x2 * x2 * a2
    b = x1 * b1 + x2 * b2
    return a, b


def z_pr(T: float, p_bar: float, x_o2: float) -> float:
    if p_bar == 0.0:
        return 1.0
    a, b = pr_parameters(T, x_o2)
    P = p_bar * PA_PER_BAR
    A = a * P / (R_GAS * T) ** 2
    B = b * P / (R_GAS * T)
    c2, c1, c0 = -(1.0 - B), A - 3.0 * B * B - 2.0 * B, -(A * B - B * B - B ** 3)

    def f(Z: float) -> float:
        return ((Z + c2) * Z + c1) * Z + c0

    Z = 1.0
    for _ in range(50):
        fz = f(Z)
        dz = (3.0 * Z + 2.0 * c2) * Z + c1
        step = fz / dz
        Z -= step
        if abs(step) < 1e-14:
            break
    if not (Z > B and abs(f(Z)) < 1e-12):
        Z = brentq(f, B + 1e-12, 10.0)
    return Z
