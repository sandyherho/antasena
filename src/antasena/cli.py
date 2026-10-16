"""Command-line interface: ``antasena <command> [options]``.

Run ``antasena`` with no arguments (or ``antasena gui``) to open the desktop app.
Add ``--why`` to any calculation to print its derivation.
"""
from __future__ import annotations

import argparse
import math
import sys

from . import __version__, blending, cylinder, explain
from .environment import Environment
from .gas import Nitrox, best_mix, ead, ead_exact, mod
from .planner import Level, PlanError, Tank, plan_dive
from .uncertainty import mod_bounds, ndl_bounds

DISCLAIMER = ("antasena is a planning and education tool, not a dive computer. "
              "Verify every plan and dive within your training.")


def _pct(s: str) -> float:
    v = float(s)
    return v / 100.0 if v > 1.0 else v


def _env(a) -> Environment:
    return Environment(water=a.water, altitude_m=a.altitude)


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--water", default="salt", choices=["salt", "en13319", "fresh"])
    p.add_argument("--altitude", type=float, default=0.0, help="dive-site altitude, m")
    p.add_argument("--why", action="store_true", help="print the derivation")


def cmd_mod(a) -> None:
    g, env = Nitrox(a.fo2), _env(a)
    m = mod(g, a.po2, env)
    print(f"{g}: MOD at PO2 {a.po2:.2f} bar = {m:.1f} m")
    if a.analyzer:
        b = mod_bounds(a.fo2, (float(a.analyzer) / 100.0), a.po2, env)
        print(f"  with analyzer error +/-{100 * (float(a.analyzer) / 100.0):.1f} %: guaranteed MOD {b.lo:.1f} m "
              f"(range {b.lo:.1f} to {b.hi:.1f} m)")
    if a.why:
        print("\n" + explain.explain_mod(g, a.po2, env).to_text())


def cmd_bestmix(a) -> None:
    env = _env(a)
    g = best_mix(a.depth, a.po2, env)
    print(f"Best mix for {a.depth:g} m at PO2 {a.po2:.2f} bar: {g} "
          f"(PO2 {g.fo2 * env.pressure(a.depth):.3f} bar)")
    if a.why:
        print("\n" + explain.explain_best_mix(a.depth, a.po2, env).to_text())


def cmd_ead(a) -> None:
    g, env = Nitrox(a.fo2), _env(a)
    print(f"{g} at {a.depth:g} m: EAD {ead_exact(g, a.depth, env):.2f} m "
          f"(classical {ead(g, a.depth, env):.2f} m)")
    if a.why:
        print("\n" + explain.explain_ead(g, a.depth, env).to_text())


def cmd_ndl(a) -> None:
    g, env = Nitrox(a.fo2), _env(a)
    b = ndl_bounds(a.fo2, (float(a.analyzer) / 100.0) if a.analyzer else 0.0, a.depth,
                   a.gf_high / 100.0, env)
    nom = ndl_bounds(a.fo2, 0.0, a.depth, a.gf_high / 100.0, env).lo
    txt = "unlimited" if math.isinf(nom) else f"{nom:.1f} min"
    print(f"{g} at {a.depth:g} m, GF high {a.gf_high:g} %: NDL {txt}")
    if a.analyzer and math.isfinite(b.hi):
        print(f"  analyzer +/-{100 * (float(a.analyzer) / 100.0):.1f} %: NDL between {b.lo:.1f} and {b.hi:.1f} min")
    if a.why:
        print("\n" + explain.explain_ndl(g, a.depth, a.gf_high / 100.0, env).to_text())


