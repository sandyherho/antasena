"""Equations of state for O2/N2 breathing gases.

Three models of the compressibility factor ``Z = P v / (R T)`` are offered,
in increasing fidelity:

``"ideal"``
    ``Z = 1``. The assumption behind classical partial-pressure blending.
``"pr"``
    Peng-Robinson cubic EOS with van der Waals one-fluid mixing rules. Fully
    transparent and derivable by hand; about 1 to 4 % low in Z at fill
    pressures (quantified in the test suite).
``"reference"`` (default)
    Tensor-product cubic interpolation of a table generated from the
    multiparameter Helmholtz mixture model (reference pure-fluid equations
    for N2 and O2). Interpolation error below 0.01 % in Z; the underlying
    model agrees with the Lemmon et al. (2000) air equation to within
    about 0.25 % up to 300 bar.

All functions take temperature in K, pressure in bar (absolute), the O2
mole fraction ``x_o2`` and volumes in liters.
"""
from __future__ import annotations

from ..constants import PA_PER_BAR, R_GAS
from ..roots import brentq
from .ideal import z_ideal
from .pengrobinson import z_pr
from .reference import P_MAX, T_RANGE, z_reference

__all__ = ["MODELS", "z", "moles", "pressure_from_moles", "free_gas_liters",
           "P_MAX", "T_RANGE"]

MODELS = {"ideal": z_ideal, "pr": z_pr, "reference": z_reference}


def _model(name: str):
    try:
        return MODELS[name]
    except KeyError:
        raise ValueError(f"unknown EOS model {name!r}; choose from {sorted(MODELS)}") from None


def z(T: float, p_bar: float, x_o2: float, model: str = "reference") -> float:
    """Compressibility factor of an O2/N2 mixture."""
    if not 0.0 <= x_o2 <= 1.0:
        raise ValueError("x_o2 must lie in [0, 1]")
    if p_bar < 0.0 or T <= 0.0:
        raise ValueError("pressure must be >= 0 and temperature > 0")
    return _model(model)(T, p_bar, x_o2)


def moles(p_bar: float, volume_l: float, T: float, x_o2: float,
          model: str = "reference") -> float:
    """Amount of gas (mol) in ``volume_l`` liters at ``p_bar`` and ``T``.

    ``n = P V / (Z R T)``.
    """
    if volume_l <= 0:
        raise ValueError("volume must be positive")
    if p_bar == 0.0:
        return 0.0
    return p_bar * PA_PER_BAR * volume_l * 1e-3 / (z(T, p_bar, x_o2, model) * R_GAS * T)


def pressure_from_moles(n_mol: float, volume_l: float, T: float, x_o2: float,
                        model: str = "reference", p_max: float = P_MAX) -> float:
    """Inverse of :func:`moles`: the pressure (bar) holding ``n_mol``.

    Solves ``P V - n R T Z(T, P, x) = 0`` with Brent's method. The function is
    strictly increasing in P throughout the supercritical gas region covered
    here, so the root is unique.
    """
    if n_mol < 0:
        raise ValueError("amount of gas must be non-negative")
    if n_mol == 0.0:
        return 0.0
    if model == "ideal":
        return n_mol * R_GAS * T / (volume_l * 1e-3) / PA_PER_BAR
    v = volume_l * 1e-3

    def f(p: float) -> float:
        return p * PA_PER_BAR * v - n_mol * R_GAS * T * z(T, p, x_o2, model)

    if f(p_max) < 0:
        raise ValueError(f"{n_mol:.4g} mol does not fit in {volume_l} L below {p_max} bar")
    return brentq(f, 0.0, p_max, xtol=1e-10)


def free_gas_liters(p_bar: float, volume_l: float, T: float, x_o2: float,
                    model: str = "reference", p_surface: float = 1.01325) -> float:
    """Gas content expressed as liters at ``p_surface`` and ``T`` (Z = 1).

    This is the "surface liters" quantity divers use for gas planning: the
    volume the cylinder contents would occupy if released at the surface at
    the same temperature.
    """
    n = moles(p_bar, volume_l, T, x_o2, model)
    return n * R_GAS * T / (p_surface * PA_PER_BAR) * 1e3
