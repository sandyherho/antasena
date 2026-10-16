"""Step-by-step derivations with the user's numbers substituted.

Each ``explain_*`` function recomputes a result through the public API and
returns a :class:`Derivation`: the governing equation, every intermediate
value, the assumptions and the validity range. The final value of each
derivation is asserted equal to the library result in the test suite, so the
explanation can never drift from the computation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import blending, cylinder, eos
from .buhlmann import TissueState, ndl_constant_depth
from .constants import FN2_AIR, P_ATM, P_H2O_ALV, T0_C
from .environment import Environment
from .gas import Nitrox, best_mix, ead, ead_exact, mod
from .planner import PlanResult

__all__ = ["Derivation", "explain_mod", "explain_best_mix", "explain_ead",
           "explain_blend", "explain_ndl", "explain_oxygen", "explain_free_gas"]


@dataclass
class Derivation:
    title: str
    equation: str
    steps: list[tuple[str, str]] = field(default_factory=list)
    result: float = math.nan
    result_text: str = ""
    assumptions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, label: str, text: str) -> "Derivation":
        self.steps.append((label, text))
        return self

    def to_text(self) -> str:
        lines = [self.title, "=" * len(self.title), "", "Equation:", "  " + self.equation, ""]
        if self.steps:
            lines.append("Steps:")
            w = max(len(lbl) for lbl, _ in self.steps)
            lines += [f"  {lbl.ljust(w)}  {txt}" for lbl, txt in self.steps]
            lines.append("")
        lines.append("Result: " + self.result_text)
        if self.assumptions:
            lines += ["", "Assumptions:"] + [f"  - {a}" for a in self.assumptions]
        if self.notes:
            lines += ["", "Notes:"] + [f"  - {n}" for n in self.notes]
        return "\n".join(lines)


def _env_steps(d: Derivation, env: Environment) -> None:
    d.add("surface pressure", f"P_surf = {env.surface_pressure:.5f} bar"
          + (f"  (ISA, altitude {env.altitude_m:g} m)" if env.altitude_m else ""))
    d.add("hydrostatic gradient", f"rho g = {env.density:.1f} kg/m3 x {env.gravity:.5f} m/s2"
          f" = {env.bar_per_meter:.6f} bar/m")


def explain_mod(gas: Nitrox, po2_max: float = 1.4, env: Environment = Environment()) -> Derivation:
    m = mod(gas, po2_max, env)
    d = Derivation(f"Maximum operating depth of {gas}",
                   "MOD = (PO2_max / fO2 - P_surf) / (rho g)")
    _env_steps(d, env)
    p = po2_max / gas.fo2
    d.add("ambient pressure at limit", f"PO2_max / fO2 = {po2_max:.2f} / {gas.fo2:.4f} = {p:.5f} bar")
    d.add("depth", f"({p:.5f} - {env.surface_pressure:.5f}) / {env.bar_per_meter:.6f}"
          f" = {m:.3f} m")
    d.result, d.result_text = m, f"MOD = {m:.2f} m"
    d.assumptions = ["Dalton's law: PO2 = fO2 x P_amb (ideal mixing at the low pressures breathed).",
                     "Hydrostatic pressure with constant water density."]
    tt = mod(gas, po2_max, Environment.training_tables())
    d.notes.append(f"With the rounded table convention (1 bar, 10 m/bar) the MOD is {tt:.2f} m; "
                   f"the difference of {tt - m:+.2f} m comes from density and surface pressure.")
    return d


def explain_best_mix(depth: float, po2_max: float = 1.4, env: Environment = Environment()) -> Derivation:
    g = best_mix(depth, po2_max, env)
    p = env.pressure(depth)
    d = Derivation(f"Best nitrox for {depth:g} m", "fO2* = PO2_max / P(d), rounded down")
    _env_steps(d, env)
    d.add("ambient pressure", f"P(d) = {env.surface_pressure:.5f} + {env.bar_per_meter:.6f} x {depth:g}"
          f" = {p:.5f} bar")
    d.add("optimum", f"fO2* = {po2_max:.2f} / {p:.5f} = {po2_max / p:.5f}")
    d.add("rounded down", f"{100 * g.fo2:.0f} % (never up, so the PO2 limit holds)")
    d.result, d.result_text = g.fo2, f"{g}  (PO2 at depth {g.fo2 * p:.3f} bar)"
    d.notes.append("Maximizing fO2 minimizes the nitrogen load, hence maximizes the no-stop time, "
                   "subject to the oxygen limit: the optimum lies on the constraint boundary.")
    return d


def explain_ead(gas: Nitrox, depth: float, env: Environment = Environment()) -> Derivation:
    e1, e2 = ead(gas, depth, env), ead_exact(gas, depth, env)
    p = env.pressure(depth)
    d = Derivation(f"Equivalent air depth of {gas} at {depth:g} m",
                   "P_ead = (P(d) - pH2O) fN2 / fN2_air + pH2O   (alveolar form)")
    _env_steps(d, env)
    d.add("ambient pressure", f"P(d) = {p:.5f} bar")
    d.add("classical", f"P(d) fN2 / fN2_air = {p:.5f} x {gas.fn2:.4f} / {FN2_AIR:.4f}"
          f" -> EAD = {e1:.3f} m")
    d.add("alveolar (exact)", f"({p:.5f} - {P_H2O_ALV}) x {gas.fn2:.4f} / {FN2_AIR:.4f} + {P_H2O_ALV}"
          f" -> EAD = {e2:.3f} m")
    d.result, d.result_text = e2, f"EAD = {e2:.2f} m (classical {e1:.2f} m)"
    d.notes.append("Tissue models are driven by alveolar, not ambient, nitrogen pressure. Matching the "
                   "alveolar value makes the nitrox dive exactly equivalent to an air dive for every "
                   f"compartment. The classical EAD is {e2 - e1:.3f} m shallower than the exact one.")
    return d


def explain_blend(target_fo2: float, target_pressure: float, *, volume_l: float = 12.0,
                  start_pressure: float = 0.0, start_fo2: float = 0.2095,
                  temperature_c: float = 20.0) -> Derivation:
    real = blending.plan_partial_pressure(target_fo2, target_pressure, volume_l=volume_l,
                                          start_pressure=start_pressure, start_fo2=start_fo2,
                                          temperature_c=temperature_c)
    ideal = blending.plan_partial_pressure(target_fo2, target_pressure, volume_l=volume_l,
                                           start_pressure=start_pressure, start_fo2=start_fo2,
                                           temperature_c=temperature_c, model="ideal")
    d = Derivation(f"Partial-pressure blend to {100 * target_fo2:.1f} % at {target_pressure:g} bar",
                   "nA = [nf (xt - xB) - n0 (x0 - xB)] / (xA - xB),  n = P V / (Z R T)")
    T = temperature_c + T0_C
    P0, Pf = start_pressure + P_ATM, target_pressure + P_ATM
    z0 = eos.z(T, P0, start_fo2)
    zf = eos.z(T, Pf, target_fo2)
    d.add("absolute pressures", f"P0 = {P0:.3f} bar, Pf = {Pf:.3f} bar (gauge + {P_ATM})")
    d.add("compressibility", f"Z0 = {z0:.5f}, Zf = {zf:.5f} at {T:.2f} K (reference EOS)")
    d.add("moles", f"n0 = {real.n_start:.4f} mol, nf = {real.n_final:.4f} mol in {volume_l:g} L")
    if real.feasible:
        d.add("O2 to add", f"nA = {real.n_add:.4f} mol = {real.add_free_liters:.0f} free liters")
        d.add("air to add", f"nB = {real.n_top:.4f} mol = {real.top_free_liters:.0f} free liters")
        d.add("gauge target", f"stop O2 at {real.fill_add_to:.2f} bar (ideal gas: {ideal.fill_add_to:.2f} bar)")
        d.result, d.result_text = real.fill_add_to, real.message
    else:
        d.result_text = real.message
    d.assumptions = ["Isothermal fill: read gauges at the settled temperature.",
                     "Argon is lumped with nitrogen; the cylinder holds O2 + N2 only.",
                     "Gas A (O2) is added first, then the cylinder is topped with gas B (air)."]
    d.notes.append("The mole balance is exactly linear: the blend is a convex combination on the "
                   "composition simplex. Only the conversion between moles and gauge pressure "
                   "depends on the equation of state.")
    return d


def explain_ndl(gas: Nitrox, depth: float, gf_high: float = 1.0,
                env: Environment = Environment()) -> Derivation:
    st = TissueState.surface_equilibrium(env.surface_pressure)
    p = env.pressure(depth)
    ndl = ndl_constant_depth(st, p, gas.fn2, env.surface_pressure, gf_high)
    d = Derivation(f"No-decompression limit for {gas} at {depth:g} m (GF high {gf_high:.2f})",
                   "t_i = ln[(P_alv - P_0) / (P_alv - M_i)] / k_i,  NDL = min_i t_i")
    pa = (p - st.p_h2o) * gas.fn2
    d.add("alveolar N2", f"P_alv = ({p:.4f} - {st.p_h2o}) x {gas.fn2:.4f} = {pa:.4f} bar")
    d.add("initial tension", f"P_0 = {st.tensions[0]:.4f} bar (saturated at the surface)")
    lead, best = None, math.inf
    for i, c in enumerate(st.compartments):
        m = c.max_tension(env.surface_pressure, gf_high)
        if pa > m:
            t = math.log((pa - st.tensions[i]) / (pa - m)) / c.k
            if t < best:
                lead, best = i, t
    if lead is not None:
        c = st.compartments[lead]
        m = c.max_tension(env.surface_pressure, gf_high)
        d.add("controlling tissue", f"#{lead + 1} (half-time {c.half_time:g} min, a = {c.a}, b = {c.b})")
        d.add("surfacing limit", f"M = P_surf + GF (a + P_surf/b - P_surf) = {m:.4f} bar")
        d.add("time to limit", f"ln[({pa:.4f} - {st.tensions[lead]:.4f}) / ({pa:.4f} - {m:.4f})]"
              f" / {c.k:.5f} = {best:.2f} min")
    d.result = ndl
    d.result_text = "unlimited" if math.isinf(ndl) else f"NDL = {ndl:.1f} min"
    d.assumptions = ["Bühlmann ZH-L16C nitrogen coefficients, compartment 1b.",
                     "Instantaneous descent; time counts from arrival at depth.",
                     "Direct ascent; a safety stop is extra margin, not part of the limit."]
    return d


def explain_oxygen(plan: PlanResult) -> Derivation:
    d = Derivation("Oxygen exposure of the plan",
                   "CNS = sum ln(T_b/T_a)/(k s);  OTU = sum (3/11) dt/(p_b - p_a) [u_b^(11/6) - u_a^(11/6)]")
    for s in plan.segments:
        if s.cns > 0 or s.otu > 0:
            d.add(f"{s.kind} {s.depth_start:.0f}->{s.depth_end:.0f} m",
                  f"{s.minutes:5.2f} min on {s.gas}, PO2 {s.po2_start:.2f}->{s.po2_end:.2f} bar: "
                  f"CNS +{100 * s.cns:.2f} %, OTU +{s.otu:.1f}")
    d.result = plan.cns
    d.result_text = f"CNS {100 * plan.cns:.1f} %, OTU {plan.otu:.1f}"
    d.assumptions = ["NOAA single-exposure limits, linear in PO2 between table nodes.",
                     "No CNS accrual at PO2 <= 0.5 bar; 900 min limit just above 0.5 bar (Baker); "
                     "OTU threshold 0.5 bar."]
    return d


def explain_free_gas(pressure: float, fo2: float, volume_l: float = 12.0,
                     temperature_c: float = 20.0) -> Derivation:
    real = cylinder.free_gas(pressure, fo2, volume_l=volume_l, temperature_c=temperature_c)
    ideal = cylinder.free_gas(pressure, fo2, volume_l=volume_l, temperature_c=temperature_c,
                              model="ideal")
    T = temperature_c + T0_C
    zz = eos.z(T, pressure + P_ATM, fo2)
    d = Derivation(f"Usable gas in a {volume_l:g} L cylinder at {pressure:g} bar",
                   "G = [n(P) - n(P_atm)] R T / P_atm,  n = P V / (Z R T)")
    d.add("compressibility", f"Z({T:.2f} K, {pressure + P_ATM:.2f} bar, fO2 {fo2:.3f}) = {zz:.5f}")
    d.add("real gas", f"G = {real:.0f} L")
    d.add("ideal gas (P x V)", f"G = {ideal:.0f} L")
    d.result, d.result_text = real, f"{real:.0f} free liters ({real - ideal:+.0f} L vs ideal)"
    d.notes.append("Above about 150-200 bar Z exceeds 1 for air: each additional bar adds less gas "
                   "than the ideal estimate suggests.")
    return d
