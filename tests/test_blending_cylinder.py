"""Blending conservation laws and cylinder thermodynamics."""
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from antasena import blending, cylinder, eos
from antasena.constants import FO2_AIR, P_ATM, T0_C


def test_ideal_absolute_reduces_to_textbook_formula():
    p = blending.plan_partial_pressure(0.32, 200.0, start_pressure=0.0, model="ideal",
                                       gauge=False)
    assert p.fill_add_to == pytest.approx(blending.ideal_o2_pressure(0.32, 200.0), rel=1e-12)
    assert p.fill_add_to == pytest.approx(200 * (0.32 - FO2_AIR) / (1 - FO2_AIR), rel=1e-12)


@settings(max_examples=60, deadline=None)
@given(st.floats(0.22, 0.40), st.floats(150.0, 300.0), st.floats(0.0, 60.0),
       st.floats(0.21, 0.40), st.floats(5.0, 35.0), st.sampled_from(["reference", "pr", "ideal"]))
def test_conservation_of_moles_and_oxygen(ft, pt, p0, f0, Tc, model):
    plan = blending.plan_partial_pressure(ft, pt, start_pressure=p0, start_fo2=f0,
                                          temperature_c=Tc, model=model)
    assume(plan.feasible)
    T = Tc + T0_C
    nf = eos.moles(pt + P_ATM, 12.0, T, ft, model)
    assert plan.n_start + plan.n_add + plan.n_top == pytest.approx(nf, rel=1e-12)
    assert (plan.n_start * f0 + plan.n_add * 1.0 + plan.n_top * FO2_AIR
            == pytest.approx(nf * ft, rel=1e-12))
    # the intermediate gauge reading holds exactly n0 + nA at the intermediate composition
    n1 = plan.n_start + plan.n_add
    x1 = (plan.n_start * f0 + plan.n_add) / n1
    assert eos.moles(plan.fill_add_to + P_ATM, 12.0, T, x1, model) == pytest.approx(n1, rel=1e-9)
    # topping the intermediate fill with air reproduces the target fraction
    assert blending.top_off(plan.fill_add_to, x1, pt, temperature_c=Tc, model=model) == \
        pytest.approx(ft, abs=1e-9)


def test_real_gas_shifts_the_o2_target():
    real = blending.plan_partial_pressure(0.32, 200.0)
    ideal = blending.plan_partial_pressure(0.32, 200.0, model="ideal")
    assert abs(real.fill_add_to - ideal.fill_add_to) > 0.5


def test_infeasible_requires_drain_and_drain_suffices():
    p = blending.plan_partial_pressure(0.32, 200.0, start_pressure=150.0, start_fo2=0.50)
    assert not p.feasible and p.drain_to is not None and 0 < p.drain_to < 150
    q = blending.plan_partial_pressure(0.32, 200.0, start_pressure=p.drain_to, start_fo2=0.50)
    assert q.feasible
    assert min(q.n_add, q.n_top) == pytest.approx(0.0, abs=1e-9 * q.n_final)


def test_target_outside_hull_rejected():
    with pytest.raises(ValueError):
        blending.plan_partial_pressure(0.15, 200)


def test_free_gas_real_less_than_ideal_at_high_pressure():
    r = cylinder.free_gas(300.0, FO2_AIR)
    i = cylinder.free_gas(300.0, FO2_AIR, model="ideal")
    assert r < 0.93 * i
    assert i == pytest.approx(300.0 * 12.0 / P_ATM, rel=1e-12)  # ideal: P_gauge V / P_atm


@given(st.floats(50.0, 300.0), st.floats(25.0, 60.0), st.floats(0.0, 24.0))
def test_cooling_round_trip(p, th, tc):
    p2 = cylinder.settled_pressure(p, th, tc, 0.32)
    assert p2 < p
    assert cylinder.settled_pressure(p2, tc, th, 0.32) == pytest.approx(p, rel=1e-9)


def test_pressure_after_use():
    assert cylinder.pressure_after_use(200, 0.0, 0.32) == pytest.approx(200, rel=1e-10)
    g = cylinder.free_gas(200, 0.32)
    assert cylinder.pressure_after_use(200, g, 0.32) == pytest.approx(0.0, abs=1e-7)
    assert cylinder.pressure_after_use(200, 600, 0.32, model="ideal") == \
        pytest.approx(200.0 - 600.0 * P_ATM / 12.0, rel=1e-12)
