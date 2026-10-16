# Equation reference

Every relation antasena evaluates, in one place. Pressures are absolute and in bar unless marked gauge, depth $d$ is in meters and time $t$ in minutes. The derivations are on the {doc}`theory` page, which also defines the notation.

## Hydrostatics

| | Equation | Code |
|---|---|---|
| H1 | $P(d) = P_s + \rho g\, d/10^5$ | `Environment.pressure` |
| H2 | $P_s(h) = P_0\,(1 - Lh/T_0)^{\gamma}$ | `surface_pressure_isa` |

$P_0 = 1.01325$ bar, $L = 0.0065\ \mathrm{K\,m^{-1}}$, $T_0 = 288.15$ K and $\gamma = gM/(RL) \approx 5.2559$. Water density $\rho$ is 1025 (salt), 1020 (EN 13319) or 1000 (fresh) $\mathrm{kg\,m^{-3}}$; $g = 9.80665\ \mathrm{m\,s^{-2}}$.

## Dalton-law limits

| | Equation | Code |
|---|---|---|
| D1 | $P_{\mathrm{O_2}} = f_{\mathrm{O_2}}\, P$ | `po2` |
| D2 | $\mathrm{MOD} = \dfrac{P_{\mathrm{O_2}}^{\max}/f_{\mathrm{O_2}} - P_s}{\rho g/10^5}$ | `mod` |
| D3 | $f_{\mathrm{O_2}}^{*} = \lfloor 100\, P_{\mathrm{O_2}}^{\max}/P(d) \rfloor / 100$ | `best_mix` |
| D4 | $P_{\mathrm{EAD}} = P(d)\, f_{\mathrm{N_2}}/f_{\mathrm{N_2}}^{\mathrm{air}}$ | `ead` (classical) |
| D5 | $P_{\mathrm{EAD}} = (P(d) - p_{\mathrm{H_2O}})\, f_{\mathrm{N_2}}/f_{\mathrm{N_2}}^{\mathrm{air}} + p_{\mathrm{H_2O}}$ | `ead_exact` |
| D6 | $\mathrm{END} = d$ (oxygen narcotic), otherwise D4 | `end` |

$p_{\mathrm{H_2O}} = 0.0627$ bar (alveolar water vapor at 37 °C) and $f_{\mathrm{N_2}}^{\mathrm{air}} = 0.7905$ (air is treated as 20.95 % oxygen).

## Tissue kinetics (Bühlmann ZH-L16C)

| | Equation | Code |
|---|---|---|
| T1 | $P_{\mathrm{alv}} = (P - p_{\mathrm{H_2O}})\, f_{\mathrm{N_2}}$ | `buhlmann.alveolar` |
| T2 | $dP_i/dt = k_i\,(P_{\mathrm{alv}} - P_i)$, $\ k_i = \ln 2/\tau_i$ | |
| T3 | $P_i(t) = P_{i,0} + (P_{\mathrm{alv},0} - P_{i,0})(1 - e^{-k_i t}) + r\,t\,\phi(k_i t)$ | `schreiner` |
| T4 | $M_i(P) = a_i + P/b_i$ | `Compartment.m_value` |
| T5 | $P_{\mathrm{ceil},i} = \dfrac{P_i - a_i\,\mathrm{GF}}{\mathrm{GF}/b_i + 1 - \mathrm{GF}}$ | `Compartment.tolerated` |
| T6 | $t_i = \dfrac{1}{k_i}\ln\dfrac{P_{\mathrm{alv}} - P_{i,0}}{P_{\mathrm{alv}} - \hat M_i}$ | `ndl_constant_depth` |
| T7 | $\mathrm{NDL} = \min_i t_i$ | `ndl_constant_depth` |
| T8 | $\mathrm{GF}(P) = \mathrm{GF}_{\mathrm{high}} + (\mathrm{GF}_{\mathrm{low}} - \mathrm{GF}_{\mathrm{high}})\dfrac{P - P_s}{P_1 - P_s}$ | `plan_dive` |

In T3, $P_{\mathrm{alv}}(t) = P_{\mathrm{alv},0} + r t$ on the segment and

$$\phi(x) = 1 - \frac{1 - e^{-x}}{x} = \sum_{n \ge 1} \frac{(-1)^{n+1} x^n}{(n+1)!},$$

the series being used for $x < 0.05$ to avoid cancellation. In T6,

$$\hat M_i = P_s + \mathrm{GF}_{\mathrm{high}}\,\left(M_i(P_s) - P_s\right)$$

is the largest tension allowed for a direct ascent. In T8, $P_1$ is the first-stop pressure.

## Oxygen exposure

