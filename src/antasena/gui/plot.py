"""A small, dependency-free 2-D plotting widget on a Tk Canvas.

Supports linear axes with "nice" ticks, optional inverted y (depth plots),
polylines, filled polygons, markers, text and a legend. The legend sits
outside the axes, in a band between the title and the plot frame that wraps
onto as many rows as the width requires, so it never hides data. The figure
is re-rendered from its stored artists whenever the widget is resized.
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import font as tkfont

from .theme import C


def nice_ticks(lo: float, hi: float, target: int = 6) -> list[float]:
    """Round tick positions covering [lo, hi] (Heckbert's algorithm)."""
    if hi <= lo:
        return [lo]
    span = hi - lo
    raw = span / max(1, target)
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10 * mag)
    start = math.ceil(lo / step - 1e-9) * step
    out, v = [], start
    while v <= hi + 1e-9 * step:
        out.append(round(v, 10))
        v += step
    return out


def _fmt(v: float) -> str:
    if abs(v) >= 1000 or v == int(v):
        return f"{v:.0f}"
    if abs(v) >= 10:
        return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"
    return f"{v:g}"


class Plot(tk.Canvas):
    def __init__(self, master, *, title: str = "", xlabel: str = "", ylabel: str = "",
                 invert_y: bool = False, height: int = 320, fonts=None, **kw):
        super().__init__(master, background=C["card"], highlightthickness=0, height=height, **kw)
        self.title, self.xlabel, self.ylabel = title, xlabel, ylabel
        self.invert_y = invert_y
        self.fonts = fonts
        self.xlim = (0.0, 1.0)
        self.ylim = (0.0, 1.0)
        self.artists: list[tuple] = []
        self.margin = (62, 22, 46, 34)  # left, right, bottom, top (without legend)
        self._legend_h = 0
        self.bind("<Configure>", lambda e: self.redraw())

    # ---- data -> pixel ------------------------------------------------------
    def _box(self):
        w = max(self.winfo_width(), 200)
        h = max(self.winfo_height(), 150)
        l, r, b, t = self.margin
        return l, t + self._legend_h, w - r, h - b

    def px(self, x: float, y: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self._box()
        fx = (x - self.xlim[0]) / (self.xlim[1] - self.xlim[0])
        fy = (y - self.ylim[0]) / (self.ylim[1] - self.ylim[0])
        if not self.invert_y:
            fy = 1.0 - fy
        return x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)

    # ---- artists ------------------------------------------------------------
    def clear(self) -> None:
        self.artists.clear()

    def set_limits(self, xlim, ylim) -> None:
        self.xlim, self.ylim = tuple(xlim), tuple(ylim)

    def line(self, xs, ys, color=C["sea"], width=2.0, dash=None, label=None) -> None:
        self.artists.append(("line", list(xs), list(ys), color, width, dash, label))

    def fill(self, xs, ys, color, stipple="", label=None) -> None:
        self.artists.append(("fill", list(xs), list(ys), color, stipple, label))

    def marker(self, x, y, color=C["danger"], r=5, label=None) -> None:
        self.artists.append(("marker", x, y, color, r, label))

    def text(self, x, y, s, color=C["ink"], anchor="w", small=True) -> None:
        self.artists.append(("text", x, y, s, color, anchor, small))

    def bar(self, x, height, width, color) -> None:
        self.artists.append(("bar", x, height, width, color))

    # ---- rendering ----------------------------------------------------------
    def _clip(self, xs, ys):
        pts = []
        for x, y in zip(xs, ys):
            if x is None or y is None or not (math.isfinite(x) and math.isfinite(y)):
                if pts:
                    yield pts
                pts = []
                continue
            pts.extend(self.px(x, y))
        if pts:
            yield pts

    # legend geometry
    _SW, _GAP, _SEP, _ROW = 22, 6, 20, 18   # swatch width, swatch-text gap, entry gap, row height

    def _legend_items(self) -> list[tuple]:
        items = []
        for a in self.artists:
            if a[0] == "line" and a[6]:
                items.append(("line", a[3], a[6], a[5], a[4]))
            elif a[0] == "fill" and a[5]:
                items.append(("fill", a[3], a[5]))
            elif a[0] == "marker" and a[5]:
                items.append(("marker", a[3], a[5]))
        return items

    def _legend_layout(self, items, small) -> list[list[tuple[tuple, float]]]:
        """Greedy flow layout: rows of (item, entry width) that fit the frame width."""
        fnt = tkfont.Font(root=self, font=small)
        l, r, _, _ = self.margin
        avail = max(self.winfo_width(), 200) - l - r
        rows: list[list[tuple[tuple, float]]] = [[]]
        used = 0.0
        for it in items:
            w = self._SW + self._GAP + fnt.measure(it[2])
            need = w if not rows[-1] else used + self._SEP + w
            if rows[-1] and need > avail:
                rows.append([])
                need = w
            rows[-1].append((it, w))
            used = need
        return [row for row in rows if row]

    def _draw_legend(self, rows, x0, y_top, small) -> None:
        y = y_top + self._ROW / 2
        for row in rows:
            x = x0
            for it, w in row:
                kind, color, label = it[0], it[1], it[2]
                sx0, sx1 = x, x + self._SW
                if kind == "line":
                    self.create_line(sx0 + 1, y, sx1 - 1, y, fill=color,
                                     width=max(2.0, it[4]), dash=it[3] or (), capstyle="butt")
                elif kind == "fill":
                    self.create_rectangle(sx0 + 3, y - 5, sx1 - 3, y + 5, fill=color,
                                          outline=C["line"])
                else:
                    cx = (sx0 + sx1) / 2
                    self.create_oval(cx - 5, y - 5, cx + 5, y + 5, fill=color, outline="white",
                                     width=1.5)
                self.create_text(sx1 + self._GAP, y, text=label, anchor="w", fill=C["ink"],
                                 font=small)
                x += w + self._SEP
            y += self._ROW

    def redraw(self) -> None:
        self.delete("all")
        f = self.fonts
        small = f.small if f else ("TkDefaultFont", 9)
        lab = f.label if f else ("TkDefaultFont", 9, "bold")
        rows = self._legend_layout(self._legend_items(), small)
        self._legend_h = len(rows) * self._ROW + (6 if rows else 0)
        x0, y0, x1, y1 = self._box()
        self.create_rectangle(x0, y0, x1, y1, outline=C["line"], fill="white")
        xt = nice_ticks(*self.xlim)
        yt = nice_ticks(*self.ylim)
        for v in xt:
            X, _ = self.px(v, self.ylim[0])
            self.create_line(X, y0, X, y1, fill=C["grid"])
            self.create_text(X, y1 + 6, text=_fmt(v), anchor="n", fill=C["muted"], font=small)
        for v in yt:
            _, Y = self.px(self.xlim[0], v)
            self.create_line(x0, Y, x1, Y, fill=C["grid"])
            self.create_text(x0 - 6, Y, text=_fmt(v), anchor="e", fill=C["muted"], font=small)
        # fills first, then lines, then markers and text
        order = {"fill": 0, "bar": 1, "line": 2, "marker": 3, "text": 4}
        for a in sorted(self.artists, key=lambda a: order[a[0]]):
            kind = a[0]
            if kind == "fill":
                _, xs, ys, color, stipple, _label = a
                pts = []
                for x, y in zip(xs, ys):
                    X, Y = self.px(x, y)
                    pts += [min(max(X, x0), x1), min(max(Y, y0), y1)]
                if len(pts) >= 6:
                    self.create_polygon(*pts, fill=color, outline="", stipple=stipple)
            elif kind == "bar":
                _, x, h, w, color = a
                X0, Y0 = self.px(x - w / 2, self.ylim[0])
                X1, Y1 = self.px(x + w / 2, h)
                self.create_rectangle(X0, max(min(Y1, y1), y0), X1, Y0, fill=color, outline="")
            elif kind == "line":
                _, xs, ys, color, width, dash, _label = a
                for seg in self._clip(xs, ys):
                    if len(seg) >= 4:
                        self.create_line(*seg, fill=color, width=width, dash=dash or (),
                                         capstyle="round", joinstyle="round")
            elif kind == "marker":
                _, x, y, color, r, _label = a
                X, Y = self.px(x, y)
                if x0 - 1 <= X <= x1 + 1 and y0 - 1 <= Y <= y1 + 1:
                    self.create_oval(X - r, Y - r, X + r, Y + r, fill=color, outline="white", width=2)
            elif kind == "text":
                _, x, y, s, color, anchor, sm = a
                X, Y = self.px(x, y)
                self.create_text(X, Y, text=s, fill=color, anchor=anchor, font=small if sm else lab)
        # clean frame edges after clipping fills
        self.create_rectangle(x0, y0, x1, y1, outline=C["line"])
        self.create_text(x0, 14, text=self.title, anchor="w", fill=C["deep"], font=lab)
        self.create_text((x0 + x1) / 2, y1 + 24, text=self.xlabel, anchor="n",
                         fill=C["muted"], font=small)
        self.create_text(14, (y0 + y1) / 2, text=self.ylabel, angle=90, fill=C["muted"], font=small)
        # legend: outside the axes, between the title and the frame
        self._draw_legend(rows, x0, y0 - self._legend_h - 2, small)
