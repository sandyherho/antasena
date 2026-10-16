"""Independent re-computation of antasena results.

Nothing here reuses antasena's mathematics. Tissue loading is integrated with
classical RK4 at a 1-second step; CNS uses Baker's published coefficient
table; OTU is integrated numerically; gas thermodynamics calls CoolProp
directly; MOD, EAD and best mix are written out by hand. antasena is used
only to produce the results being checked.

Run:  python tools/independent_check.py      (needs CoolProp)
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import CoolProp.CoolProp as CP  # noqa: E402

import antasena as A  # noqa: E402
from antasena import blending, cylinder  # noqa: E402

FAIL = []


def check(name, got, ref, tol, unit=""):
    ok = abs(got - ref) <= tol
    print(f"  [{'ok' if ok else 'FAIL'}] {name}: antasena {got:.6g}{unit}, independent {ref:.6g}{unit}"
          f" (|diff| {abs(got - ref):.2g}, tol {tol:g})")
    if not ok:
        FAIL.append(name)


# ---------------------------------------------------------------- constants (typed again)
PS, RHO, G, PW, FN2AIR = 1.01325, 1025.0, 9.80665, 0.0627, 1 - 0.2095
BPM = RHO * G / 1e5
P = lambda d: PS + BPM * d  # noqa: E731
ZHL16C = [(5.0, 1.1696, 0.5578), (8.0, 1.0, 0.6514), (12.5, 0.8618, 0.7222), (18.5, 0.7562, 0.7825),
          (27.0, 0.62, 0.8126), (38.3, 0.5043, 0.8434), (54.3, 0.441, 0.8693), (77.0, 0.4, 0.8910),
          (109.0, 0.375, 0.9092), (146.0, 0.35, 0.9222), (187.0, 0.3295, 0.9319), (239.0, 0.3065, 0.9403),
          (305.0, 0.2835, 0.9477), (390.0, 0.261, 0.9544), (498.0, 0.248, 0.9602), (635.0, 0.2327, 0.9653)]
BAKER = [(0.5, 0.6, -1800, 1800), (0.6, 0.7, -1500, 1620), (0.7, 0.8, -1200, 1410),
         (0.8, 0.9, -900, 1170), (0.9, 1.1, -600, 900), (1.1, 1.5, -300, 570), (1.5, 1.6, -750, 1245)]
DT = 1.0 / 60.0  # one second, in minutes


def rk4_step(tens, pamb0, pamb1, fn2, h):
    """Advance all tensions by h with ambient pressure linear from pamb0 to pamb1 over h."""
    out = []
    for p, (tau, _, _) in zip(tens, ZHL16C):
        k = math.log(2) / tau
        palv = lambda s: (pamb0 + (pamb1 - pamb0) * s / h - PW) * fn2  # noqa: E731
        f = lambda s, x: k * (palv(s) - x)  # noqa: E731
        k1 = f(0, p)
        k2 = f(h / 2, p + h * k1 / 2)
        k3 = f(h / 2, p + h * k2 / 2)
        k4 = f(h, p + h * k3)
        out.append(p + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6)
    return out


def ceiling(tens, gf):
    return max((p - a * gf) / (gf / b + 1 - gf) for p, (_, a, b) in zip(tens, ZHL16C))


def baker_limit(p):
    for lo, hi, m, b in BAKER:
        if lo < p <= hi + 1e-12:
            return m * p + b
    return None


# ---------------------------------------------------------------- 1. hand formulas
print("1. Dalton-law quantities (hand formulas)")
for pct in (32, 36, 40):
    f = pct / 100
    check(f"MOD EAN{pct} @1.4", A.mod(A.Nitrox(f), 1.4), (1.4 / f - PS) / BPM, 1e-9, " m")
check("best mix 30 m @1.4", A.best_mix(30).fo2, math.floor(100 * 1.4 / P(30)) / 100, 1e-12)
for pct, d in ((32, 30), (36, 25)):
    f = pct / 100
    classical = (P(d) * (1 - f) / FN2AIR - PS) / BPM
    exact = ((P(d) - PW) * (1 - f) / FN2AIR + PW - PS) / BPM
    check(f"EAD classical EAN{pct} {d} m", A.ead(A.Nitrox(f), d), classical, 1e-9, " m")
    check(f"EAD exact EAN{pct} {d} m", A.ead_exact(A.Nitrox(f), d), exact, 1e-9, " m")
check("ISA pressure at 1000 m", A.Environment(altitude_m=1000).surface_pressure, 0.898746, 2e-5,
      " bar")

# ---------------------------------------------------------------- 2. NDL by stepping
print("2. No-decompression limits, RK4 stepping at 1 s vs closed form")
for f, d, gf in ((0.2095, 30, 1.0), (0.2095, 30, 0.85), (0.32, 30, 0.85), (0.36, 25, 0.85),
                 (0.32, 18, 0.85), (0.2095, 40, 0.7)):
    tens = [(PS - PW) * FN2AIR] * 16
    lim = [PS + gf * (a + PS / b - PS) for _, a, b in ZHL16C]
    t = 0.0
    while all(p <= m for p, m in zip(tens, lim)) and t < 600:
        tens = rk4_step(tens, P(d), P(d), 1 - f, DT)
        t += DT
    st = A.TissueState.surface_equilibrium(PS)
    from antasena.buhlmann import ndl_constant_depth
    ndl = ndl_constant_depth(st, P(d), 1 - f, PS, gf)
    check(f"NDL {100 * f:.1f}% {d} m GF{100 * gf:.0f}", ndl, t - DT / 2, DT / 2 + 1e-9, " min")

# ---------------------------------------------------------------- 3. plan replay
print("3. Plans replayed at 1 s: tensions, ceiling at every second, CNS, OTU, gas")
cases = [
    ("EAN32 30 m 20 min, GF 30/85", [(30, 20)], A.Nitrox.ean(32), [], 0.3, 0.85),
    ("Air 30 m 30 min, GF 30/85", [(30, 30)], A.AIR, [], 0.3, 0.85),
    ("EAN28 40 m 25 min + EAN50, GF 30/85", [(40, 25)], A.Nitrox.ean(28), [A.Nitrox.ean(50)], 0.3, 0.85),
    ("EAN25 45 m 30 min + EAN50 + O2, GF 50/80", [(45, 30)], A.Nitrox.ean(25),
     [A.Nitrox.ean(50), A.Nitrox(1.0)], 0.5, 0.8),
    ("Multilevel EAN32 30/18/12 m", [(30, 10), (18, 20), (12, 15)], A.Nitrox.ean(32), [], 0.3, 0.85),
]
for name, levels, gas, deco, gfl, gfh in cases:
    r = A.plan_dive(levels, gas, deco, gf_low=gfl, gf_high=gfh, sac=20, record_trace=False)
    p_first = P(r.first_stop) if r.first_stop is not None else None

    def gf_at(p):
        if p_first is None:
            return gfh
        if p >= p_first:
            return gfl
        return gfh + (gfl - gfh) * (p - PS) / (p_first - PS)

    tens = [(PS - PW) * FN2AIR] * 16
    cns = otu = gasl = 0.0
    worst = -1e9
    for s in r.segments:
        n = max(1, round(s.minutes / DT))
        h = s.minutes / n
        for i in range(n):
            pa = s.p_start + (s.p_end - s.p_start) * i / n
            pb = s.p_start + (s.p_end - s.p_start) * (i + 1) / n
            tens = rk4_step(tens, pa, pb, s.gas.fn2, h)
            pm = 0.5 * (pa + pb)
            po2 = s.gas.fo2 * pm
            if po2 > 0.5:
                cns += h / baker_limit(po2)
                otu += h * ((po2 - 0.5) / 0.5) ** (5 / 6)
            gasl += 20 * pm / 1.01325 * h
            if s.kind in ("ascent", "stop", "switch", "safety"):
                worst = max(worst, ceiling(tens, gf_at(pb)) - pb)
    print(f" {name}: stops {[(st.depth, st.minutes, st.gas.name) for st in r.stops]}")
    check("  final tension max rel diff", max(abs(x / y - 1) for x, y in
                                               zip(r.final_state.tissues.tensions, tens)), 0.0, 1e-9)
    check("  ceiling above diver, worst second of ascent", max(0.0, worst), 0.0, 1e-6, " bar")
    check("  CNS", r.cns, cns, 2e-4)
    check("  OTU", r.otu, otu, 0.05)
    check("  gas used", sum(r.gas_used.values()), gasl, 1e-6 * gasl, " L")

# ---------------------------------------------------------------- 4. gas thermodynamics
print("4. Gas thermodynamics, CoolProp called directly")
T, V = 293.15, 0.012
fluid = lambda x: ("HEOS::Oxygen" if x >= 1 else f"HEOS::Nitrogen[{1 - x}]&Oxygen[{x}]")  # noqa: E731


def n_of(p_abs_bar, x):
    return CP.PropsSI("Dmolar", "T", T, "P", p_abs_bar * 1e5, fluid(x)) * V


def p_of(n, x):
    return CP.PropsSI("P", "T", T, "Dmolar", n / V, fluid(x)) / 1e5


for target in (0.32, 0.36):
    plan = blending.plan_partial_pressure(target, 200.0, temperature_c=20.0)
    n0 = n_of(1.01325, 0.2095)
    lo, hi = 0.0, 50.0
    for _ in range(100):                       # O2 to add so the gauge reads plan.fill_add_to
        nA = 0.5 * (lo + hi)
        x1 = (n0 * 0.2095 + nA) / (n0 + nA)
        lo, hi = (nA, hi) if p_of(n0 + nA, x1) < plan.fill_add_to + 1.01325 else (lo, nA)
    n1, lo, hi = n0 + nA, 0.0, 200.0
    for _ in range(100):                       # air to add until the gauge reads 200 bar
        nB = 0.5 * (lo + hi)
        xf = (n1 * x1 + nB * 0.2095) / (n1 + nB)
        lo, hi = (nB, hi) if p_of(n1 + nB, xf) < 201.01325 else (lo, nB)
    check(f"EAN{100 * target:.0f}: O2 fraction after following antasena's fill", xf, target, 2e-5)

for p in (200.0, 232.0, 300.0):
    ref = (n_of(p + 1.01325, 0.2095) - n_of(1.01325, 0.2095)) * 8.314462618 * T / 1.01325e5 * 1e3
    check(f"usable air in 12 L at {p:g} bar", cylinder.free_gas(p, 0.2095), ref, 2e-4 * ref, " L")

T1, T2 = 318.15, 293.15
n = CP.PropsSI("Dmolar", "T", T1, "P", 231.01325e5, fluid(0.32)) * V
p2 = CP.PropsSI("P", "T", T2, "Dmolar", n / V, fluid(0.32)) / 1e5 - 1.01325
check("230 bar at 45 C cools to 20 C", cylinder.settled_pressure(230, 45, 20, 0.32), p2, 0.01, " bar")

print()
print("ALL CHECKS PASSED" if not FAIL else f"{len(FAIL)} FAILED: {FAIL}")
sys.exit(1 if FAIL else 0)
