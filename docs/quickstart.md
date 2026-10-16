# Python quick start

All functions take depths in meters, pressures in bar (absolute unless the argument says gauge), times in minutes and oxygen as a fraction (0.32 for EAN32).

## Gases and depth limits

```python
>>> from antasena import Nitrox, AIR, Environment, mod, best_mix, ead, ead_exact
>>> ean32 = Nitrox.ean(32)
>>> round(mod(ean32, po2_max=1.4), 2)                 # sea water, sea level
33.44
>>> round(mod(ean32, 1.4, Environment(water="fresh", altitude_m=1500)), 2)
35.99
>>> best_mix(30).name
'EAN34'
>>> round(ead(ean32, 30), 2), round(ead_exact(ean32, 30), 2)
(24.4, 24.48)
```

`Environment.training_tables()` reproduces the rounded agency convention (1 bar at the surface, 10 m per bar).

## Guaranteed limits under analyzer error

```python
>>> from antasena import mod_bounds, ndl_bounds
>>> b = mod_bounds(0.32, 0.01)          # analyzer reads 32 % +/- 1 point
>>> round(b.lo, 1), round(b.hi, 1)      # lo is the guaranteed MOD
(32.1, 34.8)
>>> round(ndl_bounds(0.32, 0.01, 30, gf_high=0.85).lo, 1)
18.1
```

## Planning a dive

```python
>>> from antasena import plan_dive, Level, Tank
>>> r = plan_dive([Level(40, 25)], Nitrox.ean(28), [Nitrox.ean(50)],
...               gf_low=0.30, gf_high=0.85, sac=20,
...               tanks=[Tank(Nitrox.ean(28), 24, 230), Tank(Nitrox.ean(50), 7, 230)])
>>> [(s.depth, s.minutes, s.gas.name) for s in r.stops]
[(21.0, 1.0, 'EAN50'), (9.0, 1, 'EAN50'), (6.0, 4, 'EAN50'), (3.0, 7, 'EAN50')]
>>> round(r.runtime, 1), round(100 * r.cns, 1), round(r.otu)
(44.7, 23.2, 56)
>>> round(r.tank_report[0]["end_reference"]), round(r.tank_report[0]["end_ideal"])
(102, 112)
```

Repetitive dives carry the tissue state and oxygen clocks forward:

```python
>>> from antasena import surface_interval
>>> after = surface_interval(r.final_state, minutes=90)
>>> r2 = plan_dive([Level(18, 40)], Nitrox.ean(32), initial=after)
```

## Blending and cylinders

```python
>>> from antasena import plan_partial_pressure, top_off, free_gas, settled_pressure
>>> p = plan_partial_pressure(0.32, 200)       # from empty, gauge pressures
>>> round(p.fill_add_to, 1), round(p.add_free_liters)
(27.1, 327)
>>> round(free_gas(232, 0.2095))               # usable liters in a 12 L cylinder
2615
>>> round(settled_pressure(230, 45, 20, 0.32), 1)
204.5
```

Every function accepts `model="ideal"`, `"pr"` (Peng–Robinson) or `"reference"` (the default) where an equation of state is involved.

## Derivations

```python
from antasena import explain
print(explain.explain_mod(Nitrox.ean(32)).to_text())
```

```text
Maximum operating depth of EAN32
================================

Equation:
  MOD = (PO2_max / fO2 - P_surf) / (rho g)

Steps:
  surface pressure           P_surf = 1.01325 bar
  hydrostatic gradient       rho g = 1025.0 kg/m3 x 9.80665 m/s2 = 0.100518 bar/m
  ambient pressure at limit  PO2_max / fO2 = 1.40 / 0.3200 = 4.37500 bar
  depth                      (4.37500 - 1.01325) / 0.100518 = 33.444 m

Result: MOD = 33.44 m

Assumptions:
  - Dalton's law: PO2 = fO2 x P_amb (ideal mixing at the low pressures breathed).
  - Hydrostatic pressure with constant water density.

Notes:
  - With the rounded table convention (1 bar, 10 m/bar) the MOD is 33.75 m; the
    difference of +0.31 m comes from density and surface pressure.
```

The same text appears behind every **Why?** button in the app and after `--why` on the command line.
