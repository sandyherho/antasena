"""Equations of state: interpolation accuracy, limits, inverses."""
import json
import random
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from antasena import eos
from antasena.constants import PA_PER_BAR, R_GAS
from antasena.eos.pengrobinson import pr_parameters

DATA = json.loads((Path(__file__).parent / "data" / "z_reference_checkpoints.json").read_text())


def test_reference_matches_offgrid_checkpoints():
    worst = max(abs(eos.z(T, p, x) / zr - 1) for T, p, x, zr in DATA["points"])
    assert worst < 1e-5, f"worst relative interpolation error {worst:.2e}"


def test_reference_matches_coolprop_fresh_points():
    CP = pytest.importorskip("CoolProp.CoolProp")
    rng = random.Random(7)
    for _ in range(150):
        T, p, x = rng.uniform(255, 350), rng.uniform(1, 399), rng.uniform(0.0, 1.0)
        zr = CP.PropsSI("Z", "T", T, "P", p * 1e5,
                        f"HEOS::Nitrogen[{1 - x}]&Oxygen[{x}]" if 0 < x < 1 else
                        ("HEOS::Nitrogen" if x == 0 else "HEOS::Oxygen"))
        assert eos.z(T, p, x) == pytest.approx(zr, rel=1e-5)


@pytest.mark.parametrize("model", ["ideal", "pr", "reference"])
def test_low_pressure_limit_is_ideal(model):
    for x in (0.0, 0.2095, 0.5, 1.0):
        assert eos.z(293.15, 0.0, x, model) == 1.0
        assert eos.z(293.15, 0.01, x, model) == pytest.approx(1.0, abs=1e-4)


def test_pr_second_virial_slope():
    """dZ/dP at P -> 0 equals (b - a/RT)/RT for Peng-Robinson."""
    T, x, h = 300.0, 0.32, 1e-3
    a, b = pr_parameters(T, x)
    slope = (eos.z(T, h, x, "pr") - 1.0) / (h * PA_PER_BAR)
    assert slope == pytest.approx((b - a / (R_GAS * T)) / (R_GAS * T), rel=1e-3)


def test_pr_accuracy_band_documented():
    """PR is within 5 % of the reference model below 300 bar (stated in the docs)."""
    for T, p, x, zr in DATA["points"]:
        if p <= 300:
            assert abs(eos.z(T, p, x, "pr") / zr - 1) < 0.05


def test_air_is_superideal_at_fill_pressure():
    assert eos.z(293.15, 300.0, 0.2095) > 1.08
    assert eos.z(293.15, 50.0, 0.2095) < 1.0


@given(st.floats(1.0, 390.0), st.floats(258.0, 350.0), st.floats(0.0, 1.0),
       st.sampled_from(["ideal", "pr", "reference"]))
def test_moles_pressure_inverse(p, T, x, model):
    n = eos.moles(p, 12.0, T, x, model)
    assert eos.pressure_from_moles(n, 12.0, T, x, model) == pytest.approx(p, rel=1e-9)


@given(st.floats(1.0, 390.0), st.floats(1.0, 9.0))
def test_moles_monotone_in_pressure(p, dp):
    assert eos.moles(p + dp, 12, 293.15, 0.32) > eos.moles(p, 12, 293.15, 0.32)


def test_out_of_table_raises():
    with pytest.raises(ValueError):
        eos.z(200.0, 100.0, 0.21)
    with pytest.raises(ValueError):
        eos.z(293.15, 450.0, 0.21)
    with pytest.raises(ValueError):
        eos.z(293.15, 100.0, 1.2)
