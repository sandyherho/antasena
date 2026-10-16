# Theory

This page derives every relation implemented in antasena. Each section states the governing equation, derives the closed form that the code evaluates, and lists the assumptions. Pressures are absolute and in bar unless marked *gauge*, depths are in meters of water, and times are in minutes.

**Notation.** $\rho$ is the water density and $g$ the acceleration of gravity; $f_{\mathrm{O_2}}$ and $f_{\mathrm{N_2}} = 1 - f_{\mathrm{O_2}}$ are the mole fractions of oxygen and of inert gas (nitrogen with argon); $\mathrm{GF}$ denotes a gradient factor; $R$ is the molar gas constant.

## 1. Hydrostatics

For water of constant density $\rho$, the ambient pressure at depth $d$ is

$$P(d) = P_s + \frac{\rho g}{10^5}\, d ,$$

where $P_s$ is the surface pressure. At altitude $h$ the International Standard Atmosphere gives

$$P_s(h) = P_0 \left(1 - \frac{L h}{T_0}\right)^{gM/(RL)}, \qquad L = 0.0065\ \mathrm{K\,m^{-1}},\quad T_0 = 288.15\ \mathrm{K},$$

with $P_0 = 1.01325$ bar and $M$ the molar mass of air. Because $P(d)$ is affine and strictly increasing, every depth limit is the pre-image of a pressure limit:

$$d = \frac{P - P_s}{\rho g / 10^5}.$$

Three water densities are provided, $\rho = 1025$ (sea water), $1020$ (the EN 13319 gauge convention) and $1000\ \mathrm{kg\,m^{-3}}$ (fresh water), together with the rounded table convention $P_s = 1$ bar and exactly 10 m per bar.

## 2. Dalton's law and the depth limits

A gas breathed at ambient pressure $P$ supplies the partial pressures

$$P_{\mathrm{O_2}} = f_{\mathrm{O_2}} P, \qquad P_{\mathrm{N_2}} = f_{\mathrm{N_2}} P.$$

**Maximum operating depth.** Setting $f_{\mathrm{O_2}} P(d) = P_{\mathrm{O_2}}^{\max}$ gives

$$\mathrm{MOD} = \frac{P_{\mathrm{O_2}}^{\max}/f_{\mathrm{O_2}} - P_s}{\rho g / 10^5}.$$

Since $\partial\,\mathrm{MOD}/\partial f_{\mathrm{O_2}} = -P_{\mathrm{O_2}}^{\max}\big/\big(f_{\mathrm{O_2}}^2\, \rho g/10^5\big) < 0$, the MOD decreases strictly as the oxygen fraction increases.

**Best mix.** Maximizing $f_{\mathrm{O_2}}$ subject to $f_{\mathrm{O_2}} P(d) \le P_{\mathrm{O_2}}^{\max}$ minimizes the inert-gas load. The optimum lies on the constraint,

$$f_{\mathrm{O_2}}^{*} = \frac{P_{\mathrm{O_2}}^{\max}}{P(d)},$$

rounded *down* to a whole percent so that the limit still holds.

**Equivalent air depth.** The classical EAD equates inspired ambient nitrogen pressures, $P_{\mathrm{EAD}}\, f_{\mathrm{N_2}}^{\mathrm{air}} = P(d)\, f_{\mathrm{N_2}}$, with $f_{\mathrm{N_2}}^{\mathrm{air}} = 0.7905$. Tissue models, however, are driven by the *alveolar* inert pressure

$$P_{\mathrm{alv}} = \left(P - p_{\mathrm{H_2O}}\right) f_{\mathrm{N_2}}, \qquad p_{\mathrm{H_2O}} = 0.0627\ \mathrm{bar}.$$

Equating alveolar pressures instead gives

$$P_{\mathrm{EAD}}^{\mathrm{exact}} = \left(P(d) - p_{\mathrm{H_2O}}\right) \frac{f_{\mathrm{N_2}}}{f_{\mathrm{N_2}}^{\mathrm{air}}} + p_{\mathrm{H_2O}}.$$

*Equivalence theorem.* The map $P \mapsto P_{\mathrm{EAD}}^{\mathrm{exact}}$ is affine. A nitrox exposure along any piecewise-linear pressure history therefore produces, compartment by compartment and at every instant, the same tension as air breathed along the mapped history, because tissue tension depends on the alveolar history only ({ref}`Section 4 <sec-tissue>`). The classical EAD is shallower than the exact one by

$$\Delta d = \frac{p_{\mathrm{H_2O}}\left(1 - f_{\mathrm{N_2}}/f_{\mathrm{N_2}}^{\mathrm{air}}\right)}{\rho g / 10^5},$$

