"""antasena desktop application (Tkinter, standard library only)."""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from .. import __version__, blending, cylinder, eos, explain
from ..buhlmann import TissueState, ndl_constant_depth
from ..constants import FO2_AIR, P_ATM, T0_C
from ..environment import Environment
from ..gas import Nitrox, best_mix, ead, ead_exact, mod
from ..planner import Level, PlanError, PlanResult, Tank, plan_dive
from ..uncertainty import mod_bounds, ndl_bounds
from ..units import Units
from . import icon, theme
from .plot import Plot
from .theme import C, SERIES

DISCLAIMER = ("Planning and education only. antasena is not a dive computer. "
              "Analyze your gas, follow your training, and verify every plan.")


class Field:
    """A labeled numeric entry that stores its value in display units."""

    def __init__(self, app: "App", parent, label: str, value: float, kind: str = "none",
                 width: int = 9, row: int = 0, col: int = 0, unit: str = ""):
        self.app, self.kind, self.fixed_unit = app, kind, unit
        self.var = tk.StringVar(value=self._fmt(value))
        self._cache: tuple[str, float] | None = None  # (shown text, exact metric value)
        ttk.Label(parent, text=label, style="Field.TLabel").grid(row=row, column=col, sticky="w",
                                                                 padx=(0, 8), pady=2)
        self.entry = ttk.Entry(parent, textvariable=self.var, width=width, justify="right")
        self.entry.grid(row=row, column=col + 1, sticky="ew", pady=2)
        self.unit_lbl = ttk.Label(parent, text=self.unit_text(), style="Muted.TLabel", width=9)
        self.unit_lbl.grid(row=row, column=col + 2, sticky="w", padx=(4, 0))
        app.fields.append(self)

    @staticmethod
    def _fmt(v: float) -> str:
        return f"{v:.6g}" if isinstance(v, float) else str(v)

    def unit_text(self) -> str:
        u = self.app.units
        return {"depth": u.depth_unit, "pressure": u.pressure_unit, "volume": u.volume_unit,
                "temp": u.temp_unit, "rate": f"{u.depth_unit}/min",
                "sac": f"{u.volume_unit}/min"}.get(self.kind, self.fixed_unit)

    def _to_metric(self, v: float, u: Units) -> float:
        return {"depth": u.depth_in, "rate": u.depth_in, "pressure": u.pressure_in,
                "volume": u.volume_in, "sac": u.volume_in, "temp": u.temp_in}.get(
                    self.kind, lambda x: x)(v)

    def _from_metric(self, v: float, u: Units) -> float:
        return {"depth": u.depth_out, "rate": u.depth_out, "pressure": u.pressure_out,
                "volume": u.volume_out, "sac": u.volume_out, "temp": u.temp_out}.get(
                    self.kind, lambda x: x)(v)

    def raw(self) -> float:
        s = self.var.get().strip().replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            raise ValueError(f"'{s}' is not a number") from None
        if not math.isfinite(v):
            raise ValueError("value must be finite")
        return v

    def get(self) -> float:
        """Value in metric units (exact if the text is unchanged since a unit toggle)."""
        if self._cache and self._cache[0] == self.var.get():
            return self._cache[1]
        return self._to_metric(self.raw(), self.app.units)

    def set(self, metric_value: float) -> None:
        self.var.set(f"{round(self._from_metric(metric_value, self.app.units), 4):g}")

    def _decimals(self, u: Units) -> int:
        """Display precision after a unit switch (the exact value is kept internally)."""
        if self.kind == "pressure":
            return 0 if u.imperial else 1
        if self.kind == "volume":
            return 1 if u.imperial else 0
        if self.kind == "sac":
            return 2 if u.imperial else 1
        if self.kind in ("depth", "rate", "temp"):
            return 1
        return 2

    def convert(self, old: Units, new: Units) -> None:
        self.unit_lbl.configure(text=self.unit_text())
        try:
            v = self._cache[1] if self._cache and self._cache[0] == self.var.get() \
                else self._to_metric(self.raw(), old)
        except ValueError:
            return
        txt = f"{round(self._from_metric(v, new), self._decimals(new)):g}"
        self.var.set(txt)
        self._cache = (txt, v)


class Tile:
    """A result card: caption, big number, detail line and a Why? button."""

    def __init__(self, parent, caption: str, why=None):
        self.frame = ttk.Frame(parent, style="Card.TFrame", padding=(14, 10))
        top = ttk.Frame(self.frame, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=caption.upper(), style="Field.TLabel").pack(side="left")
        if why:
            ttk.Button(top, text="Why?", style="Why.TButton", command=why).pack(side="right")
        self.value = ttk.Label(self.frame, text="–", style="Big.TLabel")
        self.value.pack(anchor="w", pady=(2, 0))
        self.detail = ttk.Label(self.frame, text="", style="Muted.TLabel", wraplength=230,
                                justify="left")
        self.detail.pack(anchor="w")

    def set(self, value: str, detail: str = "", color: str | None = None) -> None:
        self.value.configure(text=value, foreground=color or C["deep"])
        self.detail.configure(text=detail)


