"""Guaranteed bounds, derivations that agree with the code, unit conversions."""
import math
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from antasena import Environment, Nitrox, explain, mod
from antasena.buhlmann import TissueState, ndl_constant_depth
from antasena.planner import plan_dive
from antasena.uncertainty import Interval, mod_bounds, ndl_bounds, po2_bounds
from antasena.units import Units, bar_to_psi, m_to_ft

ENV = Environment()
iv = st.tuples(st.floats(-50, 50, allow_subnormal=False), st.floats(0, 20, allow_subnormal=False)).map(lambda t: Interval(t[0], t[0] + t[1]))


@given(iv, iv, st.floats(0, 1), st.floats(0, 1))
def test_interval_arithmetic_encloses(a, b, s, t):
    x, y = a.lo + s * a.width, b.lo + t * b.width
    assert x + y in a + b
    assert x - y in a - b
    prod = a * b
    assert prod.lo - 1e-9 <= x * y <= prod.hi + 1e-9
    if not (b.lo <= 0 <= b.hi):
        q = a / b
        assert q.lo - 1e-9 <= x / y <= q.hi + 1e-9


@given(st.floats(0.22, 0.6), st.floats(0.001, 0.02), st.floats(1.2, 1.6))
def test_mod_bounds_are_exact_hull(f, df, lim):
    b = mod_bounds(f, df, lim)
    rng = random.Random(1)
    for _ in range(50):
        g = Nitrox(f + rng.uniform(-df, df))
        assert b.lo - 1e-9 <= mod(g, lim) <= b.hi + 1e-9
    assert b.lo == pytest.approx(mod(Nitrox(f + df), lim))


@given(st.floats(0.22, 0.4), st.floats(0.0, 0.02), st.floats(15.0, 35.0), st.floats(0.0, 1.0))
def test_ndl_bounds_enclose(f, df, d, dd):
    b = ndl_bounds(f, df, d, 0.85, depth_error=dd)
    st0 = TissueState.surface_equilibrium(ENV.surface_pressure)
    rng = random.Random(2)
    for _ in range(30):
        ff = f + rng.uniform(-df, df)
        dep = max(0.0, d + rng.uniform(-dd, dd))
        n = ndl_constant_depth(st0, ENV.pressure(dep), 1 - ff, ENV.surface_pressure, 0.85)
        assert b.lo - 1e-9 <= n <= b.hi + 1e-9 or math.isinf(b.hi)


def test_po2_bounds():
    b = po2_bounds(Interval(0.31, 0.33), Interval(29, 31))
    assert b.lo == pytest.approx(0.31 * ENV.pressure(29))
    assert b.hi == pytest.approx(0.33 * ENV.pressure(31))


def test_derivations_agree_with_library():
    g = Nitrox.ean(32)
    assert explain.explain_mod(g).result == pytest.approx(mod(g))
    assert explain.explain_best_mix(30).result == pytest.approx(0.34)
    from antasena import ead_exact
    assert explain.explain_ead(g, 30).result == pytest.approx(ead_exact(g, 30))
    st0 = TissueState.surface_equilibrium(ENV.surface_pressure)
    nd = ndl_constant_depth(st0, ENV.pressure(30), g.fn2, ENV.surface_pressure, 0.85)
    d = explain.explain_ndl(g, 30, 0.85)
    assert d.result == pytest.approx(nd)
    assert f"{nd:.2f} min" in d.to_text()
    from antasena import blending
    assert explain.explain_blend(0.32, 200).result == \
        pytest.approx(blending.plan_partial_pressure(0.32, 200).fill_add_to)
    r = plan_dive([(30, 20)], g, record_trace=False)
    assert explain.explain_oxygen(r).result == pytest.approx(r.cns)
    assert "Result" in explain.explain_free_gas(232, 0.32).to_text()


@given(st.floats(-100, 1000))
def test_unit_round_trips(x):
    for sysname in ("metric", "imperial"):
        u = Units(sysname)
        assert u.depth_in(u.depth_out(x)) == pytest.approx(x, abs=1e-9)
        assert u.pressure_in(u.pressure_out(x)) == pytest.approx(x, abs=1e-9)
        assert u.volume_in(u.volume_out(x)) == pytest.approx(x, abs=1e-9)
        assert u.temp_in(u.temp_out(x)) == pytest.approx(x, abs=1e-9)


def test_unit_constants():
    assert m_to_ft(0.3048) == pytest.approx(1.0, rel=1e-15)
    assert bar_to_psi(1.0) == pytest.approx(14.503773773, rel=1e-9)
