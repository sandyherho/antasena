"""Dive planning: profile construction, decompression schedule, oxygen and gas budgets.

Every segment of a plan has constant gas and linear depth versus time, so
tissue tensions (Schreiner), CNS and OTU (closed-form integrals) and gas
consumption (mean ambient pressure) are all evaluated exactly per segment.

Decompression follows Buhlmann ZH-L16C with gradient factors (GF low/high):

1. At the start of the final ascent, if the ceiling under ``gf_high`` lies at
   or above the surface the dive is a no-decompression dive (the same
   criterion that defines the NDL) and the ascent is checked against
   ``gf_high``.
2. Otherwise the ceiling under ``gf_low``, rounded up to the stop grid, is
   the first stop. The gradient factor then varies
   linearly with ambient pressure from ``gf_low`` at the first stop to
   ``gf_high`` at the surface.
3. Before each move to the next shallower grid depth the move is simulated
   at the ascent rate. It is taken if the ceiling at the destination's
   gradient factor lies at or above the destination; otherwise the diver
   waits in whole minutes.
4. On arrival at a grid depth the richest available deco gas whose PO2 does
   not exceed ``deco_po2_max`` is selected.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import cylinder as cyl
from .buhlmann import TissueState, ndl_constant_depth
from .constants import P_ATM, T0_C
from .environment import Environment
from .gas import AIR, Nitrox
from .toxicity import cns_after_surface_interval, cns_segment, otu_segment

__all__ = ["Level", "Tank", "Segment", "Stop", "DiverState", "PlanResult",
           "plan_dive", "surface_interval", "PlanError"]

_EPS = 1e-9


class PlanError(ValueError):
    """The requested plan violates a hard limit of the model."""


@dataclass(frozen=True)
class Level:
    """Stay at ``depth`` (m) for ``minutes``, excluding transit to it."""

    depth: float
    minutes: float


@dataclass(frozen=True)
class Tank:
    """A cylinder carrying one gas, with its fill (bar gauge)."""

    gas: Nitrox
    volume_l: float = 12.0
    pressure: float = 200.0
    reserve: float = 50.0


@dataclass
class Segment:
    kind: str
    depth_start: float
    depth_end: float
    runtime_start: float
    minutes: float
    gas: Nitrox
    p_start: float = 0.0
    p_end: float = 0.0
    po2_start: float = 0.0
    po2_end: float = 0.0
    cns: float = 0.0
    otu: float = 0.0
    gas_liters: float = 0.0

    @property
    def runtime_end(self) -> float:
        return self.runtime_start + self.minutes


@dataclass
class Stop:
    depth: float
    minutes: float
    gas: Nitrox
    runtime_end: float


@dataclass
class DiverState:
    """What carries over between dives: tissues and oxygen clocks."""

    tissues: TissueState
    cns: float = 0.0
    otu: float = 0.0

    @classmethod
    def fresh(cls, env: Environment) -> "DiverState":
        return cls(TissueState.surface_equilibrium(env.surface_pressure))

    def copy(self) -> "DiverState":
        return DiverState(self.tissues.copy(), self.cns, self.otu)


@dataclass
class PlanResult:
    segments: list[Segment]
    stops: list[Stop]
    runtime: float
    cns: float
    otu: float
    gas_used: dict[str, float]
    tank_report: list[dict]
    ndl: float | None
    deco: bool
    warnings: list[str]
    final_state: DiverState
    first_stop: float | None
    trace: list[dict] = field(default_factory=list)
    gf_low: float = 1.0
    gf_high: float = 1.0

    @property
    def max_depth(self) -> float:
        return max(max(s.depth_start, s.depth_end) for s in self.segments)

    @property
    def tts(self) -> float:
        """Time to surface from the end of the last bottom level, min."""
        t_end = max((s.runtime_end for s in self.segments if s.kind == "level"), default=0.0)
        return self.runtime - t_end


def _grid_up(depth: float, inc: float) -> float:
    return math.ceil(depth / inc - _EPS) * inc


class _Runner:
    """Applies segments to a diver state and records everything."""

    def __init__(self, env: Environment, state: DiverState, sac: float, sac_deco: float,
                 record_trace: bool):
        self.env = env
        self.state = state
        self.sac = sac
        self.sac_deco = sac_deco
        self.segments: list[Segment] = []
        self.runtime = 0.0
        self.gas_used: dict[str, float] = {}
        self.record = record_trace
        self.trace: list[dict] = []

    def apply(self, kind: str, d0: float, d1: float, minutes: float, gas: Nitrox,
              gf_of_p=None) -> Segment:
        env = self.env
        p0, p1 = env.pressure(d0), env.pressure(d1)
        seg = Segment(kind, d0, d1, self.runtime, minutes, gas, p0, p1,
                      gas.fo2 * p0, gas.fo2 * p1)
        if self.record and minutes > 0:
            n = max(2, min(60, int(minutes * 4) + 1))
            for j in range(n):
                t = minutes * j / (n - 1)
                if j == 0 and self.trace and abs(self.trace[-1]["t"] - self.runtime) < 1e-12:
                    continue
                ts = self.state.tissues.copy()
                ts.expose(p0, p0 + (p1 - p0) * t / minutes, t, gas.fn2)
                pa = p0 + (p1 - p0) * t / minutes
                gf = gf_of_p(pa) if gf_of_p else 1.0
                ceil_p = ts.ceiling(gf)
                self.trace.append({"t": self.runtime + t, "depth": env.depth(pa),
                                   "ceiling": max(0.0, env.depth(ceil_p)),
                                   "gf": gf, "tensions": ts.tensions,
                                   "gf_now": ts.gf_now(pa)})
        self.state.tissues.expose(p0, p1, minutes, gas.fn2)
        seg.cns = cns_segment(seg.po2_start, seg.po2_end, minutes)
        seg.otu = otu_segment(seg.po2_start, seg.po2_end, minutes)
        self.state.cns += seg.cns
        self.state.otu += seg.otu
        rate = self.sac_deco if kind in ("stop", "switch") else self.sac
        seg.gas_liters = rate * 0.5 * (p0 + p1) / P_ATM * minutes
        self.gas_used[gas.name] = self.gas_used.get(gas.name, 0.0) + seg.gas_liters
        self.segments.append(seg)
        self.runtime += minutes
        return seg


def surface_interval(state: DiverState, minutes: float, env: Environment = Environment()) -> DiverState:
    """Return the state after ``minutes`` breathing air at the surface."""
    out = state.copy()
    p = env.surface_pressure
    out.tissues.expose(p, p, minutes, AIR.fn2)
    out.cns = cns_after_surface_interval(state.cns, minutes)
    return out


def plan_dive(levels: list[Level] | list[tuple[float, float]], bottom_gas: Nitrox = AIR,
              deco_gases: list[Nitrox] | tuple = (), *, gf_low: float = 0.3,
              gf_high: float = 0.85, env: Environment = Environment(),
              descent_rate: float = 18.0, ascent_rate: float = 9.0,
              stop_increment: float = 3.0, last_stop: float = 3.0,
              po2_max: float = 1.4, deco_po2_max: float = 1.6,
              switch_minutes: float = 1.0, safety_stop: bool = True,
              safety_stop_depth: float = 5.0, safety_stop_minutes: float = 3.0,
              sac: float = 20.0, sac_deco: float | None = None,
              tanks: list[Tank] | tuple = (), water_temperature_c: float = 20.0,
              initial: DiverState | None = None, record_trace: bool = True,
              max_stop_minutes: int = 2000) -> PlanResult:
    """Plan a single dive on nitrox with optional decompression gases.

    ``levels`` are visited in order; transit between them uses the descent
    or ascent rate. ``gf_low`` and ``gf_high`` are fractions (0.3, 0.85).
    """
    levels = [lv if isinstance(lv, Level) else Level(*lv) for lv in levels]
    if not levels:
        raise PlanError("at least one level is required")
    if not (0 < gf_low <= gf_high <= 1.5):
        raise PlanError("require 0 < gf_low <= gf_high")
    if descent_rate <= 0 or ascent_rate <= 0 or stop_increment <= 0:
        raise PlanError("rates and stop increment must be positive")
    if last_stop < stop_increment - _EPS and last_stop != 0:
        raise PlanError("last stop must be at least one stop increment")
    for lv in levels:
        if lv.depth < 0 or lv.minutes < 0:
            raise PlanError("depths and times must be non-negative")
    warnings: list[str] = []
    dmax = max(lv.depth for lv in levels)
    po2_bottom = bottom_gas.fo2 * env.pressure(dmax)
    if po2_bottom > 1.6 + 1e-9:
        raise PlanError(f"{bottom_gas} reaches PO2 {po2_bottom:.2f} bar at {dmax:g} m, "
                        "beyond the 1.6 bar limit of the oxygen-toxicity model")
    if po2_bottom > po2_max + 1e-9:
        warnings.append(f"{bottom_gas} exceeds the working PO2 of {po2_max:.2f} bar at "
                        f"{dmax:g} m (PO2 {po2_bottom:.2f} bar).")
    state = (initial or DiverState.fresh(env)).copy()
    run = _Runner(env, state, sac, sac if sac_deco is None else sac_deco, record_trace)

    # ---- descent and levels -------------------------------------------------
    def gf_bottom(_p: float) -> float:
        return gf_low

    depth = 0.0
    for lv in levels:
        if lv.depth > depth:
            run.apply("descent", depth, lv.depth, (lv.depth - depth) / descent_rate, bottom_gas,
                      gf_bottom)
        elif lv.depth < depth:
            run.apply("transit", depth, lv.depth, (depth - lv.depth) / ascent_rate, bottom_gas,
                      gf_bottom)
        depth = lv.depth
        if lv.minutes > 0:
            run.apply("level", depth, depth, lv.minutes, bottom_gas, gf_bottom)

    p_surf = env.surface_pressure
    ndl = None
    if len(levels) == 1:
        # NDL from the start of the level (descent included), gf_high at surface.
        pre = (initial or DiverState.fresh(env)).copy()
        if levels[0].depth > 0:
            pre.tissues.expose(p_surf, env.pressure(levels[0].depth),
                               levels[0].depth / descent_rate, bottom_gas.fn2)
        ndl = ndl_constant_depth(pre.tissues, env.pressure(levels[0].depth),
                                 bottom_gas.fn2, p_surf, gf_high)

    # ---- ascent -------------------------------------------------------------
    stops: list[Stop] = []
    gases = sorted({bottom_gas, *deco_gases}, key=lambda g: g.fo2)
    current = bottom_gas
    # A dive is a decompression dive iff a direct ascent would violate GF high,
    # the same criterion that defines the NDL. GF low then places the first stop.
    ceil_low = state.tissues.ceiling(gf_low)
    deco = state.tissues.ceiling(gf_high) > p_surf + _EPS
    first_stop = None
    if deco:
        first_stop = max(_grid_up(env.depth(ceil_low), stop_increment), last_stop)
        first_stop = min(first_stop, _grid_up(depth, stop_increment))
    p_first = env.pressure(first_stop) if first_stop is not None else None
    # Ceiling shown during the bottom phase: the GF that governs the ascent start.
    gf_shown = gf_low if deco else gf_high
    for pt in run.trace:
        ts = TissueState(list(pt["tensions"]), state.tissues.compartments, state.tissues.p_h2o)
        pt["gf"] = gf_shown
        pt["ceiling"] = max(0.0, env.depth(ts.ceiling(gf_shown)))

    def gf_at(p: float) -> float:
        if p_first is None or p_first <= p_surf + _EPS:
            return gf_high
        if p >= p_first:
            return gf_low
        return gf_high + (gf_low - gf_high) * (p - p_surf) / (p_first - p_surf)

    def next_depth(d: float) -> float:
        if d <= last_stop + _EPS:
            return 0.0
        nd = _grid_up(d, stop_increment) - stop_increment
        return nd if nd >= last_stop - _EPS else last_stop

    def can_ascend(d: float, nd: float, gas: Nitrox) -> bool:
        trial = state.tissues.copy()
        trial.expose(env.pressure(d), env.pressure(nd), (d - nd) / ascent_rate, gas.fn2)
        pn = env.pressure(nd)
        return trial.ceiling(gf_at(pn)) <= pn + 1e-9

    def best_gas(d: float) -> Nitrox:
        ok = [g for g in gases if g.fo2 * env.pressure(d) <= deco_po2_max + 1e-9]
        return max(ok, key=lambda g: g.fo2) if ok else current

    mandatory = False  # becomes True once a decompression wait is actually required
    while depth > _EPS:
        nd = next_depth(depth)
        if not mandatory and safety_stop and depth > safety_stop_depth + _EPS \
                and nd < safety_stop_depth:
            nd = safety_stop_depth
        if can_ascend(depth, nd, current):
            run.apply("ascent", depth, nd, (depth - nd) / ascent_rate, current, gf_at)
            depth = nd
            if depth <= _EPS:
                break
            g = best_gas(depth)
            if g != current and deco:
                current = g
                if switch_minutes > 0:
                    run.apply("switch", depth, depth, switch_minutes, current, gf_at)
                    stops.append(Stop(depth, switch_minutes, current, run.runtime))
            if not mandatory and safety_stop and abs(depth - safety_stop_depth) < _EPS:
                run.apply("safety", depth, depth, safety_stop_minutes, current, gf_at)
                stops.append(Stop(depth, safety_stop_minutes, current, run.runtime))
            continue
        # must wait here
        mandatory = True
        if not deco:
            deco = True
            warnings.append("No-decompression ascent not possible within GF high; "
                            "decompression stops were added.")
            if p_first is None:
                first_stop = depth
                p_first = env.pressure(depth)
        waited = 0
        while not can_ascend(depth, nd, current):
            run.apply("stop", depth, depth, 1.0, current, gf_at)
            waited += 1
            if waited > max_stop_minutes:
                raise PlanError("decompression did not converge (stop exceeds "
                                f"{max_stop_minutes} min); check the plan")
        if stops and stops[-1].depth == depth and stops[-1].gas == current:
            stops[-1].minutes += waited
            stops[-1].runtime_end = run.runtime
        else:
            stops.append(Stop(depth, waited, current, run.runtime))

    if deco and not mandatory:
        warnings.append("Bottom time exceeds the no-stop limit for an instantaneous ascent, but "
                        "off-gassing during the ascent clears it: no mandatory stop. Treat this "
                        "dive as at the limit.")
    deco = mandatory

    # ---- budgets ------------------------------------------------------------
    if state.cns > 1.0:
        warnings.append(f"CNS clock {100 * state.cns:.0f} % exceeds 100 %.")
    elif state.cns > 0.8:
        warnings.append(f"CNS clock {100 * state.cns:.0f} % is above 80 %.")
    if state.otu > 300:
        warnings.append(f"Pulmonary dose {state.otu:.0f} OTU exceeds a single-day 300 OTU guideline.")

    tank_report = []
    for tk in tanks:
        used = run.gas_used.get(tk.gas.name, 0.0)
        rep = {"gas": tk.gas.name, "volume_l": tk.volume_l, "start": tk.pressure,
               "used_liters": used}
        for model in ("ideal", "reference"):
            try:
                rep[f"end_{model}"] = cyl.pressure_after_use(
                    tk.pressure, used, tk.gas.fo2, volume_l=tk.volume_l,
                    temperature_c=water_temperature_c, model=model)
            except ValueError:
                rep[f"end_{model}"] = float("nan")
        rep["available_liters"] = cyl.free_gas(tk.pressure, tk.gas.fo2, volume_l=tk.volume_l,
                                               temperature_c=water_temperature_c)
        rep["out_of_gas"] = used > rep["available_liters"]
        rep["below_reserve"] = rep["out_of_gas"] or rep["end_reference"] < tk.reserve
        if rep["out_of_gas"]:
            rep["end_reference"] = float("nan")
            rep["end_ideal"] = float("nan")
            warnings.append(f"{tk.gas.name}: plan needs {used:.0f} L but the cylinder holds only "
                            f"{rep['available_liters']:.0f} L of usable gas (OUT OF GAS).")
        elif rep["below_reserve"]:
            warnings.append(f"{tk.gas.name} cylinder ends at {rep['end_reference']:.0f} bar, "
                            f"below the {tk.reserve:.0f} bar reserve.")
        tank_report.append(rep)
    for g in run.gas_used:
        if tanks and g not in {tk.gas.name for tk in tanks}:
            warnings.append(f"No cylinder assigned for {g}.")

    if run.trace:
        p = env.surface_pressure
        run.trace.append({"t": run.runtime, "depth": 0.0,
                          "ceiling": max(0.0, env.depth(state.tissues.ceiling(gf_high))),
                          "gf": gf_high, "tensions": list(state.tissues.tensions),
                          "gf_now": state.tissues.gf_now(p)})
    _ = T0_C  # temperature only enters through the cylinder model
    return PlanResult(run.segments, stops, run.runtime, state.cns, state.otu,
                      dict(run.gas_used), tank_report, ndl, deco, warnings, state,
                      first_stop, run.trace, gf_low, gf_high)
