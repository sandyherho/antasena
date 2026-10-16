"""Dive planner: hard invariants of the decompression schedule and budgets."""
import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from antasena import AIR, Environment, Level, Nitrox, Tank, plan_dive, surface_interval
from antasena.planner import DiverState, PlanError
from antasena.toxicity import cns_segment

ENV = Environment()
EAN50, O2 = Nitrox.ean(50), Nitrox(1.0)


def _ceiling_respected(r, tol=1e-6):
    """The diver is never shallower than the ceiling at the GF in force."""
    for p in r.trace:
        assert p["ceiling"] <= p["depth"] + tol, p


def test_no_deco_within_ndl():
    g = Nitrox.ean(32)
    r0 = plan_dive([Level(30, 1)], g, gf_low=0.3, gf_high=0.85, record_trace=False)
    bt = math.floor(r0.ndl) - 1
    r = plan_dive([Level(30, bt)], g, gf_low=0.3, gf_high=0.85)
    assert not r.deco
    assert [(s.depth, s.minutes) for s in r.stops] == [(5.0, 3.0)]  # safety stop only
    _ceiling_respected(r)


def test_just_past_ndl_keeps_safety_stop():
    r = plan_dive([Level(30, 20)], Nitrox.ean(32), gf_low=0.3, gf_high=0.85)
    assert r.ndl < 20
    assert any(s.depth == 5.0 for s in r.stops) or r.deco
    assert r.stops, "a dive past the NDL must never end without any stop"
    _ceiling_respected(r)


def test_deco_beyond_ndl():
    r0 = plan_dive([Level(30, 1)], AIR, gf_low=0.3, gf_high=0.85, record_trace=False)
    r = plan_dive([Level(30, math.ceil(r0.ndl) + 10)], AIR, gf_low=0.3, gf_high=0.85)
    assert r.deco and any(s.depth >= 3 for s in r.stops)
    _ceiling_respected(r)


@settings(max_examples=25, deadline=None)
@given(st.floats(20, 50), st.floats(10, 50), st.floats(0.2, 0.6), st.floats(0.7, 1.0),
       st.booleans())
def test_ceiling_never_violated(depth, minutes, gfl, gfh, with_deco_gas):
    gas = Nitrox(round(min(0.36, 1.4 / ENV.pressure(depth)), 2))
    r = plan_dive([Level(depth, minutes)], gas, [EAN50, O2] if with_deco_gas else [],
                  gf_low=min(gfl, gfh), gf_high=gfh)
    _ceiling_respected(r)
    assert r.final_state.tissues.ceiling(gfh) <= ENV.surface_pressure + 1e-9


def test_stops_are_minimal_last_stop():
    """Leaving the last stop one minute early violates the surfacing limit."""
    r = plan_dive([Level(40, 25)], Nitrox.ean(28), [EAN50], gf_low=0.3, gf_high=0.85)
    last = r.stops[-1]
    seg_idx = max(i for i, s in enumerate(r.segments) if s.kind == "stop")
    st = DiverState.fresh(ENV).tissues
    for s in r.segments[:seg_idx]:
        st.expose(s.p_start, s.p_end, s.minutes, s.gas.fn2)
    # st is now at the beginning of the final minute of the last stop
    st.expose(ENV.pressure(last.depth), ENV.surface_pressure, last.depth / 9.0, last.gas.fn2)
    assert st.ceiling(0.85) > ENV.surface_pressure


def test_gas_switch_at_mod_on_grid():
    r = plan_dive([Level(45, 25)], Nitrox.ean(28), [EAN50, O2], gf_low=0.3, gf_high=0.85)
    switches = [(s.gas.name, s.depth_start) for s in r.segments if s.kind == "switch"]
    # MOD at 1.6 bar in sea water: EAN50 21.8 m -> 21 m; O2 5.84 m -> 3 m, because
    # at 6 m pure O2 gives 1.616 bar (the rounded 10 m/bar rule would allow 6 m).
    assert switches == [("EAN50", 21.0), ("O2", 3.0)]
    r2 = plan_dive([Level(45, 25)], Nitrox.ean(28), [EAN50, O2], gf_low=0.3, gf_high=0.85,
                   env=Environment.training_tables())
    assert ("O2", 6.0) in [(s.gas.name, s.depth_start) for s in r2.segments if s.kind == "switch"]
    for s in r.segments:
        assert s.po2_start <= 1.6 + 1e-9 and s.po2_end <= 1.6 + 1e-9


def test_po2_above_1_6_rejected():
    with pytest.raises(PlanError):
        plan_dive([Level(40, 10)], Nitrox.ean(40))


def test_budgets_are_sums_of_exact_segment_integrals():
    r = plan_dive([Level(25, 30)], Nitrox.ean(32), sac=20, record_trace=False)
    assert r.cns == pytest.approx(sum(cns_segment(s.po2_start, s.po2_end, s.minutes)
                                      for s in r.segments), rel=1e-12)
    used = sum(20 * 0.5 * (s.p_start + s.p_end) / 1.01325 * s.minutes for s in r.segments)
    assert sum(r.gas_used.values()) == pytest.approx(used, rel=1e-12)


def test_repetitive_dive_has_shorter_ndl():
    g = Nitrox.ean(32)
    r1 = plan_dive([Level(25, 40)], g, record_trace=False)
    st = surface_interval(r1.final_state, 60, ENV)
    r2 = plan_dive([Level(25, 1)], g, initial=st, record_trace=False)
    fresh = plan_dive([Level(25, 1)], g, record_trace=False)
    assert r2.ndl < fresh.ndl
    assert st.cns == pytest.approx(r1.cns * 0.5 ** (60 / 90))


def test_altitude_shortens_ndl():
    g = Nitrox.ean(32)
    sea = plan_dive([Level(20, 1)], g, record_trace=False).ndl
    alt = plan_dive([Level(20, 1)], g, env=Environment(water="fresh", altitude_m=2000),
                    record_trace=False).ndl
    assert alt < sea


def test_trace_flag_does_not_change_schedule():
    a = plan_dive([Level(40, 25)], Nitrox.ean(28), [EAN50], record_trace=True)
    b = plan_dive([Level(40, 25)], Nitrox.ean(28), [EAN50], record_trace=False)
    assert [(s.depth, s.minutes, s.gas) for s in a.stops] == \
        [(s.depth, s.minutes, s.gas) for s in b.stops]


def test_out_of_gas_is_flagged():
    r = plan_dive([Level(30, 40)], Nitrox.ean(30), tanks=[Tank(Nitrox.ean(30), 10, 150)],
                  record_trace=False)
    assert r.tank_report[0]["out_of_gas"]
    assert any("OUT OF GAS" in w for w in r.warnings)


def test_real_gas_leaves_less_than_ideal_estimate():
    r = plan_dive([Level(20, 30)], Nitrox.ean(32), tanks=[Tank(Nitrox.ean(32), 12, 232)],
                  record_trace=False)
    rep = r.tank_report[0]
    assert rep["end_reference"] < rep["end_ideal"]


def test_multilevel_runs():
    r = plan_dive([Level(30, 10), Level(18, 20), Level(12, 15)], Nitrox.ean(32))
    assert r.ndl is None and r.runtime > 45
    _ceiling_respected(r)