| | Equation | Code |
|---|---|---|
| O1 | $\mathrm{CNS} = \displaystyle\int \frac{dt}{T_{\lim}(P_{\mathrm{O_2}})}$ | `cns_segment` |
| O2 | linear segment: $\displaystyle\sum_{\text{bands}} \frac{1}{\beta m} \ln \frac{T_{\lim}(p_b)}{T_{\lim}(p_a)}$ | `cns_segment` |
| O3 | $\mathrm{OTU} = \dfrac{3}{11}\dfrac{\Delta t}{p_b - p_a}\left[u_b^{11/6} - u_a^{11/6}\right]$ | `otu_segment` |
| O4 | $\mathrm{CNS}(t) = \mathrm{CNS}_0\, 2^{-t/90}$ at the surface | `cns_after_surface_interval` |

On each band the time limit is linear, $T_{\lim} = m\,P_{\mathrm{O_2}} + c$, and $\beta$ is the rate of change of $P_{\mathrm{O_2}}$ on the segment. In O3, $u = (P_{\mathrm{O_2}} - 0.5)/0.5$, clipped at zero. CNS bands ($T_{\lim}$ in minutes):

| $P_{\mathrm{O_2}}$ band (bar) | $m$ | $c$ |
|---|---|---|
| 0.5–0.6 | −1800 | 1800 |
| 0.6–0.7 | −1500 | 1620 |
| 0.7–0.8 | −1200 | 1410 |
| 0.8–0.9 | −900 | 1170 |
| 0.9–1.1 | −600 | 900 |
| 1.1–1.5 | −300 | 570 |
| 1.5–1.6 | −750 | 1245 |

These reproduce the NOAA single-exposure limits at every tabulated pressure; the 0.5–0.6 bar band is Baker's extension.

## Gas thermodynamics

| | Equation | Code |
|---|---|---|
| G1 | $n = PV/(ZRT)$ | `eos.moles` |
| G2 | $P = \dfrac{RT}{v - b} - \dfrac{a(T)}{v^2 + 2bv - b^2}$ | `eos.pengrobinson` |
| G3 | $Z^3 - (1 - B)Z^2 + (A - 3B^2 - 2B)Z - (AB - B^2 - B^3) = 0$ | `z_pr` |
| G4 | $Z(T, P, x)$ by tensor-product cubic interpolation of the reference table | `z_reference` |
| G5 | $n_A = \dfrac{n_f(x_t - x_B) - n_0(x_0 - x_B)}{x_A - x_B}$, $\ n_B = n_f - n_0 - n_A$ | `plan_partial_pressure` |
| G6 | $\Delta P_{\mathrm{O_2}} = \dfrac{P_f(x_t - x_B) - P_0(x_0 - x_B)}{1 - x_B}$ (ideal gas) | `ideal_o2_pressure` |
| G7 | $G = [\,n(P) - n(P_{\mathrm{atm}})\,]\,RT/P_{\mathrm{atm}}$ | `free_gas` |
| G8 | $n(P_2, T_2) = n(P_1, T_1)$, solved for $P_2$ | `settled_pressure` |
| G9 | gas used $= \dot V\,\bar P\,\Delta t/P_{\mathrm{atm}}$ | `plan_dive` |

In G2 and G3,

$$a_i = 0.45724\,\frac{R^2 T_{c,i}^2}{P_{c,i}}\left[1 + \kappa_i\left(1 - \sqrt{T/T_{c,i}}\right)\right]^2, \qquad b_i = 0.07780\,\frac{R\,T_{c,i}}{P_{c,i}},$$

$$\kappa_i = 0.37464 + 1.54226\,\omega_i - 0.26992\,\omega_i^2, \qquad a = \sum_{ij} x_i x_j \sqrt{a_i a_j}, \qquad b = \sum_i x_i b_i,$$

with $A = aP/(RT)^2$ and $B = bP/(RT)$.

## Guaranteed limits

| | Equation | Code |
|---|---|---|
| U1 | $\mathrm{MOD}_{\mathrm{guaranteed}} = \mathrm{MOD}(f_{\mathrm{O_2}} + \delta) - \delta_d$ | `mod_bounds` |
| U2 | $\mathrm{NDL}_{\mathrm{guaranteed}} = \mathrm{NDL}(d + \delta_d,\ f_{\mathrm{O_2}} - \delta)$ | `ndl_bounds` |

$\delta$ is the analyzer accuracy and $\delta_d$ the depth-gauge accuracy. Both bounds follow from monotonicity: the MOD decreases with $f_{\mathrm{O_2}}$, and every $t_i$ in T6 decreases with $P_{\mathrm{alv}}$, which increases with depth and with $f_{\mathrm{N_2}}$.
