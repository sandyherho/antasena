# Validation

antasena is checked in three independent ways.

## 1. Input data against published sources

| Item | Source | Status |
|---|---|---|
| ZH-L16C nitrogen half-times, a and b | Published table (Bühlmann) | all 16 compartments match |
| Alveolar water vapor 0.0627 bar | Bühlmann | matches |
| NOAA single-exposure oxygen limits | NOAA Diving Manual | all 11 values match |
| CNS bands below 0.6 bar, OTU dose law | Baker, *Oxygen toxicity calculations* | match |
| Air equation of state | Lemmon et al. (2000) | reference mixture model agrees within 0.25 % to 300 bar |
| EN 13319 density 1020 kg/m³ | Dive-computer manufacturers | value commonly cited; standard text not checked |

The tabulated ZH-L16 $b$ of the 18.5-min compartment, 0.7825, lies 0.0100 above Bühlmann's generating formula $b = 1.005 - \tau^{-1/2}$. antasena uses the published value, and a test pins the deviation.

## 2. Automated tests

`pytest` runs 113 tests, many property-based (Hypothesis) over random inputs:

- Schreiner solution against RK4 and 50-digit decimal arithmetic; splitting a segment never changes the result.
- Closed-form NDL against bisection on the ceiling condition.
- The EAD equivalence theorem: nitrox at depth $d$ and air at the alveolar-exact EAD load every compartment identically (relative 10⁻¹²).
- CNS and OTU against piecewise quadrature; additivity; time-reversal symmetry; agreement with Baker's coefficient table.
- Mole and oxygen conservation in blending for all three equations of state.
- Equation-of-state interpolation against 400 off-grid reference points; inverse round trips.
- Guaranteed bounds enclose the true value for sampled inputs.
- Decompression schedules never put the diver above the ceiling; leaving the last stop a minute early violates it.
- Every derivation reproduces the library result.
- Every `>>>` example in this documentation reproduces its printed output.
- The desktop app opens, computes every tab, converts units without drift and reports bad input.

## 3. Independent re-implementation

`tools/independent_check.py` recomputes results without reusing antasena's mathematics: tissues by RK4 at a one-second step, CNS from Baker's coefficient table, OTU by numerical integration, thermodynamics by calling CoolProp directly, and MOD/EAD by hand formulas.

| Check | Largest difference |
|---|---|
| MOD, EAD, best mix | 0 |
| No-stop limits, 6 cases | below the 1-s step |
| Five complete plans: final tissue tensions | 4 × 10⁻¹³ relative |
| Ceiling during every second of every ascent | never above the diver |
| CNS / OTU / gas used | 10⁻⁵ / 10⁻⁴ / 10⁻¹⁰ L |
| Following antasena's fill instructions (EAN32, EAN36) | final O₂ fraction within 2.4 × 10⁻⁸ |
| Usable gas, cooling of a hot cylinder | below 10⁻⁴ L, 10⁻⁵ bar |

## Numbers worth knowing

From `tools/validation_report.py`:

| Quantity | Value |
|---|---|
| Interpolation error of the reference Z table | 1.5 × 10⁻⁶ (max relative) |
| Peng–Robinson error in Z below 300 bar | up to 3.7 % |
| Usable air in 12 L at 232 bar, 20 °C | 2615 L (ideal gas: 2748 L, −4.8 %) |
| Usable air in 12 L at 300 bar, 20 °C | 3206 L (ideal gas: 3553 L, −9.8 %) |
| EAN32 to 200 bar, oxygen stop | 27.13 bar real gas; 28.10 ideal; 27.96 textbook |
| Mix obtained by following the textbook target | 32.34 % instead of 32 % |
| EAN32 MOD at 1.4 bar | 33.44 m (salt), 33.61 m (EN 13319), 33.75 m (10 m/bar) |
| EAN32 at 30 m, EAD | 24.48 m exact, 24.40 m classical |

## Reproducing

```console
$ pytest
$ HYPOTHESIS_PROFILE=thorough pytest
$ pip install CoolProp
$ python tools/independent_check.py
$ python tools/validation_report.py
```
