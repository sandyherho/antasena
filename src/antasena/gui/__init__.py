"""Desktop app. Import is deferred so the library works without Tk."""


def launch() -> int:
    try:
        from .app import launch as _launch
    except ImportError as exc:  # tkinter missing (some minimal Linux Pythons)
        print(f"The desktop app needs tkinter ({exc}). On Debian/Ubuntu: "
              "sudo apt install python3-tk. The command line works without it: antasena --help")
        return 1
    return _launch()