which is positive for every nitrox, so the classical formula errs on the non-conservative side (by about 9 cm for EAN32 at 30 m).

**Equivalent narcotic depth.** If oxygen is treated as narcotic, every O₂/N₂ mix is as narcotic as air at the same depth and $\mathrm{END} = d$; otherwise the END reduces to the classical EAD.

## 3. Equations of state and blending

### 3.1 Compressibility

The compressibility factor $Z = Pv/(RT)$, with $v$ the molar volume, relates pressure to amount of substance through

$$n = \frac{PV}{ZRT}.$$

Three models are offered.

*Ideal gas.* $Z = 1$.

*Peng–Robinson.*

$$P = \frac{RT}{v - b} - \frac{a(T)}{v^2 + 2bv - b^2},$$

with, for component $i$ of critical temperature $T_{c,i}$, critical pressure $P_{c,i}$ and acentric factor $\omega_i$,

$$a_i = 0.45724\,\frac{R^2 T_{c,i}^2}{P_{c,i}}\left[1 + \kappa_i\left(1 - \sqrt{T/T_{c,i}}\right)\right]^2, \qquad b_i = 0.07780\,\frac{R T_{c,i}}{P_{c,i}},$$

$$\kappa_i = 0.37464 + 1.54226\,\omega_i - 0.26992\,\omega_i^2,$$

and one-fluid mixing rules $a = \sum_{ij} x_i x_j \sqrt{a_i a_j}$ and $b = \sum_i x_i b_i$. With $A = aP/(RT)^2$ and $B = bP/(RT)$, $Z$ is the root of

$$Z^3 - (1 - B)Z^2 + \left(A - 3B^2 - 2B\right)Z - \left(AB - B^2 - B^3\right) = 0.$$

Above both critical temperatures, which is always the case for diving, the cubic has a single real root. As $P \to 0$, $Z \approx 1 + (b - a/RT)\,P/RT$, the Peng–Robinson second virial coefficient; the test suite checks this slope.

*Reference model (default).* $Z$ is tabulated on a grid $T \in [253.15, 353.15]$ K (step 5 K), $P \in [0, 400]$ bar (step 10 bar) and $x_{\mathrm{O_2}} \in [0, 1]$ (step 0.05), generated from the multiparameter Helmholtz mixture model built on the reference equations of state for nitrogen and oxygen with GERG-type mixing, as implemented in CoolProp. Off-grid values use tensor-product four-point Lagrange interpolation, whose error is $O(h^4)$ in each direction because $Z$ is analytic in the supercritical region. Against 400 random off-grid reference evaluations the maximum relative error is $1.5 \times 10^{-6}$. The mixture model agrees with the Lemmon et al. (2000) air equation within about 0.25 % up to 300 bar; that, not the interpolation, sets the accuracy.

### 3.2 Partial-pressure blending

A cylinder holds $n_0$ mol at oxygen fraction $x_0$. Gas A (fraction $x_A$, normally pure oxygen) and gas B (fraction $x_B$, normally air) are added to reach $n_f$ mol at fraction $x_t$. Conservation of total moles and of oxygen moles,

$$n_0 + n_A + n_B = n_f, \qquad n_0 x_0 + n_A x_A + n_B x_B = n_f x_t,$$

is a linear system with solution

$$n_A = \frac{n_f(x_t - x_B) - n_0(x_0 - x_B)}{x_A - x_B}, \qquad n_B = n_f - n_0 - n_A.$$

The final state is a convex combination on the composition simplex. Pressures enter only through $n_0 = n(P_0, x_0)$, $n_f = n(P_f, x_t)$ and the gauge reading after adding A, which solves $n(P_1, x_1) = n_0 + n_A$ with

$$x_1 = \frac{n_0 x_0 + n_A x_A}{n_0 + n_A}.$$

With $Z = 1$ and absolute pressures this reduces to the textbook formula

$$\Delta P_{\mathrm{O_2}} = \frac{P_f(x_t - x_B) - P_0(x_0 - x_B)}{1 - x_B}.$$

*Feasibility.* With $x_B \le x_t \le x_A$, both additions are non-negative if and only if

$$n_0(x_0 - x_B) \le n_f(x_t - x_B) \quad\text{and}\quad n_0(x_A - x_0) \le n_f(x_A - x_t).$$

Both are upper bounds on $n_0$. When one fails, the start gas must be drained to the amount given by the tighter bound, which the code converts back to a gauge pressure.

*Gauge pressure.* Fill-station gauges read $P - P_{\mathrm{atm}}$. An "empty" cylinder at 0 bar gauge still holds one atmosphere of gas, which the balance includes.

