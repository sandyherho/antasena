# Installation

antasena needs Python 3.9 or newer and nothing else. The desktop app uses Tkinter, which ships with the standard Python installers for Windows and macOS.

## With pip

```console
$ pip install antasena
```

From a source checkout:

```console
$ git clone https://github.com/sandyherho/antasena
$ cd antasena
$ pip install .
```

`pipx install antasena` installs the app in an isolated environment and puts the `antasena` command on your path.

## Stand-alone executables

Each tagged release builds one-file executables for Windows, macOS and Linux with PyInstaller (the `release` workflow). They contain their own Python and need no installation: download, then double-click to open the app, or run it from a terminal with command-line arguments.

## Linux and Tkinter

Some Linux distributions package Tkinter separately. If `antasena` reports that Tkinter is missing:

```console
$ sudo apt install python3-tk        # Debian, Ubuntu
$ sudo dnf install python3-tkinter   # Fedora
```

The command line and the Python library work without Tkinter.

## Development install

```console
$ pip install -e ".[test]"
$ pytest
```

Optional extras:

`reference`
: installs CoolProp, used only to regenerate the equation-of-state table and to run the reference checks.

Building this documentation locally:

```console
$ pip install -r docs/requirements.txt
$ sphinx-build -b html docs docs/_build/html
```
