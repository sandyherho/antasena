# Command line

```console
$ antasena --help
usage: antasena [-h] [--version]
                {gui,mod,bestmix,ead,ndl,blend,topoff,cylinder,plan} ...
```

Run `antasena` without arguments (or `antasena gui`) to open the desktop app. Oxygen can be given as a percentage (`32`) or a fraction (`0.32`). Most commands accept:

`--water {salt,en13319,fresh}`
: water density (default `salt`, 1025 kg/m³).

`--altitude METERS`
: dive-site altitude; the surface pressure follows the International Standard Atmosphere.

`--why`
: print the step-by-step derivation after the result.

## mod

```console
$ antasena mod 32 --analyzer 1
EAN32: MOD at PO2 1.40 bar = 33.4 m
  with analyzer error +/-1.0 %: guaranteed MOD 32.1 m (range 32.1 to 34.8 m)
```

Options: `--po2` (default 1.4), `--analyzer` accuracy in percentage points.

## bestmix

```console
$ antasena bestmix 30
Best mix for 30 m at PO2 1.40 bar: EAN34 (PO2 1.370 bar)
```

## ead

```console
$ antasena ead 32 30
EAN32 at 30 m: EAD 24.48 m (classical 24.40 m)
```

## ndl

```console
$ antasena ndl 32 30 --analyzer 1
EAN32 at 30 m, GF high 85 %: NDL 19.1 min
  analyzer +/-1.0 %: NDL between 18.1 and 20.1 min
```

The limit counts from arrival at depth. Option: `--gf-high` in percent (default 85).

## blend

```console
$ antasena blend 32 200
[real gas ] add O2 to   27.1 bar, top with air to 200 bar   O2 used    327 L
[ideal gas] add O2 to   28.1 bar, top with air to 200 bar   O2 used    333 L
```

Options: `--start` (current gauge pressure), `--start-fo2`, `--volume` (liters), `--temp` (settled °C).

## topoff

```console
$ antasena topoff 100 36 200
After topping with air to 200 bar: 28.81 % O2 (ideal gas 28.51 %)
```

Arguments: current gauge pressure, current oxygen percentage, final gauge pressure.

## cylinder

```console
$ antasena cylinder 230 --temp 45 --cool-to 20
12 L at 230 bar, 45 °C: 2551 usable free liters (ideal gas 2724 L, -6.3 %)
  at 20 °C the gauge will read 204.7 bar
```

## plan

Levels are `DEPTH:MINUTES`, visited in order.

```console
$ antasena plan 40:25 --gas 28 --deco 50 --gf 30 85 --volume 24 --fill 230
Plan: 40:25 on EAN28; GF 30/85
  NDL at depth: 7.3 min
      Stop   Time     Run  Gas
      21 m     1'   30.3'  EAN50
       9 m     1'   32.7'  EAN50
       6 m     4'   37.0'  EAN50
       3 m     7'   44.3'  EAN50
  Run time 44.7 min, TTS 17.4 min, CNS 23.2 %, OTU 56
   EAN28:   2787 L used, ends at 102 bar (ideal-gas estimate 112 bar)
   EAN50:    504 L used, ends at 151 bar (ideal-gas estimate 157 bar)
  ! EAN28 exceeds the working PO2 of 1.40 bar at 40 m (PO2 1.41 bar).
```

Options: `--gas`, `--deco` (one or more), `--gf LOW HIGH`, `--sac` (liters per minute at the surface), `--volume` and `--deco-volume` (liters), `--fill` (bar, all cylinders), `--no-safety-stop`.