(sec-cylinder)=
### 3.3 Cylinder contents

Usable free gas, expressed as liters at $P_{\mathrm{atm}}$ and the cylinder temperature, is

$$G = \frac{\left[n(P) - n(P_{\mathrm{atm}})\right] RT}{P_{\mathrm{atm}}}.$$

Isochoric cooling from $T_1$ to $T_2$ conserves $n$, so the new pressure $P_2$ solves $n(P_2, T_2) = n(P_1, T_1)$. Breathing $G$ free liters removes $G P_{\mathrm{atm}}/(RT)$ mol. Every inverse $n \mapsto P$ uses Brent's method on $PV - nRT\,Z(T, P, x)$, which is strictly increasing in $P$ throughout the table range.

(sec-tissue)=
## 4. Tissue kinetics (Bühlmann ZH-L16C)

Each compartment $i$ is a well-stirred, perfusion-limited tank,

$$\frac{dP_i}{dt} = k_i\left[P_{\mathrm{alv}}(t) - P_i\right], \qquad k_i = \frac{\ln 2}{\tau_i},$$

where $\tau_i$ is the half-time. On a segment with constant gas and linear depth change the alveolar pressure is linear in time, $P_{\mathrm{alv}}(t) = P_{\mathrm{alv},0} + r t$. The integrating factor $e^{k_i t}$ gives the Schreiner solution

$$P_i(t) = P_{\mathrm{alv},0} + r\left(t - \frac{1}{k_i}\right) - \left(P_{\mathrm{alv},0} - P_{i,0} - \frac{r}{k_i}\right) e^{-k_i t}.$$

*Evaluation.* The textbook form subtracts terms of size $r/k_i$, which for fast compartments on steep, short ramps loses several digits. antasena evaluates the algebraically identical form

$$P_i(t) = P_{i,0} + \left(P_{\mathrm{alv},0} - P_{i,0}\right)\left(1 - e^{-x}\right) + r\,t\,\phi(x), \qquad x = k_i t,$$

$$\phi(x) = 1 - \frac{1 - e^{-x}}{x} = \sum_{n \ge 1} \frac{(-1)^{n+1} x^n}{(n+1)!},$$

with $1 - e^{-x}$ computed by `expm1` and $\phi$ by its series for $x < 0.05$. Tests compare the result against 50-digit arithmetic (relative agreement $10^{-14}$). Because the solution operator of a linear ODE is a semigroup, splitting a segment at any interior time leaves the result unchanged, which the tests also check.

*Initial state.* Tissues start saturated with air at the surface, $P_i = \left(P_s - p_{\mathrm{H_2O}}\right) f_{\mathrm{N_2}}^{\mathrm{air}}$.

## 5. Tolerance, gradient factors and the NDL

Bühlmann's M-value line is

$$M_i(P) = a_i + \frac{P}{b_i}.$$

A gradient factor $\mathrm{GF}$ allows the supersaturation $P_i \le P + \mathrm{GF}\left(M_i(P) - P\right)$. Solving for $P$ gives the ceiling

$$P_{\mathrm{ceil},i} = \frac{P_i - a_i\,\mathrm{GF}}{\mathrm{GF}/b_i + 1 - \mathrm{GF}}, \qquad P_{\mathrm{ceil}} = \max_i P_{\mathrm{ceil},i}.$$

**No-decompression limit.** At constant depth $P_i(t) = P_{\mathrm{alv}} + \left(P_{i,0} - P_{\mathrm{alv}}\right) e^{-k_i t}$ approaches $P_{\mathrm{alv}}$ monotonically. A direct ascent is allowed while $P_i \le \hat M_i$, where

$$\hat M_i = P_s + \mathrm{GF}_{\mathrm{high}}\left(M_i(P_s) - P_s\right).$$

If $P_{\mathrm{alv}} > \hat M_i > P_{i,0}$, the limit is first reached at

$$t_i = \frac{1}{k_i} \ln \frac{P_{\mathrm{alv}} - P_{i,0}}{P_{\mathrm{alv}} - \hat M_i}, \qquad \mathrm{NDL} = \min_i t_i,$$

and otherwise compartment $i$ imposes no limit. The result is exact; tests confirm it against bisection on the ceiling condition.

*Monotonicity.* Each $t_i$ decreases strictly with $P_{\mathrm{alv}}$, and $P_{\mathrm{alv}}$ increases with depth and with $f_{\mathrm{N_2}}$. The minimum of decreasing functions is decreasing, so the NDL decreases with depth and with $f_{\mathrm{N_2}}$; this justifies the corner evaluation of {ref}`Section 8 <sec-guaranteed>`.