def cmd_blend(a) -> None:
    for model in ("reference", "ideal"):
        p = blending.plan_partial_pressure(
            _pct(a.target), a.pressure, volume_l=a.volume, start_pressure=a.start,
            start_fo2=_pct(a.start_fo2), temperature_c=a.temp, model=model)
        tag = "real gas " if model == "reference" else "ideal gas"
        if p.feasible:
            print(f"[{tag}] add O2 to {p.fill_add_to:6.1f} bar, top with air to {a.pressure:g} bar"
                  f"   O2 used {p.add_free_liters:6.0f} L")
        else:
            print(f"[{tag}] {p.message}")
    if a.why:
        print("\n" + explain.explain_blend(_pct(a.target), a.pressure, volume_l=a.volume,
                                           start_pressure=a.start, start_fo2=_pct(a.start_fo2),
                                           temperature_c=a.temp).to_text())


def cmd_topoff(a) -> None:
    f = blending.top_off(a.start, _pct(a.start_fo2), a.pressure, volume_l=a.volume,
                         temperature_c=a.temp)
    fi = blending.top_off(a.start, _pct(a.start_fo2), a.pressure, volume_l=a.volume,
                          temperature_c=a.temp, model="ideal")
    print(f"After topping with air to {a.pressure:g} bar: {100 * f:.2f} % O2 "
          f"(ideal gas {100 * fi:.2f} %)")


def cmd_cylinder(a) -> None:
    fo2 = _pct(a.fo2)
    real = cylinder.free_gas(a.pressure, fo2, volume_l=a.volume, temperature_c=a.temp)
    ideal = cylinder.free_gas(a.pressure, fo2, volume_l=a.volume, temperature_c=a.temp, model="ideal")
    print(f"{a.volume:g} L at {a.pressure:g} bar, {a.temp:g} °C: {real:.0f} usable free liters "
          f"(ideal gas {ideal:.0f} L, {100 * (real / ideal - 1):+.1f} %)")
    if a.cool_to is not None:
        p2 = cylinder.settled_pressure(a.pressure, a.temp, a.cool_to, fo2, volume_l=a.volume)
        print(f"  at {a.cool_to:g} °C the gauge will read {p2:.1f} bar")
    if a.why:
        print("\n" + explain.explain_free_gas(a.pressure, fo2, a.volume, a.temp).to_text())


def _parse_levels(items: list[str]) -> list[Level]:
    out = []
    for it in items:
        try:
            d, t = it.split(":")
            out.append(Level(float(d), float(t)))
        except ValueError:
            raise SystemExit(f"bad level {it!r}; use DEPTH:MINUTES, e.g. 30:25") from None
    return out


