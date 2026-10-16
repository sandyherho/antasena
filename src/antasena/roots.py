"""Bracketing root finder (Brent 1973) in pure Python.

Brent's method combines bisection, secant and inverse quadratic
interpolation. It keeps a sign-changing bracket at every iteration, so it
converges for any continuous function with ``f(a) f(b) <= 0``, and it is
superlinear near a simple root.
"""
from __future__ import annotations

import math
from typing import Callable

__all__ = ["brentq", "RootError"]


class RootError(ValueError):
    """Raised when no sign change brackets a root."""


def brentq(f: Callable[[float], float], a: float, b: float, *,
           xtol: float = 1e-12, rtol: float = 4 * 2.220446049250313e-16,
           maxiter: int = 200) -> float:
    fa, fb = f(a), f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        raise RootError(f"no sign change on [{a}, {b}]: f(a)={fa}, f(b)={fb}")
    c, fc = a, fa
    d = e = b - a
    for _ in range(maxiter):
        if fb * fc > 0.0:
            c, fc = a, fa
            d = e = b - a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol = 2.0 * rtol * abs(b) + 0.5 * xtol
        m = 0.5 * (c - b)
        if abs(m) <= tol or fb == 0.0:
            return b
        if abs(e) >= tol and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p, q = 2.0 * m * s, 1.0 - s
            else:
                q, r = fa / fc, fb / fc
                p = s * (2.0 * m * q * (q - r) - (b - a) * (r - 1.0))
                q = (q - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0.0:
                q = -q
            p = abs(p)
            if 2.0 * p < min(3.0 * m * q - abs(tol * q), abs(e * q)):
                e, d = d, p / q
            else:
                d = e = m
        else:
            d = e = m
        a, fa = b, fb
        b += d if abs(d) > tol else math.copysign(tol, m)
        fb = f(b)
    raise RootError("brentq did not converge")
