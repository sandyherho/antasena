"""Command line and desktop app smoke tests."""
import os

import pytest

from antasena.cli import main


@pytest.mark.parametrize("argv,needle", [
    (["mod", "32"], "MOD at PO2 1.40 bar = 33.4 m"),
    (["mod", "32", "--analyzer", "1"], "guaranteed MOD 32.1 m"),
    (["bestmix", "30"], "EAN34"),
    (["ead", "32", "30", "--why"], "Equivalent air depth"),
    (["ndl", "32", "30"], "NDL"),
    (["blend", "32", "200", "--why"], "real gas"),
    (["topoff", "100", "36", "200"], "% O2"),
    (["cylinder", "300", "--cool-to", "20", "--temp", "45"], "gauge will read"),
    (["plan", "40:25", "--gas", "28", "--deco", "50", "--why"], "Run time"),
])
def test_cli_commands(argv, needle, capsys):
    assert main(argv) == 0
    assert needle in capsys.readouterr().out


def test_cli_rejects_impossible_plan(capsys):
    with pytest.raises(SystemExit):
        main(["plan", "40:10", "--gas", "40"])


@pytest.fixture
def app():
    tk = pytest.importorskip("tkinter")
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("no display")
    from antasena.gui.app import App
    try:
        a = App()
    except tk.TclError:
        pytest.skip("cannot open a window")
    a.update()
    yield a
    a.destroy()


def test_gui_computes_every_tab(app):
    app.recompute_all()
    assert app.t_mod.value.cget("text") == "33.4 m"
    assert "bar" in app.t_fill.value.cget("text")
    assert app.last_plan is not None
    for i in range(len(app.TOPICS)):
        app.lb.selection_clear(0, "end")
        app.lb.selection_set(i)
        app.show_topic()
        assert len(app.learn.get("1.0", "end")) > 50


def test_gui_unit_toggle_round_trip(app):
    before = [f.var.get() for f in app.fields]
    app.unit_var.set("imperial")
    app._units_changed()
    assert app.t_mod.value.cget("text").endswith("ft")
    app.unit_var.set("metric")
    app._units_changed()
    after = [f.var.get() for f in app.fields]
    for b, a in zip(before, after):
        assert float(a) == pytest.approx(float(b), rel=1e-3, abs=1e-2)


def test_gui_bad_input_reports_instead_of_crashing(app):
    app.g_fo2.var.set("abc")
    app.compute_gas()
    assert "not a number" in app.status.cget("text")


def test_gui_why_windows_open(app):
    w = app.show_text("t", "body")
    w.destroy()
    app.why(lambda: __import__("antasena").explain.explain_mod(
        __import__("antasena").Nitrox.ean(32)))()