def cmd_plan(a) -> None:
    env = _env(a)
    bottom = Nitrox(_pct(a.gas))
    deco = [Nitrox(_pct(x)) for x in (a.deco or [])]
    tanks = [Tank(bottom, a.volume, a.fill)]
    tanks += [Tank(g, a.deco_volume, a.fill) for g in deco]
    try:
        r = plan_dive(_parse_levels(a.levels), bottom, deco, gf_low=a.gf[0] / 100,
                      gf_high=a.gf[1] / 100, env=env, sac=a.sac, tanks=tanks,
                      safety_stop=not a.no_safety_stop, record_trace=False)
    except PlanError as e:
        raise SystemExit(f"plan rejected: {e}") from None
    print(f"Plan: {', '.join(a.levels)} on {bottom}; GF {a.gf[0]:g}/{a.gf[1]:g}")
    if r.ndl is not None:
        print(f"  NDL at depth: {'unlimited' if math.isinf(r.ndl) else f'{r.ndl:.1f} min'}")
    print(f"  {'Stop':>8} {'Time':>6} {'Run':>7}  Gas")
    for s in r.stops:
        print(f"  {s.depth:6.0f} m {s.minutes:5.0f}' {s.runtime_end:6.1f}'  {s.gas}")
    print(f"  Run time {r.runtime:.1f} min, TTS {r.tts:.1f} min, "
          f"CNS {100 * r.cns:.1f} %, OTU {r.otu:.0f}")
    for t in r.tank_report:
        if t["out_of_gas"]:
            print(f"  {t['gas']:>6}: {t['used_liters']:6.0f} L needed, only "
                  f"{t['available_liters']:.0f} L available: OUT OF GAS")
            continue
        print(f"  {t['gas']:>6}: {t['used_liters']:6.0f} L used, ends at {t['end_reference']:.0f} bar "
              f"(ideal-gas estimate {t['end_ideal']:.0f} bar)")
    for w in r.warnings:
        print("  ! " + w)
    if a.why:
        print("\n" + explain.explain_oxygen(r).to_text())


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="antasena", description="Rigorous nitrox calculations. "
                                 + DISCLAIMER)
    ap.add_argument("--version", action="version", version=f"antasena {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("gui", help="open the desktop app")

    p = sub.add_parser("mod", help="maximum operating depth")
    p.add_argument("fo2", type=_pct, help="O2 fraction or percent, e.g. 32")
    p.add_argument("--po2", type=float, default=1.4)
    p.add_argument("--analyzer", help="analyzer accuracy, percent points, e.g. 1")
    _common(p)
    p.set_defaults(func=cmd_mod)

    p = sub.add_parser("bestmix", help="richest nitrox for a depth")
    p.add_argument("depth", type=float)
    p.add_argument("--po2", type=float, default=1.4)
    _common(p)
    p.set_defaults(func=cmd_bestmix)

    p = sub.add_parser("ead", help="equivalent air depth")
    p.add_argument("fo2", type=_pct)
    p.add_argument("depth", type=float)
    _common(p)
    p.set_defaults(func=cmd_ead)

    p = sub.add_parser("ndl", help="no-decompression limit (Buhlmann ZH-L16C)")
    p.add_argument("fo2", type=_pct)
    p.add_argument("depth", type=float)
    p.add_argument("--gf-high", type=float, default=85.0)
    p.add_argument("--analyzer")
    _common(p)
    p.set_defaults(func=cmd_ndl)

    p = sub.add_parser("blend", help="partial-pressure blending, real vs ideal gas")
    p.add_argument("target", help="target O2 percent")
    p.add_argument("pressure", type=float, help="target gauge pressure, bar")
    p.add_argument("--start", type=float, default=0.0, help="current gauge pressure")
    p.add_argument("--start-fo2", default="20.95")
    p.add_argument("--volume", type=float, default=12.0)
    p.add_argument("--temp", type=float, default=20.0, help="settled temperature, °C")
    p.add_argument("--why", action="store_true")
    p.set_defaults(func=cmd_blend)

    p = sub.add_parser("topoff", help="mix after topping a partial fill with air")
    p.add_argument("start", type=float)
    p.add_argument("start_fo2")
    p.add_argument("pressure", type=float)
    p.add_argument("--volume", type=float, default=12.0)
    p.add_argument("--temp", type=float, default=20.0)
    p.set_defaults(func=cmd_topoff)

    p = sub.add_parser("cylinder", help="real gas content, hot-fill cooling")
    p.add_argument("pressure", type=float)
    p.add_argument("--fo2", default="20.95")
    p.add_argument("--volume", type=float, default=12.0)
    p.add_argument("--temp", type=float, default=20.0)
    p.add_argument("--cool-to", type=float)
    p.add_argument("--why", action="store_true")
    p.set_defaults(func=cmd_cylinder)

    p = sub.add_parser("plan", help="plan a dive")
    p.add_argument("levels", nargs="+", help="DEPTH:MINUTES, e.g. 30:25 18:10")
    p.add_argument("--gas", default="32")
    p.add_argument("--deco", nargs="*", help="deco gases, e.g. 50 100")
    p.add_argument("--gf", type=float, nargs=2, default=(30.0, 85.0), metavar=("LOW", "HIGH"))
    p.add_argument("--sac", type=float, default=20.0, help="L/min at the surface")
    p.add_argument("--volume", type=float, default=12.0)
    p.add_argument("--deco-volume", type=float, default=7.0)
    p.add_argument("--fill", type=float, default=200.0)
    p.add_argument("--no-safety-stop", action="store_true")
    _common(p)
    p.set_defaults(func=cmd_plan)
    return ap


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd in (None, "gui"):
        from .gui import launch
        return launch()
    a.func(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
