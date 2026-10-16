# Changelog

## 0.0.1 (2026-10-15)

First release.

* Dalton-law quantities: MOD (with guaranteed MOD under analyzer and gauge error), best mix,
  classical and alveolar-exact EAD, END, hypoxic floor; sea, EN 13319 and fresh water; altitude.
* Bühlmann ZH-L16C with gradient factors: cancellation-free Schreiner solution, closed-form NDL,
  multilevel plans, decompression schedules with nitrox/O2 switches, repetitive dives.
* Oxygen toxicity: closed-form CNS (NOAA) and OTU integrals.
* Real-gas thermodynamics: reference-quality Z(T, P, x) table with pure-Python interpolation,
  Peng-Robinson, ideal gas; partial-pressure blending, top-off, drain advice, cylinder contents,
  hot-fill cooling, end pressure after a plan.
* Step-by-step derivations for every result (`--why`, Why? buttons, Learn tab).
* Tkinter desktop app with metric/imperial units; command-line interface.
* Test suite with property-based, closed-form-versus-numerical and invariant tests, plus
  `tools/independent_check.py`, an independent re-implementation of the core results.
* Sphinx documentation for Read the Docs (Furo theme): installation, app guide, command line,
  theory, equation reference, validation, limitations, API reference; examples are tested.
* CNS below 0.6 bar follows Baker's published convention.
* Every equation in the documentation is typeset with MathJax 4 in CI (`tools/check_math.py`).
* American English throughout the code, interface and documentation.
* Logo: a keris with seven luk in a deep-water emblem (`tools/make_logo.py`), also used as the
  app's window icon.
* Copyright: Bandung Institute of Technology.