def card(parent, title: str = "", padding=(14, 10)) -> ttk.Frame:
    f = ttk.Frame(parent, style="Card.TFrame", padding=padding)
    if title:
        ttk.Label(f, text=title, style="H2.TLabel").grid(row=0, column=0, columnspan=6,
                                                         sticky="w", pady=(0, 8))
    return f


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"antasena {__version__} · nitrox, done exactly")
        self.geometry("1280x820")
        self.minsize(1040, 700)
        self.fonts = theme.apply(self)
        self._icons = {}
        try:  # PNG photo images need Tk 8.6+, which every supported Python ships
            self._icons["window"] = tk.PhotoImage(data=icon.ICON_64)
            self._icons["header"] = tk.PhotoImage(data=icon.HEADER_44)
            self.iconphoto(True, self._icons["window"])
        except tk.TclError:
            self._icons.clear()
        self.units = Units("metric")
        self.fields: list[Field] = []
        self.last_plan: PlanResult | None = None
        self._build_header()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(10, 0))
        self._build_gas_tab()
        self._build_blend_tab()
        self._build_plan_tab()
        self._build_learn_tab()
        self._build_status()
        self.bind_all("<Return>", lambda e: self.recompute())
        self._startup = self.after(50, self.recompute_all)

    def destroy(self):
        try:
            self.after_cancel(self._startup)
        except (tk.TclError, AttributeError):
            pass
        super().destroy()

    # ------------------------------------------------------------------ chrome
    def _build_header(self):
        h = ttk.Frame(self, style="Header.TFrame", padding=(18, 12))
        h.pack(fill="x")
        if "header" in self._icons:
            ttk.Label(h, image=self._icons["header"], style="HeaderTitle.TLabel").pack(
                side="left", padx=(0, 12))
        left = ttk.Frame(h, style="Header.TFrame")
        left.pack(side="left")
        ttk.Label(left, text="antasena", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(left, text="Nitrox physics with every number derived  ·  v" + __version__,
                  style="HeaderSub.TLabel").pack(anchor="w")
        right = ttk.Frame(h, style="Header.TFrame")
        right.pack(side="right")
        ttk.Label(right, text="Water", style="HeaderSub.TLabel").grid(row=0, column=0, padx=(0, 4))
        self.water = tk.StringVar(value="salt")
        cb = ttk.Combobox(right, textvariable=self.water, width=10, state="readonly",
                          values=["salt", "en13319", "fresh"])
        cb.grid(row=0, column=1, padx=(0, 14))
        cb.bind("<<ComboboxSelected>>", lambda e: self.recompute_all())
        ttk.Label(right, text="Altitude (m)", style="HeaderSub.TLabel").grid(row=0, column=2,
                                                                           padx=(0, 4))
        self.altitude = tk.StringVar(value="0")
        e = ttk.Entry(right, textvariable=self.altitude, width=7, justify="right")
        e.grid(row=0, column=3, padx=(0, 14))
        e.bind("<FocusOut>", lambda ev: self.recompute_all())
        self.unit_var = tk.StringVar(value="metric")
        for i, (txt, val) in enumerate((("Metric", "metric"), ("Imperial", "imperial"))):
            ttk.Radiobutton(right, text=txt, value=val, variable=self.unit_var,
                            style="Header.TRadiobutton",
                            command=self._units_changed).grid(row=0, column=4 + i, padx=2)

    def _build_status(self):
        s = ttk.Frame(self, padding=(14, 6))
        s.configure(style="TFrame")
        s.pack(fill="x", side="bottom")
        self.status = ttk.Label(s, text=DISCLAIMER, style="Status.TLabel", anchor="w",
                                padding=(10, 5))
        self.status.pack(fill="x")

    def say(self, msg: str, error: bool = False) -> None:
        self.status.configure(text=msg, foreground=C["danger"] if error else C["muted"])

    def env(self) -> Environment:
        try:
            alt = float(self.altitude.get() or 0)
        except ValueError:
            raise ValueError("altitude must be a number") from None
        return Environment(water=self.water.get(), altitude_m=alt)

    def _units_changed(self):
        old, new = self.units, Units(self.unit_var.get())
        if old.system == new.system:
            return
        self.units = new
        for f in self.fields:
            f.convert(old, new)
        self._refresh_levels_display(old)
        self.recompute_all()

    def why(self, builder):
        def show():
            try:
                d = builder()
            except Exception as exc:  # noqa: BLE001
                self.say(f"Cannot explain: {exc}", error=True)
                return
            self.show_text(d.title, d.to_text())
        return show

    def show_text(self, title: str, text: str):
        w = tk.Toplevel(self)
        w.title(title)
        w.configure(bg=C["card"])
        w.geometry("760x560")
        t = tk.Text(w, wrap="word", font=self.fonts.code, bg=C["card"], fg=C["ink"],
                    relief="flat", padx=18, pady=14)
        t.insert("1.0", text)
        t.configure(state="disabled")
        t.pack(fill="both", expand=True)
        b = ttk.Frame(w, style="Card.TFrame", padding=10)
        b.pack(fill="x")

        def copy():
            self.clipboard_clear()
            self.clipboard_append(text)
            self.say("Derivation copied to the clipboard.")
        ttk.Button(b, text="Copy", command=copy).pack(side="right", padx=4)
        ttk.Button(b, text="Close", command=w.destroy).pack(side="right")
        return w

    def recompute(self):
        tab = self.nb.index(self.nb.select())
        [self.compute_gas, self.compute_blend, self.compute_plan, self.show_topic][tab]()

    def recompute_all(self):
        self.compute_gas()
        self.compute_blend()
        self.compute_plan()
        self.show_topic()

    def _guard(self, fn):
        try:
            fn()
            return True
        except (ValueError, PlanError, ZeroDivisionError) as exc:
            self.say(str(exc), error=True)
            return False

    # -------------------------------------------------------------- gas tab
    def _build_gas_tab(self):
        tab = ttk.Frame(self.nb, padding=12)
        self.nb.add(tab, text="  Gas & limits  ")
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        side = ttk.Frame(tab)
        side.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        inp = card(side, "Your gas")
        inp.pack(fill="x")
        self.g_fo2 = Field(self, inp, "Oxygen", 32.0, unit="%", row=1)
        self.g_dfo2 = Field(self, inp, "Analyzer ±", 1.0, unit="% pts", row=2)
        self.g_po2 = Field(self, inp, "Working PO2", 1.4, unit="bar", row=3)
        self.g_po2c = Field(self, inp, "Contingency PO2", 1.6, unit="bar", row=4)
        self.g_depth = Field(self, inp, "Planned depth", 30.0, kind="depth", row=5)
        self.g_gfh = Field(self, inp, "GF high", 85.0, unit="%", row=6)
        ttk.Button(inp, text="Calculate", style="Accent.TButton",
                   command=self.compute_gas).grid(row=7, column=0, columnspan=3, sticky="ew",
                                                  pady=(10, 0))
        note = card(side, "How to read this", padding=(16, 10))
        note.pack(fill="x", pady=(12, 0))
        ttk.Label(note, style="Muted.TLabel", wraplength=270, justify="left", text=(
            "Every result follows from Dalton's law, P_O2 = f_O2 × P(depth), and an exact "
            "solution of the Bühlmann tissue equations. The guaranteed values assume the "
            "true oxygen fraction is anywhere inside the analyzer tolerance. "
            "Press Why? on any card for the full derivation with your numbers."
        )).grid(row=1, column=0, sticky="w")

        main = ttk.Frame(tab)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        tiles = ttk.Frame(main)
        tiles.grid(row=0, column=0, sticky="ew")
        for i in range(3):
            tiles.columnconfigure(i, weight=1, uniform="t")
        E = self.env
        self.t_mod = Tile(tiles, "Maximum operating depth", self.why(
            lambda: explain.explain_mod(self._gas(), self.g_po2.get(), E())))
        self.t_gmod = Tile(tiles, "Guaranteed MOD", self.why(lambda: self._explain_gmod()))
        self.t_best = Tile(tiles, "Best mix for planned depth", self.why(
            lambda: explain.explain_best_mix(self.g_depth.get(), self.g_po2.get(), E())))
        self.t_ead = Tile(tiles, "Equivalent air depth", self.why(
            lambda: explain.explain_ead(self._gas(), self.g_depth.get(), E())))
        self.t_ndl = Tile(tiles, "No-stop time at depth", self.why(
            lambda: explain.explain_ndl(self._gas(), self.g_depth.get(),
                                        self.g_gfh.get() / 100, E())))
        self.t_po2 = Tile(tiles, "PO2 at planned depth", None)
        for i, t in enumerate((self.t_mod, self.t_gmod, self.t_best, self.t_ead, self.t_ndl,
                               self.t_po2)):
            t.frame.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0 if i % 3 == 0 else 10, 0),
                         pady=(0, 10))
        pc = card(main, padding=(8, 8))
        pc.grid(row=1, column=0, sticky="nsew")
        pc.columnconfigure(0, weight=1)
        pc.rowconfigure(0, weight=1)
        self.plot_window = Plot(pc, title="Operating window", xlabel="Oxygen fraction (%)",
                             invert_y=True, fonts=self.fonts, height=300)
        self.plot_window.grid(row=0, column=0, sticky="nsew")

    def _gas(self) -> Nitrox:
        f = self.g_fo2.get() / 100.0
        if not 0.05 <= f <= 1.0:
            raise ValueError("oxygen must be between 5 and 100 %")
        return Nitrox(f)

    def _explain_gmod(self):
        g, df, po2 = self._gas(), self.g_dfo2.get() / 100, self.g_po2.get()
        d = explain.explain_mod(Nitrox(min(1.0, g.fo2 + df)), po2, self.env())
        d.title = f"Guaranteed MOD of {g} with analyzer ±{100 * df:.1f} % points"
        d.notes.insert(0, f"MOD decreases as fO2 increases, so the shallowest MOD over the "
                          f"tolerance band is attained at fO2 = {g.fo2:.4f} + {df:.4f}.")
        return d

    def compute_gas(self):
        if self._guard(self._compute_gas):
            self.say(DISCLAIMER)

    def _compute_gas(self):
        env, u = self.env(), self.units
        g, df = self._gas(), self.g_dfo2.get() / 100.0
        po2, po2c = self.g_po2.get(), self.g_po2c.get()
        depth, gfh = self.g_depth.get(), self.g_gfh.get() / 100.0
        if depth < 0:
            raise ValueError("depth must be non-negative")
        du = u.depth_unit
        m = mod(g, po2, env)
        mc = mod(g, po2c, env)
        b = mod_bounds(g.fo2, df, po2, env)
        self.t_mod.set(f"{u.depth_out(m):.1f} {du}",
                       f"at PO2 {po2:.2f} bar · contingency {u.depth_out(mc):.1f} {du} at {po2c:.2f}")
        self.t_gmod.set(f"{u.depth_out(b.lo):.1f} {du}",
                        f"true fO2 anywhere in {100 * (g.fo2 - df):.1f}–{100 * (g.fo2 + df):.1f} %",
                        C["ok"] if b.lo >= depth else C["danger"])
        bm = best_mix(depth, po2, env)
        self.t_best.set(f"{bm}", f"PO2 {bm.fo2 * env.pressure(depth):.2f} bar at "
                        f"{u.depth_out(depth):.0f} {du}")
        e1, e2 = ead_exact(g, depth, env), ead(g, depth, env)
        self.t_ead.set(f"{u.depth_out(e1):.1f} {du}",
                       f"alveolar-exact · classical {u.depth_out(e2):.1f} {du}")
        nb = ndl_bounds(g.fo2, df, depth, gfh, env)
        nom = ndl_bounds(g.fo2, 0.0, depth, gfh, env).lo
        if math.isinf(nom):
            self.t_ndl.set("unlimited", "no compartment reaches its surfacing limit")
        else:
            self.t_ndl.set(f"{nom:.0f} min", f"from arrival at depth · guaranteed {nb.lo:.0f} min "
                           f"with analyzer error · GF high {100 * gfh:.0f} %")
        p = g.fo2 * env.pressure(depth)
        col = C["ok"] if p <= po2 + 1e-9 else (C["warn"] if p <= po2c + 1e-9 else C["danger"])
        status = ("within working limit" if p <= po2 + 1e-9 else
                  "contingency range only" if p <= po2c + 1e-9 else "EXCEEDS contingency limit")
        self.t_po2.set(f"{p:.2f} bar", status, col)
        self._draw_window(env, g, po2, po2c, depth, gfh)

    def _draw_window(self, env, g, po2, po2c, depth, gfh):
        u = self.units
        P = self.plot_window
        P.clear()
        P.ylabel = f"Depth ({u.depth_unit})"
        fmax = 0.60 if g.fo2 <= 0.5 else 1.0
        dmax = 50.0
        fs = [0.21 + (fmax - 0.21) * i / 120 for i in range(121)]
        mod14 = [min(dmax, mod(Nitrox(f), po2, env)) for f in fs]
        mod16 = [min(dmax, mod(Nitrox(f), po2c, env)) for f in fs]
        X = [100 * f for f in fs]
        D = u.depth_out
        P.fill(X + X[::-1], [D(v) for v in mod16] + [D(dmax)] * len(X), "#f6d5cc",
               label=f"PO2 > {po2c:.1f}")
        P.fill(X + X[::-1], [D(v) for v in mod14] + [D(v) for v in mod16[::-1]], "#fbe7c6",
               label=f"PO2 {po2:.1f}–{po2c:.1f}")
        st = TissueState.surface_equilibrium(env.surface_pressure)
        for T, col in ((10, SERIES[3]), (20, SERIES[0]), (40, SERIES[2]), (80, SERIES[5])):
            ys = []
            for f in fs:
                fn2 = 1 - f

                def h(d, fn2=fn2, T=T):
                    return ndl_constant_depth(st, env.pressure(d), fn2,
                                              env.surface_pressure, gfh) - T
                lo, hi = 0.0, dmax
                if h(hi) > 0:
                    ys.append(None)
                    continue
                if h(lo) < 0:
                    ys.append(0.0)
                    continue
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    lo, hi = (mid, hi) if h(mid) > 0 else (lo, mid)
                ys.append(D(0.5 * (lo + hi)))
            P.line(X, ys, color=col, width=1.6, dash=(5, 3), label=f"NDL {T} min")
        P.line(X, [D(v) if v < dmax else None for v in mod14], color=C["warn"], width=2.2)
        P.line(X, [D(v) if v < dmax else None for v in mod16], color=C["danger"], width=2.2)
        P.line([100 * g.fo2] * 2, [0, D(dmax)], color=C["deep"], width=1.2, dash=(2, 3))
        P.line([21, 100 * fmax], [D(depth)] * 2, color=C["deep"], width=1.2, dash=(2, 3))
        P.marker(100 * g.fo2, D(min(dmax, depth)), color=C["deep"], label=f"{g} at planned depth")
        P.marker(100 * g.fo2, D(min(dmax, mod(g, po2, env))), color=C["warn"])
        P.set_limits((21, 100 * fmax), (0, D(dmax)))
        P.redraw()

    # ------------------------------------------------------------ blend tab
    def _build_blend_tab(self):
        tab = ttk.Frame(self.nb, padding=12)
        self.nb.add(tab, text="  Blend & cylinder  ")
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        side = ttk.Frame(tab)
        side.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        a = card(side, "Partial-pressure fill (O2, then air)")
        a.pack(fill="x")
        self.b_vol = Field(self, a, "Cylinder volume", 12.0, unit="L", row=1)
        self.b_p0 = Field(self, a, "Now in cylinder", 0.0, kind="pressure", row=2)
        self.b_f0 = Field(self, a, "  …at oxygen", 20.95, unit="%", row=3)
        self.b_ft = Field(self, a, "Target oxygen", 32.0, unit="%", row=4)
        self.b_pt = Field(self, a, "Target pressure", 200.0, kind="pressure", row=5)
        self.b_T = Field(self, a, "Settled temperature", 20.0, kind="temp", row=6)
        ttk.Button(a, text="Plan fill", style="Accent.TButton",
                   command=self.compute_blend).grid(row=7, column=0, columnspan=3, sticky="ew",
                                                    pady=(10, 0))
        c = card(side, "Cylinder contents")
        c.pack(fill="x", pady=(12, 0))
        self.c_p = Field(self, c, "Gauge reading", 232.0, kind="pressure", row=1)
        self.c_T = Field(self, c, "…at temperature", 40.0, kind="temp", row=2)
        self.c_T2 = Field(self, c, "Cools to", 20.0, kind="temp", row=3)
        self.c_f = Field(self, c, "Oxygen", 32.0, unit="%", row=4)

        main = ttk.Frame(tab)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)
        tiles = ttk.Frame(main)
        tiles.grid(row=0, column=0, columnspan=2, sticky="ew")
        for i in range(4):
            tiles.columnconfigure(i, weight=1, uniform="b")
        self.t_fill = Tile(tiles, "Stop oxygen at", self.why(self._explain_blend))
        self.t_o2 = Tile(tiles, "Oxygen used", None)
        self.t_free = Tile(tiles, "Usable gas", self.why(
            lambda: explain.explain_free_gas(self.c_p.get(), self.c_f.get() / 100,
                                             self.b_vol.get(), self.c_T.get())))
        self.t_cool = Tile(tiles, "Gauge after cooling", None)
        for i, t in enumerate((self.t_fill, self.t_o2, self.t_free, self.t_cool)):
            t.frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0),
                         pady=(0, 10))
        p1 = card(main, padding=(8, 8))
        p1.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        p1.columnconfigure(0, weight=1)
        p1.rowconfigure(0, weight=1)
        self.plot_fill = Plot(p1, title="Fill path: gauge pressure vs oxygen fraction",
                           xlabel="Oxygen in cylinder (%)", fonts=self.fonts)
        self.plot_fill.grid(row=0, column=0, sticky="nsew")
        p2 = card(main, padding=(8, 8))
        p2.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        p2.columnconfigure(0, weight=1)
        p2.rowconfigure(0, weight=1)
        self.plot_z = Plot(p2, title="Compressibility Z = PV/(nRT): three models",
                        xlabel="", ylabel="Z", fonts=self.fonts)
        self.plot_z.grid(row=0, column=0, sticky="nsew")

    def _explain_blend(self):
        return explain.explain_blend(self.b_ft.get() / 100, self.b_pt.get(),
                                     volume_l=self.b_vol.get(), start_pressure=self.b_p0.get(),
                                     start_fo2=self.b_f0.get() / 100,
                                     temperature_c=self.b_T.get())

    def compute_blend(self):
        if self._guard(self._compute_blend):
            self.say(DISCLAIMER)

    def _compute_blend(self):
        u = self.units
        pu, vu = u.pressure_unit, u.volume_unit
        V, P0, f0 = self.b_vol.get(), self.b_p0.get(), self.b_f0.get() / 100
        ft, Pt, Tc = self.b_ft.get() / 100, self.b_pt.get(), self.b_T.get()
        if V <= 0:
            raise ValueError("cylinder volume must be positive")
        if not -30 <= Tc <= 75:
            raise ValueError("temperature must lie between -30 and 75 °C")
        kw = dict(volume_l=V, start_pressure=P0, start_fo2=f0, temperature_c=Tc)
        real = blending.plan_partial_pressure(ft, Pt, **kw)
        ideal = blending.plan_partial_pressure(ft, Pt, model="ideal", **kw)
        classic = blending.ideal_o2_pressure(ft, Pt, P0, f0) + P0
        if real.feasible:
            self.t_fill.set(f"{u.pressure_out(real.fill_add_to):.1f} {pu}",
                            f"then air to {u.pressure_out(Pt):.0f} {pu}. Ideal gas says "
                            f"{u.pressure_out(ideal.fill_add_to):.1f}; textbook formula "
                            f"{u.pressure_out(classic):.1f}")
            self.t_o2.set(f"{u.volume_out(real.add_free_liters):.0f} {vu}",
                          f"free O2 · air {u.volume_out(real.top_free_liters):.0f} {vu}")
        else:
            self.t_fill.set("Drain first", real.message, C["danger"])
            self.t_o2.set("–", "")
        cp, cT, cT2, cf = self.c_p.get(), self.c_T.get(), self.c_T2.get(), self.c_f.get() / 100
        g_real = cylinder.free_gas(cp, cf, volume_l=V, temperature_c=cT)
        g_ideal = cylinder.free_gas(cp, cf, volume_l=V, temperature_c=cT, model="ideal")
        self.t_free.set(f"{u.volume_out(g_real):.0f} {vu}",
                        f"ideal-gas estimate {u.volume_out(g_ideal):.0f} {vu} "
                        f"({100 * (g_real / g_ideal - 1):+.1f} %)")
        p2 = cylinder.settled_pressure(cp, cT, cT2, cf, volume_l=V)
        self.t_cool.set(f"{u.pressure_out(p2):.1f} {pu}",
                        f"from {u.pressure_out(cp):.0f} {pu} at {u.temp_out(cT):.0f}{u.temp_unit}")
        self._draw_fill(real, ideal, V, P0, f0, Tc)
        self._draw_z(cf, cT)

    def _fill_path(self, plan, V, P0, f0, Tc, model):
        T = Tc + T0_C
        pts_x, pts_p = [], []
        n0 = plan.n_start
        for i in range(41):
            nA = plan.n_add * i / 40
            n = n0 + nA
            x = (n0 * f0 + nA * 1.0) / n
            pts_x.append(100 * x)
            pts_p.append(eos.pressure_from_moles(n, V, T, x, model) - P_ATM)
        n1 = n0 + plan.n_add
        x1 = (n0 * f0 + plan.n_add) / n1
        for i in range(1, 41):
            nB = plan.n_top * i / 40
            n = n1 + nB
            x = (n1 * x1 + nB * FO2_AIR) / n
            pts_x.append(100 * x)
            pts_p.append(eos.pressure_from_moles(n, V, T, x, model) - P_ATM)
        return pts_x, pts_p

    def _draw_fill(self, real, ideal, V, P0, f0, Tc):
        u, P = self.units, self.plot_fill
        P.clear()
        P.ylabel = f"Gauge pressure ({u.pressure_unit})"
        if not (real.feasible and ideal.feasible):
            P.set_limits((20, 100), (0, u.pressure_out(max(real.target_pressure, 10))))
            P.text(25, u.pressure_out(real.target_pressure) * 0.5, real.message,
                   color=C["danger"])
            P.redraw()
            return
        xr, pr = self._fill_path(real, V, P0, f0, Tc, "reference")
        xi, pi = self._fill_path(ideal, V, P0, f0, Tc, "ideal")
        P.line(xi, [u.pressure_out(p) for p in pi], color=C["muted"], width=2, dash=(6, 4),
               label="ideal gas")
        P.line(xr, [u.pressure_out(p) for p in pr], color=C["sea"], width=2.6,
               label="real gas (reference EOS)")
        P.marker(xr[40], u.pressure_out(pr[40]), color=C["o2"], label="stop O2 here")
        P.marker(xr[-1], u.pressure_out(pr[-1]), color=C["ok"], label="final mix")
        xs = xr + xi
        lo, hi = min(xs), max(xs)
        pad = max(2.0, 0.1 * (hi - lo))
        P.set_limits((max(0, lo - pad), min(100, hi + pad)),
                     (0, u.pressure_out(max(pr + pi) * 1.08)))
        P.redraw()

    def _draw_z(self, fo2, Tc):
        u, P = self.units, self.plot_z
        P.clear()
        P.xlabel = f"Absolute pressure ({u.pressure_unit}), {u.temp_out(Tc):.0f}{u.temp_unit}, " \
                   f"{100 * fo2:.0f} % O2"
        T = min(max(Tc + T0_C, eos.T_RANGE[0]), eos.T_RANGE[1])
        ps = [1 + 3 * i for i in range(101)]
        P.line([u.pressure_out(p) for p in ps], [1.0] * len(ps), color=C["muted"], dash=(6, 4),
               label="ideal")
        P.line([u.pressure_out(p) for p in ps], [eos.z(T, p, fo2, "pr") for p in ps],
               color=SERIES[3], width=2, label="Peng–Robinson")
        zr = [eos.z(T, p, fo2) for p in ps]
        P.line([u.pressure_out(p) for p in ps], zr, color=C["sea"], width=2.6, label="reference")
        P.set_limits((0, u.pressure_out(300)), (min(zr + [0.9]) - 0.01, max(zr + [1.0]) + 0.02))
        P.redraw()

    # -------------------------------------------------------------- plan tab
    def _build_plan_tab(self):
        tab = ttk.Frame(self.nb, padding=12)
        self.nb.add(tab, text="  Dive plan  ")
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        side = ttk.Frame(tab)
        side.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        lv = card(side, "Levels")
        lv.pack(fill="x")
        self.levels_metric: list[tuple[float, float]] = [(30.0, 20.0)]
        self.tree_lv = ttk.Treeview(lv, columns=("d", "t"), show="headings", height=3)
        self.tree_lv.heading("d", text="Depth")
        self.tree_lv.heading("t", text="Minutes")
        self.tree_lv.column("d", width=90, anchor="e")
        self.tree_lv.column("t", width=90, anchor="e")
        self.tree_lv.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.l_d = Field(self, lv, "Depth", 30.0, kind="depth", row=2)
        self.l_t = Field(self, lv, "Minutes", 20.0, unit="min", row=3)
        btns = ttk.Frame(lv, style="Card.TFrame")
        btns.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ttk.Button(btns, text="Add", command=self._add_level).pack(side="left")
        ttk.Button(btns, text="Replace", command=self._replace_level).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove", command=self._remove_level).pack(side="left")
        self._refresh_levels_display()

        gs = card(side, "Gases & model")
        gs.pack(fill="x", pady=(12, 0))
        self.p_gas = Field(self, gs, "Bottom gas O2", 32.0, unit="%", row=1)
        self.p_deco1 = tk.StringVar(value="")
        self.p_deco2 = tk.StringVar(value="")
        for r, (lbl, var) in enumerate((("Deco gas 1 O2", self.p_deco1),
                                        ("Deco gas 2 O2", self.p_deco2)), start=2):
            ttk.Label(gs, text=lbl, style="Field.TLabel").grid(row=r, column=0, sticky="w", pady=3)
            ttk.Entry(gs, textvariable=var, width=9, justify="right").grid(row=r, column=1,
                                                                          sticky="ew")
            ttk.Label(gs, text="% / blank", style="Muted.TLabel").grid(row=r, column=2, sticky="w",
                                                                     padx=(4, 0))
        self.p_gfl = Field(self, gs, "GF low", 30.0, unit="%", row=4)
        self.p_gfh = Field(self, gs, "GF high", 85.0, unit="%", row=5)
        self.p_sac = Field(self, gs, "SAC (RMV)", 20.0, kind="sac", row=6)
        self.p_vol = Field(self, gs, "Bottom cylinder", 12.0, unit="L", row=7)
        self.p_dvol = Field(self, gs, "Each deco cylinder", 7.0, unit="L", row=8)
        self.p_fill = Field(self, gs, "All filled to", 200.0, kind="pressure", row=9)
        self.p_safety = tk.BooleanVar(value=True)
        ttk.Checkbutton(gs, text="Safety stop on no-stop dives", variable=self.p_safety).grid(
            row=10, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Button(gs, text="Plan dive", style="Accent.TButton", command=self.compute_plan).grid(
            row=11, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        main = ttk.Frame(tab)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(1, weight=1)
        tiles = ttk.Frame(main)
        tiles.grid(row=0, column=0, columnspan=2, sticky="ew")
        for i in range(4):
            tiles.columnconfigure(i, weight=1, uniform="p")
        self.t_run = Tile(tiles, "Run time", None)
        self.t_cns = Tile(tiles, "Oxygen exposure", self.why(
            lambda: explain.explain_oxygen(self._need_plan())))
        self.t_gas = Tile(tiles, "Bottom gas left", None)
        self.t_ndl2 = Tile(tiles, "No-stop time", None)
        for i, t in enumerate((self.t_run, self.t_cns, self.t_gas, self.t_ndl2)):
            t.frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0),
                         pady=(0, 10))
        pc = card(main, padding=(8, 8))
        pc.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        pc.columnconfigure(0, weight=1)
        pc.rowconfigure(0, weight=3)
        pc.rowconfigure(1, weight=2)
        self.plot_profile = Plot(pc, title="Profile and decompression ceiling", xlabel="Run time (min)",
                              invert_y=True, fonts=self.fonts, height=260)
        self.plot_profile.grid(row=0, column=0, sticky="nsew")
        self.plot_tissue = Plot(pc, title="Tissue loading at end of bottom time (% of surfacing M-value)",
                             xlabel="Compartment half-time (min)", ylabel="%", fonts=self.fonts,
                             height=180)
        self.plot_tissue.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        rc = card(main, "Ascent schedule")
        rc.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        rc.columnconfigure(0, weight=1)
        rc.rowconfigure(1, weight=1)
        self.tree_stops = ttk.Treeview(rc, columns=("d", "s", "r", "g"), show="headings", height=10)
        for cid, txt, w in (("d", "Depth", 70), ("s", "Stop", 60), ("r", "Run", 70), ("g", "Gas", 70)):
            self.tree_stops.heading(cid, text=txt)
            self.tree_stops.column(cid, width=w, anchor="e")
        self.tree_stops.grid(row=1, column=0, sticky="nsew")
        self.lbl_warn = ttk.Label(rc, text="", style="Warn.TLabel", wraplength=300, justify="left")
        self.lbl_warn.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.lbl_gasuse = ttk.Label(rc, text="", style="Muted.TLabel", wraplength=300,
                                    justify="left")
        self.lbl_gasuse.grid(row=3, column=0, sticky="w", pady=(6, 0))

    def _refresh_levels_display(self, _old=None):
        u = self.units
        self.tree_lv.heading("d", text=f"Depth ({u.depth_unit})")
        self.tree_lv.delete(*self.tree_lv.get_children())
        for d, t in self.levels_metric:
            self.tree_lv.insert("", "end", values=(f"{u.depth_out(d):.1f}", f"{t:g}"))

    def _read_level(self):
        d, t = self.l_d.get(), self.l_t.get()
        if d <= 0 or t < 0:
            raise ValueError("a level needs a positive depth and non-negative time")
        return d, t

    def _add_level(self):
        if self._guard(lambda: self.levels_metric.append(self._read_level())):
            self._refresh_levels_display()
            self.compute_plan()

    def _selected(self):
        sel = self.tree_lv.selection()
        return self.tree_lv.index(sel[0]) if sel else None

    def _replace_level(self):
        i = self._selected()
        if i is None:
            self.say("Select a level to replace.", error=True)
            return
        try:
            self.levels_metric[i] = self._read_level()
        except ValueError as e:
            self.say(str(e), error=True)
            return
        self._refresh_levels_display()
        self.compute_plan()

    def _remove_level(self):
        i = self._selected()
        if i is None or len(self.levels_metric) <= 1:
            self.say("Select a level to remove (at least one must remain).", error=True)
            return
        del self.levels_metric[i]
        self._refresh_levels_display()
        self.compute_plan()

    def _need_plan(self) -> PlanResult:
        if self.last_plan is None:
            raise ValueError("plan a dive first")
        return self.last_plan

    def _deco_gases(self):
        out = []
        for var in (self.p_deco1, self.p_deco2):
            s = var.get().strip()
            if s:
                f = float(s.replace(",", ".")) / 100
                if not 0.21 <= f <= 1.0:
                    raise ValueError("deco gas oxygen must be between 21 and 100 %")
                out.append(Nitrox(f))
        return out

    def compute_plan(self):
        if self._guard(self._compute_plan):
            self.say(DISCLAIMER)

    def _compute_plan(self):
        u, env = self.units, self.env()
        g = Nitrox(self.p_gas.get() / 100)
        deco = self._deco_gases()
        tanks = [Tank(g, self.p_vol.get(), self.p_fill.get())]
        tanks += [Tank(dg, self.p_dvol.get(), self.p_fill.get()) for dg in deco]
        r = plan_dive([Level(d, t) for d, t in self.levels_metric], g, deco,
                      gf_low=self.p_gfl.get() / 100, gf_high=self.p_gfh.get() / 100, env=env,
                      sac=self.p_sac.get(), safety_stop=self.p_safety.get(), tanks=tanks)
        self.last_plan = r
        du = u.depth_unit
        self.t_run.set(f"{r.runtime:.0f} min", f"time to surface {r.tts:.1f} min · "
                       + ("decompression dive" if r.deco else "no-stop dive"),
                       C["danger"] if r.deco and not deco else None)
        self.t_cns.set(f"{100 * r.cns:.0f} % CNS", f"pulmonary dose {r.otu:.0f} OTU",
                       C["danger"] if r.cns > 0.8 else None)
        tk_ = r.tank_report[0]
        if tk_["out_of_gas"]:
            self.t_gas.set("OUT OF GAS", f"needs {u.volume_out(tk_['used_liters']):.0f} "
                           f"{u.volume_unit}, holds {u.volume_out(tk_['available_liters']):.0f}",
                           C["danger"])
        else:
            self.t_gas.set(f"{u.pressure_out(tk_['end_reference']):.0f} {u.pressure_unit}",
                           f"ideal gas would say {u.pressure_out(tk_['end_ideal']):.0f} "
                           f"{u.pressure_unit}",
                           C["danger"] if tk_["below_reserve"] else C["ok"])
        if r.ndl is None:
            self.t_ndl2.set("multilevel", "NDL shown for single-level plans")
        elif math.isinf(r.ndl):
            self.t_ndl2.set("unlimited", "")
        else:
            bt = self.levels_metric[0][1]
            self.t_ndl2.set(f"{r.ndl:.0f} min", f"incl. descent · you plan {bt:g} min",
                            C["ok"] if bt <= r.ndl else C["danger"])
        self.tree_stops.heading("d", text=f"Depth ({du})")
        self.tree_stops.delete(*self.tree_stops.get_children())
        for s in r.stops:
            self.tree_stops.insert("", "end", values=(f"{u.depth_out(s.depth):.0f}",
                                                      f"{s.minutes:.0f}'", f"{s.runtime_end:.0f}'",
                                                      s.gas.name))
        if not r.stops:
            self.tree_stops.insert("", "end", values=("–", "direct", f"{r.runtime:.0f}'", g.name))
        self.lbl_warn.configure(text="\n".join("• " + w for w in r.warnings))
        lines = [f"{k}: {u.volume_out(v):.0f} {u.volume_unit} free gas" for k, v in r.gas_used.items()]
        self.lbl_gasuse.configure(text="Gas required at SAC "
                                  f"{u.volume_out(self.p_sac.get()):.{2 if u.imperial else 0}f} {u.volume_unit}/min — "
                                  + "; ".join(lines))
        self._draw_profile(r)
        self._draw_tissues(r, env)

    def _draw_profile(self, r: PlanResult):
        u, P = self.units, self.plot_profile
        P.clear()
        P.ylabel = f"Depth ({u.depth_unit})"
        ts = [p["t"] for p in r.trace]
        P.line(ts, [u.depth_out(p["ceiling"]) for p in r.trace], color=C["danger"], width=1.6,
               dash=(4, 3), label="ceiling (current GF)")
        P.line(ts, [u.depth_out(p["depth"]) for p in r.trace], color=C["sea"], width=2.6,
               label="diver")
        prev = None
        for s in r.stops:
            label = f"{s.minutes:.0f}'" + (f" {s.gas}" if s.gas != prev else "")
            prev = s.gas
            P.text(s.runtime_end - s.minutes - 0.3, u.depth_out(s.depth), label,
                   color=C["deep"], anchor="e")
        P.set_limits((0, max(ts) * 1.04 if ts else 1), (0, u.depth_out(r.max_depth) * 1.12 + 1))
        P.redraw()

    def _draw_tissues(self, r: PlanResult, env):
        P = self.plot_tissue
        P.clear()
        # tensions at end of last bottom level
        t_end = max(s.runtime_end for s in r.segments if s.kind == "level")
        snap = min(r.trace, key=lambda p: abs(p["t"] - t_end))
        st = TissueState.surface_equilibrium(env.surface_pressure)
        gfh = r.gf_high
        lx: list = []
        ly: list = []
        for i, (p, c) in enumerate(zip(snap["tensions"], st.compartments)):
            pct = 100 * p / c.m_value(env.surface_pressure)
            lim = 100 * c.max_tension(env.surface_pressure, gfh) / c.m_value(env.surface_pressure)
            col = C["danger"] if pct > lim else (C["warn"] if pct > 0.85 * lim else C["glass"])
            P.bar(i + 1, pct, 0.7, col)
            lx += [i + 0.55, i + 1.45, None]
            ly += [lim, lim, None]
        P.line([0.5, 16.5], [100, 100], color=C["danger"], width=1.4, label="M-value (100 %)")
        P.line(lx, ly, color=C["deep"], width=2.0, label=f"surfacing limit at GF {100 * gfh:.0f} %")
        P.set_limits((0.5, 16.5), (0, 120))
        P.xlabel = "Compartment 1–16 (half-times 5 … 635 min)"
        P.redraw()

    # -------------------------------------------------------------- learn tab
    TOPICS = [
        "Maximum operating depth",
        "Best mix",
        "Equivalent air depth (exact)",
        "No-decompression limit",
        "Partial-pressure blending",
        "Real gas: cylinder contents",
        "Oxygen exposure of the plan",
        "Equations of state compared",
        "About antasena",
    ]

    def _build_learn_tab(self):
        tab = ttk.Frame(self.nb, padding=12)
        self.nb.add(tab, text="  Learn  ")
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        left = card(tab, "Topics")
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.lb = tk.Listbox(left, height=len(self.TOPICS), activestyle="none", relief="flat",
                             font=self.fonts.body, selectbackground=C["sea"], width=30,
                             highlightthickness=0, bg=C["card"], fg=C["ink"])
        for t in self.TOPICS:
            self.lb.insert("end", t)
        self.lb.grid(row=1, column=0, sticky="nsew")
        self.lb.selection_set(0)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.show_topic())
        ttk.Label(left, style="Muted.TLabel", wraplength=230, justify="left", text=(
            "Each page is computed live from the values on the other tabs.")).grid(
            row=2, column=0, sticky="w", pady=(10, 0))
        right = card(tab, padding=(4, 4))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.learn = tk.Text(right, wrap="word", font=self.fonts.code, relief="flat", padx=20,
                             pady=16, bg=C["card"], fg=C["ink"])
        sb = ttk.Scrollbar(right, command=self.learn.yview)
        self.learn.configure(yscrollcommand=sb.set)
        self.learn.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

    def topic_text(self, name: str) -> str:
        env = self.env()
        g = self._gas()
        if name == "Maximum operating depth":
            return explain.explain_mod(g, self.g_po2.get(), env).to_text()
        if name == "Best mix":
            return explain.explain_best_mix(self.g_depth.get(), self.g_po2.get(), env).to_text()
        if name == "Equivalent air depth (exact)":
            return explain.explain_ead(g, self.g_depth.get(), env).to_text()
        if name == "No-decompression limit":
            return explain.explain_ndl(g, self.g_depth.get(), self.g_gfh.get() / 100, env).to_text()
        if name == "Partial-pressure blending":
            return self._explain_blend().to_text()
        if name == "Real gas: cylinder contents":
            return explain.explain_free_gas(self.c_p.get(), self.c_f.get() / 100,
                                            self.b_vol.get(), self.c_T.get()).to_text()
        if name == "Oxygen exposure of the plan":
            return explain.explain_oxygen(self._need_plan()).to_text()
        if name == "Equations of state compared":
            return eos_table()
        return ABOUT

    def show_topic(self):
        sel = self.lb.curselection()
        name = self.TOPICS[sel[0] if sel else 0]
        try:
            txt = self.topic_text(name)
        except (ValueError, PlanError) as exc:
            txt = f"{name}\n\nCannot compute with the current inputs: {exc}"
        self.learn.configure(state="normal")
        self.learn.delete("1.0", "end")
        self.learn.insert("1.0", txt)
        self.learn.configure(state="disabled")


