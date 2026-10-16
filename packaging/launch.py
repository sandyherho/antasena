"""Entry point for frozen (PyInstaller) builds: opens the app, or runs CLI arguments."""
from antasena.cli import main

raise SystemExit(main())
