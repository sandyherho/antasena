"""Tissue kinetics and limits: closed forms against numerics."""
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from antasena.buhlmann import (ZHL16C_N2, Compartment, TissueState, haldane,
                               ndl_constant_depth, schreiner)
from antasena.environment import Environment

ENV = Environment()


def test_zhl16c_coefficients_against_zhl16a_generating_formulas():
    """b follows b = 1.005 - tau^-1/2; C lowers a below A = 2 tau^-1/3 (never raises it).

    The one exception is the tabulated b of the 18.5-min compartment, 0.7825,
    which lies 0.0100 above the generating formula (0.7725). antasena keeps the
    published value; this test pins the deviation so it cannot change silently.
    """
    assert len(ZHL16C_N2) == 16
    for c in ZHL16C_N2:
        formula = 1.005 - c.half_time ** -0.5
        if c.half_time == 18.5:
            assert c.b - formula == pytest.approx(0.0100, abs=6e-5)
        else:
            assert c.b == pytest.approx(formula, abs=6e-5)
        a_A = 2.0 * c.half_time ** (-1.0 / 3.0)
        assert c.a <= a_A + 6e-5
    for c in ZHL16C_N2[:2]:
        assert c.a == pytest.approx(2.0 * c.half_time ** (-1.0 / 3.0), abs=6e-5)
    hts = [c.half_time for c in ZHL16C_N2]
    assert hts == sorted(hts)


def _rk4(p0, pa0, rate, k, t, n=4000):
    h, p, s = t / n, p0, 0.0
    f = lambda s, p: k * (pa0 + rate * s - p)  # noqa: E731
    for _ in range(n):
        k1 = f(s, p)
        k2 = f(s + h / 2, p + h * k1 / 2)
        k3 = f(s + h / 2, p + h * k2 / 2)
        k4 = f(s + h, p + h * k3)
        p += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        s += h
    return p


@given(st.floats(0.5, 5.0), st.floats(0.5, 5.0), st.floats(-0.5, 0.5),
       st.sampled_from([c.k for c in ZHL16C_N2]), st.floats(0.1, 60.0))
def test_schreiner_solves_the_ode(p0, pa0, rate, k, t):
    assert schreiner(p0, pa0, rate, k, t) == pytest.approx(_rk4(p0, pa0, rate, k, t), rel=1e-10)


@given(st.floats(0.5, 5.0), st.floats(0.5, 5.0), st.floats(0.01, 0.2), st.floats(0.0, 100.0))
def test_schreiner_reduces_to_haldane(p0, pa, k, t):
    assert schreiner(p0, pa, 0.0, k, t) == pytest.approx(haldane(p0, pa, k, t), rel=1e-13)


@given(st.floats(0.0, 40.0), st.floats(0.0, 40.0), st.floats(0.1, 30.0), st.floats(0.05, 0.95))
def test_exposure_is_a_semigroup(d0, d1, t, frac):
    """Splitting a linear ramp at any interior time leaves the result unchanged."""
    a = TissueState.surface_equilibrium(1.01325)
    b = a.copy()
    p0, p1 = ENV.pressure(d0), ENV.pressure(d1)
    a.expose(p0, p1, t, 0.68)
    pm = p0 + (p1 - p0) * frac
    b.expose(p0, pm, t * frac, 0.68)
    b.expose(pm, p1, t * (1 - frac), 0.68)
    for x, y in zip(a.tensions, b.tensions):
        assert x == pytest.approx(y, rel=1e-12)


@given(st.floats(0.6, 5.0), st.floats(0.2, 1.2))
def test_tolerated_and_max_tension_are_inverse(p_amb, gf):
    for c in ZHL16C_N2:
        assert c.tolerated(c.max_tension(p_amb, gf), gf) == pytest.approx(p_amb, rel=1e-12)


def test_gf_one_is_plain_buhlmann():
    c = Compartment(27.0, 0.62, 0.8126)
    assert c.tolerated(2.0, 1.0) == pytest.approx((2.0 - 0.62) * 0.8126)


@pytest.mark.parametrize("fo2,depth,gf", [(0.2095, 30, 1.0), (0.32, 30, 0.85), (0.36, 25, 0.7),
                                           (0.2095, 18, 0.85), (0.40, 20, 1.0)])
def test_ndl_closed_form_against_bruteforce(fo2, depth, gf):
    st0 = TissueState.surface_equilibrium(ENV.surface_pressure)
    p = ENV.pressure(depth)
    ndl = ndl_constant_depth(st0, p, 1 - fo2, ENV.surface_pressure, gf)

    def ok(t):
        s = st0.copy()
        s.expose(p, p, t, 1 - fo2)
        return s.ceiling(gf) <= ENV.surface_pressure

    lo, hi = 0.0, 1000.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    assert ndl == pytest.approx(lo, abs=1e-9)


def test_ndl_values_are_plausible_and_ordered():
    st0 = TissueState.surface_equilibrium(ENV.surface_pressure)
    ndl = lambda f, d: ndl_constant_depth(st0, ENV.pressure(d), 1 - f,  # noqa: E731
                                          ENV.surface_pressure, 1.0)
    air30 = ndl(0.2095, 30)
    assert 12 < air30 < 22          # ZH-L16C, instantaneous descent
    assert ndl(0.32, 30) > air30     # nitrox benefit
    assert ndl(0.2095, 40) < air30   # deeper is shorter
    assert math.isinf(ndl(0.32, 3))  # no limit in very shallow water


def test_ndl_zero_when_already_too_loaded():
    s = TissueState.surface_equilibrium(ENV.surface_pressure)
    s.expose(ENV.pressure(40), ENV.pressure(40), 60, 0.79)
    assert ndl_constant_depth(s, ENV.pressure(40), 0.79, ENV.surface_pressure) == 0.0


@given(st.floats(0.5, 5.0), st.floats(0.5, 5.0), st.floats(-20.0, 20.0),
       st.sampled_from([c.k for c in ZHL16C_N2]), st.floats(1e-4, 30.0))
def test_schreiner_against_50_digit_reference(p0, pa0, rate, k, t):
    """The stable form agrees with the textbook form evaluated in 50-digit arithmetic."""
    from decimal import Decimal, getcontext
    getcontext().prec = 50
    P0, A, R, K, T = map(Decimal, (p0, pa0, rate, k, t))
    exact = A + R * (T - 1 / K) - (A - P0 - R / K) * (-K * T).exp()
    assert schreiner(p0, pa0, rate, k, t) == pytest.approx(float(exact), rel=1e-14, abs=1e-14)
