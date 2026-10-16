"""Print the quantitative validation numbers quoted in README and docs.

Run:  python tools/validation_report.py
Only the standard library and antasena are needed (CoolProp optional).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from antasena import AIR, Environment, Nitrox, blending, cylinder, eos, mod  # noqa: E402
from antasena.buhlmann import TissueState, ndl_constant_depth  # noqa: E402
from antasena.gas import ead, ead_exact  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
pts = json.loads((ROOT / "tests" / "data" / "z_reference_checkpoints.json").read_text())["points"]
interp = max(abs(eos.z(T, p, x) / z - 1) for T, p, x, z in pts)
pr = max(abs(eos.z(T, p, x, "pr") / z - 1) for T, p, x, z in pts if p <= 300)
print(f"Reference-table interpolation error (400 off-grid points): max {interp:.1e}")
print(f"Peng-Robinson deviation from reference, P <= 300 bar:      max {100 * pr:.1f} %")
print()
print("Z of air at 20 degC:", ", ".join(f"{p} bar {eos.z(293.15, p, 0.2095):.4f}"
                                        for p in (100, 200, 232, 300)))
for p in (200, 232, 300):
    r = cylinder.free_gas(p, 0.2095)
    i = cylinder.free_gas(p, 0.2095, model="ideal")
    print(f"Usable air in 12 L at {p} bar: real {r:.0f} L, ideal {i:.0f} L ({100 * (r / i - 1):+.1f} %)")
print()
for ft in (0.32, 0.36):
    r = blending.plan_partial_pressure(ft, 200)
    i = blending.plan_partial_pressure(ft, 200, model="ideal")
    t = blending.ideal_o2_pressure(ft, 200)
    print(f"EAN{100 * ft:.0f} to 200 bar from empty: stop O2 at {r.fill_add_to:.2f} bar (real), "
          f"{i.fill_add_to:.2f} (ideal, gauge-correct), {t:.2f} (textbook)")
print()
env, tt = Environment(), Environment.training_tables()
for pct in (32, 36):
    g = Nitrox.ean(pct)
    print(f"EAN{pct} MOD at 1.4 bar: {mod(g):.2f} m (sea water 1025), "
          f"{mod(g, env=Environment(water='en13319')):.2f} m (EN13319), {mod(g, env=tt):.2f} m (10 m/bar)")
g = Nitrox.ean(32)
print(f"EAN32 at 30 m: EAD exact {ead_exact(g, 30):.3f} m, classical {ead(g, 30):.3f} m")
st = TissueState.surface_equilibrium(env.surface_pressure)
for f, d in ((AIR.fo2, 30), (0.32, 30), (0.36, 25)):
    n1 = ndl_constant_depth(st, env.pressure(d), 1 - f, env.surface_pressure, 1.0)
    n2 = ndl_constant_depth(st, env.pressure(d), 1 - f, env.surface_pressure, 0.85)
    print(f"NDL {Nitrox(f)} {d} m: GF100 {n1:.1f} min, GF85 {n2:.1f} min (instantaneous descent)")
_ = math
print()
for ft in (0.32, 0.36):
    t = blending.ideal_o2_pressure(ft, 200)
    # follow the textbook gauge target with real gas: what mix results?
    n0 = eos.moles(1.01325, 12, 293.15, 0.2095)
    n1 = eos.moles(t + 1.01325, 12, 293.15, 1.0)  # first guess composition, then iterate
    x1 = 1.0
    for _ in range(50):
        nA = n1 - n0
        x1 = (n0 * 0.2095 + nA) / n1
        n1 = eos.moles(t + 1.01325, 12, 293.15, x1)
    f = blending.top_off(t, x1, 200)
    print(f"Following the textbook O2 target for EAN{100 * ft:.0f} yields {100 * f:.2f} % O2 "
          f"(MOD at 1.4 bar shrinks by {mod(Nitrox(ft)) - mod(Nitrox(f)):.2f} m)")
