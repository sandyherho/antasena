"""Closed-form CNS and OTU integrals against quadrature."""
import pytest
from hypothesis import given
from hypothesis import strategies as st

from antasena.toxicity import (_BREAKS, NOAA_SINGLE, OxygenLimitError,
                               cns_after_surface_interval, cns_limit, cns_rate, cns_segment,
                               otu_segment)

po2 = st.floats(0.2, 1.6)


def simpson(f, a, b, n=20000):
    h = (b - a) / n
    s = f(a) + f(b)
    for i in range(1, n):
        s += (4 if i % 2 else 2) * f(a + i * h)
    return s * h / 3


@pytest.mark.parametrize("p,limit", NOAA_SINGLE)
def test_cns_one_limit_is_100_percent(p, limit):
    assert cns_segment(p, p, limit) == pytest.approx(1.0, rel=1e-12)


def test_cns_below_0_6_follows_baker():
    """Baker's line T = 1800 - 1800 PO2 on (0.5, 0.6]; nothing at or below 0.5 bar."""
    assert cns_rate(0.6 - 1e-12) == pytest.approx(cns_rate(0.6), rel=1e-9)
    assert cns_rate(0.5) == 0.0
    for p in (0.51, 0.55, 0.59):
        assert 1.0 / cns_rate(p) == pytest.approx(1800 - 1800 * p, rel=1e-12)


@pytest.mark.parametrize("lo,hi,m,b", [(0.5, 0.6, -1800, 1800), (0.6, 0.7, -1500, 1620),
                                        (0.7, 0.8, -1200, 1410), (0.8, 0.9, -900, 1170),
                                        (0.9, 1.1, -600, 900), (1.1, 1.5, -300, 570),
                                        (1.5, 1.6, -750, 1245)])
def test_limits_equal_baker_coefficient_table(lo, hi, m, b):
    for f in (0.25, 0.5, 0.75):
        p = lo + f * (hi - lo)
        assert 1.0 / cns_rate(p) == pytest.approx(m * p + b, rel=1e-12)


@given(po2, po2, st.floats(0.1, 120.0))
def test_cns_closed_form_matches_quadrature(pa, pb, t):
    exact = cns_segment(pa, pb, t)
    # the integrand has kinks at the table nodes: integrate piecewise between them
    cuts = sorted({0.0, t, *[(b - pa) / (pb - pa) * t for b in _BREAKS
                             if pb != pa and min(pa, pb) < b < max(pa, pb)]})
    # rate jumps from 0 to 1/900 at 0.5 bar: use the one-sided value on each piece
    def piece(c0, c1):
        pm = pa + (pb - pa) * 0.5 * (c0 + c1) / t
        if pm <= 0.5:
            return 0.0
        return simpson(lambda s: 1.0 / cns_limit(max(0.5, pa + (pb - pa) * s / t)), c0, c1, 2000)
    num = sum(piece(c0, c1) for c0, c1 in zip(cuts, cuts[1:]))
    assert exact == pytest.approx(num, rel=1e-6, abs=1e-12)


@given(st.floats(0.2, 3.0), st.floats(0.2, 3.0), st.floats(0.1, 300.0))
def test_otu_closed_form_matches_quadrature(pa, pb, t):
    exact = otu_segment(pa, pb, t)
    u = lambda p: max(0.0, (p - 0.5) / 0.5) ** (5 / 6)  # noqa: E731
    num = simpson(lambda s: u(pa + (pb - pa) * s / t), 0.0, t, 40000)
    assert exact == pytest.approx(num, rel=2e-5, abs=1e-9)


def test_otu_reference_values():
    assert otu_segment(1.0, 1.0, 60) == pytest.approx(60.0)
    assert otu_segment(0.5, 0.5, 600) == 0.0
    assert otu_segment(1.4, 1.4, 30) == pytest.approx(30 * 1.8 ** (5 / 6))


@given(po2, po2, st.floats(1.0, 60.0), st.floats(0.05, 0.95))
def test_additivity(pa, pb, t, f):
    pm = pa + (pb - pa) * f
    for fn in (cns_segment, otu_segment):
        whole = fn(pa, pb, t)
        parts = fn(pa, pm, t * f) + fn(pm, pb, t * (1 - f))
        assert whole == pytest.approx(parts, rel=1e-9, abs=1e-14)


@given(po2, po2, st.floats(0.5, 60.0))
def test_direction_symmetry(pa, pb, t):
    assert cns_segment(pa, pb, t) == pytest.approx(cns_segment(pb, pa, t), rel=1e-12, abs=1e-15)
    assert otu_segment(pa, pb, t) == pytest.approx(otu_segment(pb, pa, t), rel=1e-12, abs=1e-15)


def test_above_noaa_range_raises():
    with pytest.raises(OxygenLimitError):
        cns_segment(1.5, 1.7, 5)


def test_surface_half_life():
    assert cns_after_surface_interval(0.8, 90) == pytest.approx(0.4)
    assert cns_after_surface_interval(0.8, 0) == 0.8
