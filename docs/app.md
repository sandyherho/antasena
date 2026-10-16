# The desktop app

Start it with `antasena` (or `antasena-app`, or `python -m antasena`). The header sets the conditions used everywhere: water type (salt, EN 13319, fresh), site altitude, and metric or imperial units. Values typed into fields are recalculated when you press Enter or a Calculate button. Invalid input is reported in the status bar at the bottom and never closes the app.

Cards marked **Why?** open the full derivation of that number with your inputs substituted. The derivation can be copied to the clipboard.

## Gas & limits

```{image} img/gas.png
:alt: Gas & limits tab
:class: screenshot
```

Inputs: oxygen percentage, analyzer accuracy, working and contingency PO2, planned depth and GF high.

- **Maximum operating depth** at the working PO2, with the contingency depth below it.
- **Guaranteed MOD**: the shallowest MOD for any true oxygen fraction inside the analyzer tolerance. Green when the planned depth is within it, red otherwise.
- **Best mix** for the planned depth.
- **Equivalent air depth** in its exact (alveolar) form, with the classical value for comparison.
- **No-stop time**, counted from arrival at depth, with its guaranteed value.
- **PO2 at the planned depth**, colored by limit.

The **operating window** chart shows oxygen fraction against depth. The shaded bands mark PO2 between the working and contingency limits and above the contingency limit; dashed curves are no-stop contours (10, 20, 40 and 80 min); the dots mark your gas at the planned depth and at its MOD.

## Blend & cylinder

```{image} img/blend.png
:alt: Blend & cylinder tab
:class: screenshot
```

The fill planner computes partial-pressure blending with oxygen first and an air top-off. Gauge pressures are read at the settled temperature. If the target cannot be reached without removing gas, the card says how far to drain first.

The **fill path** chart follows the gauge pressure and oxygen fraction through the fill, for real and ideal gas. The **compressibility** chart compares the ideal-gas, Peng–Robinson and reference models for the current mix and temperature.

The cylinder panel gives the usable gas behind a gauge reading and the pressure a hot cylinder will show once it cools.

## Dive plan

```{image} img/plan.png
:alt: Dive plan tab
:class: screenshot
```

Add one or more levels (depth and minutes, excluding transit), choose the bottom gas and up to two deco gases, gradient factors, breathing rate and cylinders, then press **Plan dive**.

- The cards show run time and time to surface, CNS and OTU, bottom gas left by the real-gas model (with the ideal-gas estimate), and the no-stop time including descent.
- The **profile** chart plots the diver's depth and the decompression ceiling. Stop labels give stop minutes, with the gas at each change.
- The **tissue loading** chart shows each of the 16 compartments at the end of the bottom time as a percentage of its surfacing M-value, with the GF-high limit marked for each.
- The ascent schedule table lists stops, run times and gases. Warnings (PO2 above the working limit, reserve, out of gas, CNS) appear beneath it.

## Learn

Every topic page is computed live from the values on the other tabs: MOD, best mix, exact EAD, no-stop limit, blending, cylinder contents, oxygen exposure of the current plan, and a comparison of the three equations of state.

## Units

Switching to imperial converts every field and result in place (feet, psi, cubic feet, °F). PO2 stays in bar. Internally all values remain metric, and switching back restores the original numbers exactly.