*Coefficients.* ZH-L16C uses compartment 1b ($\tau = 5$ min). The $b$ coefficients follow $b = 1.005 - \tau^{-1/2}$ and the ZH-L16A $a$ coefficients follow $a = 2\tau^{-1/3}$; version C lowers $a$ for the intermediate compartments. The published $b$ of the 18.5-min compartment, 0.7825, lies 0.0100 above the formula value; antasena uses the published value.

## 6. Decompression schedule

1. A dive is a decompression dive if and only if a direct ascent would violate $\mathrm{GF}_{\mathrm{high}}$, the same criterion that defines the NDL.
2. The first stop is the ceiling under $\mathrm{GF}_{\mathrm{low}}$, rounded up to the stop grid (3 m by default, last stop 3 m).
3. Between the first-stop pressure $P_1$ and the surface, the gradient factor varies linearly with pressure:

   $$\mathrm{GF}(P) = \mathrm{GF}_{\mathrm{high}} + \left(\mathrm{GF}_{\mathrm{low}} - \mathrm{GF}_{\mathrm{high}}\right)\frac{P - P_s}{P_1 - P_s}.$$

4. A move to the next grid depth is simulated with the Schreiner solution at the ascent rate and taken only if the ceiling at the destination's gradient factor lies at or above the destination; otherwise the diver waits in whole minutes.
5. On arriving at a grid depth, the richest decompression gas with $P_{\mathrm{O_2}} \le 1.6$ bar is selected, with an optional fixed switch time.

The test suite replays every plan and asserts that the diver is never shallower than the ceiling, that the surfacing condition holds at the end, and that leaving the last stop one minute early would violate it.

## 7. Oxygen toxicity

**CNS clock.** With $T_{\lim}$ the single-exposure time limit,

$$\mathrm{CNS} = \int \frac{dt}{T_{\lim}\left(P_{\mathrm{O_2}}(t)\right)}.$$

The limit is linear in $P_{\mathrm{O_2}}$ on each band, $T_{\lim}(p) = m\,p + c$, and on a segment $p(t) = p_a + \beta t$, so

$$\int \frac{dt}{T_{\lim}} = \frac{1}{\beta m} \ln \frac{T_{\lim}(p_b)}{T_{\lim}(p_a)} \qquad (\beta m \ne 0).$$

The code splits each segment at the band edges and sums. Between 0.6 and 1.6 bar the bands reproduce the NOAA single-exposure limits at every tabulated pressure. Below 0.6 bar, where the NOAA table is silent, antasena follows Baker's method: no accrual for $P_{\mathrm{O_2}} \le 0.5$ bar and $T_{\lim} = 1800 - 1800\,P_{\mathrm{O_2}}$ on $(0.5, 0.6]$, so the limit is 900 min just above 0.5 bar. Plans above 1.6 bar are rejected. Surface elimination uses a 90-min half-time.

**Pulmonary dose.** With $u = (p - 0.5)/0.5$ and $\mathrm{OTU} = \int u^{5/6}\, dt$ for $p > 0.5$ bar, a linear segment gives

$$\mathrm{OTU} = \frac{3}{11} \frac{\Delta t}{p_b - p_a}\left[u_b^{11/6} - u_a^{11/6}\right].$$

The formula remains valid across the 0.5-bar threshold when $u$ is clipped at zero, because the clipped integrand has the clipped antiderivative.

(sec-guaranteed)=
## 8. Guaranteed limits under measurement error

An analyzer reading $f_{\mathrm{O_2}}$ with accuracy $\pm\delta$ places the true fraction in $[f_{\mathrm{O_2}} - \delta,\ f_{\mathrm{O_2}} + \delta]$. For a function monotone in each argument, the exact range over the input box is attained at its corners. Hence the guaranteed MOD is $\mathrm{MOD}(f_{\mathrm{O_2}} + \delta)$ minus any depth-gauge error, and the guaranteed NDL is the NDL at the deepest depth and leanest mix. Property-based tests sample the box and verify that every sampled value lies inside the reported bounds.

## 9. Gas consumption

With a surface respiratory minute volume $\dot V$ (liters per minute at ambient pressure), the gas used on a segment, expressed at $P_{\mathrm{atm}}$, is

$$\frac{\dot V\, \bar P\, \Delta t}{P_{\mathrm{atm}}},$$

where $\bar P$ is the mean ambient pressure; this is exact for linear pressure histories. The cylinder end pressure then follows from {ref}`Section 3.3 <sec-cylinder>` with the reference equation of state, alongside the ideal-gas estimate for comparison.
