"""Unit conversions between the internal SI-like system and imperial display units."""
from __future__ import annotations

FT_PER_M = 1.0 / 0.3048                 # exact (international foot)
PSI_PER_BAR = 1.0e5 / 6894.757293168    # exact (pound-force per square inch)
CUFT_PER_L = 1.0 / 28.316846592         # exact


def m_to_ft(x: float) -> float:
    return x * FT_PER_M


def ft_to_m(x: float) -> float:
    return x / FT_PER_M


def bar_to_psi(x: float) -> float:
    return x * PSI_PER_BAR


def psi_to_bar(x: float) -> float:
    return x / PSI_PER_BAR


def l_to_cuft(x: float) -> float:
    return x * CUFT_PER_L


def cuft_to_l(x: float) -> float:
    return x / CUFT_PER_L


def c_to_f(x: float) -> float:
    return x * 9.0 / 5.0 + 32.0


def f_to_c(x: float) -> float:
    return (x - 32.0) * 5.0 / 9.0


class Units:
    """Display-unit system. Internal values are always metric."""

    def __init__(self, system: str = "metric"):
        if system not in ("metric", "imperial"):
            raise ValueError("system must be 'metric' or 'imperial'")
        self.system = system

    @property
    def imperial(self) -> bool:
        return self.system == "imperial"

    # depth
    @property
    def depth_unit(self) -> str:
        return "ft" if self.imperial else "m"

    def depth_out(self, m: float) -> float:
        return m_to_ft(m) if self.imperial else m

    def depth_in(self, v: float) -> float:
        return ft_to_m(v) if self.imperial else v

    # pressure
    @property
    def pressure_unit(self) -> str:
        return "psi" if self.imperial else "bar"

    def pressure_out(self, bar: float) -> float:
        return bar_to_psi(bar) if self.imperial else bar

    def pressure_in(self, v: float) -> float:
        return psi_to_bar(v) if self.imperial else v

    # gas volume
    @property
    def volume_unit(self) -> str:
        return "cu ft" if self.imperial else "L"

    def volume_out(self, liters: float) -> float:
        return l_to_cuft(liters) if self.imperial else liters

    def volume_in(self, v: float) -> float:
        return cuft_to_l(v) if self.imperial else v

    # temperature
    @property
    def temp_unit(self) -> str:
        return "°F" if self.imperial else "°C"

    def temp_out(self, c: float) -> float:
        return c_to_f(c) if self.imperial else c

    def temp_in(self, v: float) -> float:
        return f_to_c(v) if self.imperial else v
