"""Physical constants and diving conventions used throughout antasena.

All pressures are absolute and in bar, depths in meters of water, times in
minutes and temperatures in kelvin unless a name says otherwise.
"""
from __future__ import annotations

#: Molar gas constant, J mol^-1 K^-1 (CODATA 2018, exact).
R_GAS = 8.314462618

#: Standard acceleration of gravity, m s^-2 (exact, CGPM 1901).
G0 = 9.80665

#: Standard atmosphere, bar.
P_ATM = 1.01325

#: 0 degC in kelvin.
T0_C = 273.15

#: Pascal per bar.
PA_PER_BAR = 1.0e5

#: Mole fraction of O2 in dry air (CO2, Ar lumped with the inert fraction).
FO2_AIR = 0.2095

#: Inert (N2 + Ar) fraction of dry air as treated by the decompression model.
FN2_AIR = 1.0 - FO2_AIR

#: Alveolar water-vapor pressure at 37 degC used by Buhlmann, bar.
P_H2O_ALV = 0.0627

#: Water densities, kg m^-3. ``EN13319`` is the density assumed by the
#: European standard for depth gauges and by most dive computers.
WATER_DENSITY = {
    "fresh": 1000.0,
    "en13319": 1020.0,
    "salt": 1025.0,
}

#: Molar volume of an ideal gas at 0 degC and 1 atm, m^3 mol^-1.
#: Used only to express "free gas" in the conventional surface liters.
V_M_STP = R_GAS * T0_C / (P_ATM * PA_PER_BAR)