def eos_table() -> str:
    lines = ["Equations of state compared",
             "===========================", "",
             "Z = P v / (R T) for air and EAN32 at 20 °C. 'reference' is the multiparameter",
             "Helmholtz mixture model (tabulated, interpolation error < 1e-5);",
             "'PR' is Peng-Robinson with van der Waals mixing.", "",
             f"{'mix':>6} {'P/bar':>6} {'ideal':>7} {'PR':>8} {'reference':>10} {'PR error':>9}"]
    T = 293.15
    for name, f in (("air", FO2_AIR), ("EAN32", 0.32), ("O2", 1.0)):
        for p in (50, 100, 200, 232, 300):
            zp, zr = eos.z(T, p, f, "pr"), eos.z(T, p, f)
            lines.append(f"{name:>6} {p:6d} {1:7.4f} {zp:8.4f} {zr:10.4f} {100 * (zp / zr - 1):+8.2f} %")
    lines += ["", "Consequences for divers:",
              "  - Gas content: above ~150-200 bar air holds less than P x V suggests.",
              "  - Blending: the gauge reading at which to stop adding O2 shifts by about a bar.",
              "  - A hot fill cools to a lower pressure than Gay-Lussac's law predicts."]
    return "\n".join(lines)


ABOUT = f"""antasena {__version__}
{'=' * (9 + len(__version__))}

Rigorous, educational nitrox calculations in pure Python (standard library only).

Named after Antasena, the son of Bima in Javanese wayang, who lives in the
depths of the ocean and breathes underwater.

Authors: Sandy H. S. Herho, Iwan P. Anwar, Andini Alifah, Faruq Khadami,
         Karina A. Sujatmiko, Sito F. Biosa, Alfita P. Handayani,
         Dasapta E. Irawan
License: MIT
Copyright (c) 2026 Bandung Institute of Technology

What is computed exactly
  - MOD, best mix, EAD (classical and alveolar-exact), END
  - Bühlmann ZH-L16C tissue tensions (Schreiner closed form), NDL in closed form
  - Gradient-factor decompression schedules with gas switches
  - CNS and OTU as closed-form integrals over linear segments
  - Real-gas blending, cylinder contents and cooling (reference EOS)
  - Guaranteed limits under analyzer and gauge uncertainty

{DISCLAIMER}
"""


def launch() -> int:
    try:
        app = App()
    except tk.TclError as exc:
        print(f"Cannot open a window ({exc}). Use the command line: antasena --help")
        return 1
    app.mainloop()
    return 0
