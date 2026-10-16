"""Colors, fonts and ttk styles for the antasena desktop app."""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# Deep-water palette: navy chrome, sea-glass accents, warm alerts.
C = {
    "abyss": "#0b2239",
    "deep": "#12385a",
    "sea": "#1f6f8b",
    "glass": "#4fb3bf",
    "foam": "#e8f4f6",
    "paper": "#f7fafb",
    "card": "#ffffff",
    "ink": "#15212b",
    "muted": "#5f7180",
    "line": "#d5e1e6",
    "ok": "#2a9d6f",
    "warn": "#e09f3e",
    "danger": "#c8553d",
    "o2": "#3a86ff",
    "n2": "#8f6bd6",
    "grid": "#e6eef1",
}

SERIES = ["#1f6f8b", "#c8553d", "#2a9d6f", "#8f6bd6", "#e09f3e", "#3a86ff"]


def _pick(root: tk.Misc, *names: str) -> str:
    fams = set(tkfont.families(root))
    for n in names:
        if n in fams:
            return n
    return "TkDefaultFont"


class Fonts:
    def __init__(self, root: tk.Misc):
        ui = _pick(root, "Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Cantarell",
                   "DejaVu Sans", "Helvetica", "Arial")
        mono = _pick(root, "Cascadia Mono", "SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono",
                     "Liberation Mono", "Courier New", "Courier")
        self.ui = ui
        self.mono = mono
        self.body = (ui, 10)
        self.small = (ui, 9)
        self.label = (ui, 9, "bold")
        self.h1 = (ui, 18, "bold")
        self.h2 = (ui, 12, "bold")
        self.big = (ui, 22, "bold")
        self.code = (mono, 10)


def apply(root: tk.Tk) -> Fonts:
    f = Fonts(root)
    root.configure(bg=C["paper"])
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure(".", font=f.body, background=C["paper"], foreground=C["ink"])
    st.configure("TFrame", background=C["paper"])
    st.configure("Card.TFrame", background=C["card"], relief="flat")
    st.configure("Header.TFrame", background=C["abyss"])
    st.configure("TLabel", background=C["paper"], foreground=C["ink"])
    st.configure("Card.TLabel", background=C["card"])
    st.configure("Muted.TLabel", background=C["card"], foreground=C["muted"], font=f.small)
    st.configure("Field.TLabel", background=C["card"], foreground=C["muted"], font=f.label)
    st.configure("H2.TLabel", background=C["card"], foreground=C["deep"], font=f.h2)
    st.configure("Big.TLabel", background=C["card"], foreground=C["deep"], font=f.big)
    st.configure("Warn.TLabel", background=C["card"], foreground=C["danger"], font=f.body)
    st.configure("HeaderTitle.TLabel", background=C["abyss"], foreground="white", font=f.h1)
    st.configure("HeaderSub.TLabel", background=C["abyss"], foreground=C["glass"], font=f.small)
    st.configure("Status.TLabel", background=C["foam"], foreground=C["muted"], font=f.small)
    st.configure("TNotebook", background=C["paper"], borderwidth=0, tabmargins=(12, 8, 12, 0))
    st.configure("TNotebook.Tab", padding=(18, 8), font=f.label, background=C["foam"],
                 foreground=C["muted"], borderwidth=0)
    st.map("TNotebook.Tab", background=[("selected", C["card"])],
           foreground=[("selected", C["deep"])])
    st.configure("Accent.TButton", background=C["sea"], foreground="white", borderwidth=0,
                 focusthickness=0, padding=(14, 7), font=f.label)
    st.map("Accent.TButton", background=[("active", C["deep"]), ("pressed", C["abyss"])])
    st.configure("Why.TButton", background=C["card"], foreground=C["sea"], borderwidth=0,
                 padding=(4, 0), font=f.small)
    st.map("Why.TButton", foreground=[("active", C["deep"])], background=[("active", C["foam"])])
    st.configure("TButton", padding=(10, 5))
    st.configure("TEntry", fieldbackground="white", bordercolor=C["line"], lightcolor=C["line"],
                 padding=4)
    st.configure("TCombobox", fieldbackground="white", padding=3)
    st.configure("TCheckbutton", background=C["card"])
    st.configure("Header.TRadiobutton", background=C["abyss"], foreground="white")
    st.map("Header.TRadiobutton", background=[("active", C["deep"])])
    st.configure("Header.TCombobox", padding=2)
    st.configure("Treeview", rowheight=24, fieldbackground="white", bordercolor=C["line"])
    st.configure("Treeview.Heading", font=f.label, background=C["foam"], foreground=C["deep"])
    return f
