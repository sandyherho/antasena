"""Hydrostatics and Dalton-law quantities: MOD, best mix, EAD, END."""
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from antasena import AIR, Environment, Nitrox, best_mix, ead, ead_exact, end, mod
from antasena.buhlmann import TissueState, ndl_constant_depth
from antasena.constants import FN2_AIR, P_H2O_ALV
from antasena.environment import surface_pressure_isa

ENV = Environment()
TT = Environment.training_tables()
fo2s = st.floats(0.21, 1.0)
depths = st.floats(0.0, 80.0)


def test_isa_sea_level_and_1000m():
    assert surface_pressure_isa(0.0) == pytest.approx(1.01325, abs=1e-12)
    # ISA at 1000 m: 89 874.6 Pa
    assert surface_pressure_isa(1000.0) == pytest.approx(0.898746, abs=2e-5)


def test_training_convention_is_ten_meters_per_bar():
    assert TT.bar_per_meter == pytest.approx(0.1, rel=1e-15)
    assert TT.pressure(10) == pytest.approx(2.0)


@given(depths)
def test_depth_pressure_inverse(d):
    assert ENV.depth(ENV.pressure(d)) == pytest.approx(d, abs=1e-12)


def test_negative_depth_rejected():
    with pytest.raises(ValueError):
        ENV.pressure(-1)


@pytest.mark.parametrize("pct,expected", [(32, 33.75), (36, 1.4 / 0.36 * 10 - 10), (40, 25.0)])
def test_mod_training_tables(pct, expected):
    assert mod(Nitrox.ean(pct), 1.4, TT) == pytest.approx(expected, abs=1e-12)


def test_mod_physical_closed_form():
    g = Nitrox.ean(32)
    expected = (1.4 / 0.32 - 1.01325) / (1025 * 9.80665 / 1e5)
    assert mod(g, 1.4) == pytest.approx(expected, rel=1e-14)


@given(fo2s, st.floats(0.5, 1.6))
def test_po2_at_mod_equals_limit(f, lim):
    g = Nitrox(f)
    m = mod(g, lim)
    if m > 0:
        assert f * ENV.pressure(m) == pytest.approx(lim, rel=1e-12)


@given(st.floats(0.21, 0.99), st.floats(1e-4, 0.01))
def test_mod_strictly_decreasing_in_fo2(f, df):
    assert mod(Nitrox(f + df)) <= mod(Nitrox(f))


@given(st.floats(0.0, 60.0), st.floats(1.2, 1.6))
def test_best_mix_is_feasible_and_maximal(d, lim):
    g = best_mix(d, lim)
    p = ENV.pressure(d)
    assert g.fo2 * p <= lim + 1e-12
    if g.fo2 < 1.0:
        assert (g.fo2 + 0.01) * p > lim - 1e-12


def test_ead_of_air_is_identity():
    for d in (0, 10, 33.3, 50):
        assert ead(AIR, d) == pytest.approx(d, abs=1e-12)
        assert ead_exact(AIR, d) == pytest.approx(d, abs=1e-12)


@given(st.floats(0.22, 0.6), st.floats(0.0, 40.0))
def test_exact_ead_gap_formula(f, d):
    g = Nitrox(f)
    gap = (ead_exact(g, d) - ead(g, d)) * ENV.bar_per_meter
    assert gap == pytest.approx(P_H2O_ALV * (1 - g.fn2 / FN2_AIR), abs=1e-12)
    assert gap > 0  # classical EAD is the shallower (non-conservative) one


@given(st.floats(0.22, 0.5), st.floats(5.0, 35.0), st.floats(1.0, 120.0))
def test_exact_ead_equivalence_theorem(f, d, t):
    """Nitrox at d loads every compartment exactly like air at EAD_exact(d)."""
    g = Nitrox(f)
    nx = TissueState.surface_equilibrium(ENV.surface_pressure)
    ar = nx.copy()
    nx.expose(ENV.pressure(d), ENV.pressure(d), t, g.fn2)
    e = ead_exact(g, d)
    if e < 0:
        return
    ar.expose(ENV.pressure(e), ENV.pressure(e), t, AIR.fn2)
    for a, b in zip(nx.tensions, ar.tensions):
        assert a == pytest.approx(b, rel=1e-12)
    st0 = TissueState.surface_equilibrium(ENV.surface_pressure)
    n1 = ndl_constant_depth(st0, ENV.pressure(d), g.fn2, ENV.surface_pressure, 0.85)
    n2 = ndl_constant_depth(st0, ENV.pressure(e), AIR.fn2, ENV.surface_pressure, 0.85)
    if math.isfinite(n1):
        assert n1 == pytest.approx(n2, rel=1e-10)


def test_end_conventions():
    g = Nitrox.ean(32)
    assert end(g, 30) == 30
    assert end(g, 30, o2_narcotic=False) == pytest.approx(ead(g, 30))


def test_nitrox_validation_and_names():
    with pytest.raises(ValueError):
        Nitrox(0.0)
    with pytest.raises(ValueError):
        Nitrox(1.2)
    assert AIR.name == "Air" and Nitrox(1.0).name == "O2" and Nitrox.ean(32).name == "EAN32"
