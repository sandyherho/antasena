"""Partial-pressure blending with real-gas thermodynamics.

Blending is a statement about *amounts of substance*, not pressures. If a
cylinder holds ``n0`` mol at O2 fraction ``x0`` and receives ``nA`` mol of
gas A and ``nB`` mol of gas B, conservation of total moles and of O2 moles

    n0 + nA + nB              = nf
    n0 x0 + nA xA + nB xB     = nf xt

is a 2x2 *linear* system with the unique solution

    nA = [nf (xt - xB) - n0 (x0 - xB)] / (xA - xB)
    nB = nf - n0 - nA.

The final mixture is a barycentric (convex) combination of the three gases
on the composition simplex. Pressures enter only through the equation of
state ``n = P V / (Z R T)``. With ``Z = 1`` the classical "partial pressure"
formula is recovered; with the reference EOS the gauge targets shift because
Z depends on pressure and composition.

Pressures given to this module are **gauge** pressures by default, because
that is what a fill-station gauge shows; they are converted to absolute
pressure with ``P_abs = P_gauge + p_atm``. An "empty" cylinder at 0 bar gauge
therefore still contains one atmosphere of gas.

Fills are assumed isothermal at the settled temperature ``T``: read the
gauge only once the cylinder has returned to ``T`` (hot readings are handled
by :mod:`antasena.cylinder`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import eos
from .constants import FO2_AIR, P_ATM, PA_PER_BAR, R_GAS, T0_C
from .roots import brentq

__all__ = ["BlendPlan", "plan_partial_pressure", "top_off", "ideal_o2_pressure"]


def _abs(p: float, gauge: bool, p_atm: float) -> float:
    return p + p_atm if gauge else p


def _rel(p: float, gauge: bool, p_atm: float) -> float:
    return p - p_atm if gauge else p


def _free_liters(n: float, T: float, p_atm: float) -> float:
    return n * R_GAS * T / (p_atm * PA_PER_BAR) * 1e3


@dataclass
class BlendPlan:
    """Result of :func:`plan_partial_pressure`. Pressures in the input convention."""

    feasible: bool
    model: str
    start_pressure: float
    start_fo2: float
    target_pressure: float
    target_fo2: float
    add_gas_fo2: float
    top_gas_fo2: float
    fill_add_to: float | None = None        # gauge reading after adding gas A
    fill_top_to: float | None = None        # = target pressure
    n_start: float = 0.0
    n_add: float = 0.0
    n_top: float = 0.0
    n_final: float = 0.0
    add_free_liters: float = 0.0
    top_free_liters: float = 0.0
    drain_to: float | None = None           # if infeasible: drain start gas to this
    message: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def add_pressure_increment(self) -> float | None:
        return None if self.fill_add_to is None else self.fill_add_to - self.start_pressure


def plan_partial_pressure(target_fo2: float, target_pressure: float, *,
                          volume_l: float = 12.0,
                          start_pressure: float = 0.0, start_fo2: float = FO2_AIR,
                          add_fo2: float = 1.0, top_fo2: float = FO2_AIR,
                          temperature_c: float = 20.0, model: str = "reference",
                          gauge: bool = True, p_atm: float = P_ATM) -> BlendPlan:
    """Plan "add gas A, then top with gas B" (default: O2 then air).

    Returns the gauge reading at which to stop adding gas A, the amounts of
    each gas, and the free-gas volumes used. If the target cannot be reached
    without removing gas (too much residual gas, or residual too rich or too
    lean), ``feasible`` is False and ``drain_to`` gives the pressure to which
    the start gas must be drained.
    """
    if not 0 <= target_fo2 <= 1 or not 0 <= start_fo2 <= 1:
        raise ValueError("fractions must lie in [0, 1]")
    if add_fo2 <= top_fo2:
        raise ValueError("the added gas must be richer in O2 than the top-off gas")
    if not top_fo2 <= target_fo2 <= add_fo2:
        raise ValueError("target fraction must lie between the top-off and added gas")
    T = temperature_c + T0_C
    P0 = _abs(start_pressure, gauge, p_atm)
    Pf = _abs(target_pressure, gauge, p_atm)
    if Pf <= 0 or P0 < 0:
        raise ValueError("pressures must be physical")
    n0 = eos.moles(P0, volume_l, T, start_fo2, model)
    nf = eos.moles(Pf, volume_l, T, target_fo2, model)
    xA, xB, x0, xt = add_fo2, top_fo2, start_fo2, target_fo2
    nA = (nf * (xt - xB) - n0 * (x0 - xB)) / (xA - xB)
    nB = nf - n0 - nA
    plan = BlendPlan(feasible=True, model=model, start_pressure=start_pressure,
                     start_fo2=start_fo2, target_pressure=target_pressure,
                     target_fo2=target_fo2, add_gas_fo2=xA, top_gas_fo2=xB,
                     n_start=n0, n_add=nA, n_top=nB, n_final=nf)
    tol = 1e-12 * max(1.0, nf)
    if nA < -tol or nB < -tol:
        plan.feasible = False
        # Largest residual amount n0' (same composition x0) for which both
        # additions are non-negative.
        # With xA > xB:  nA >= 0  <=>  n0 (x0 - xB) <= nf (xt - xB)
        #                nB >= 0  <=>  n0 (xA - x0) <= nf (xA - xt)
        # Both are upper bounds on n0 because xB <= xt <= xA and x0 in [0, 1].
        bounds = [n0]
        if x0 - xB > 1e-15:
            bounds.append(nf * (xt - xB) / (x0 - xB))
        if xA - x0 > 1e-15:
            bounds.append(nf * (xA - xt) / (xA - x0))
        n_ok = max(0.0, min(bounds))
        p_ok = eos.pressure_from_moles(n_ok, volume_l, T, x0, model) if n_ok > 0 else 0.0
        plan.drain_to = _rel(p_ok, gauge, p_atm)
        if plan.drain_to < 0:
            plan.message = ("Target not reachable even from an empty cylinder at "
                            "ambient pressure: the cylinder would need to be evacuated.")
        else:
            plan.message = (f"Target not reachable from the current fill: drain to "
                            f"{plan.drain_to:.1f} bar first.")
        return plan
    nA, nB = max(nA, 0.0), max(nB, 0.0)
    n1 = n0 + nA
    x1 = (n0 * x0 + nA * xA) / n1 if n1 > 0 else xA
    P1 = eos.pressure_from_moles(n1, volume_l, T, x1, model)
    plan.n_add, plan.n_top = nA, nB
    plan.fill_add_to = _rel(P1, gauge, p_atm)
    plan.fill_top_to = target_pressure
    plan.add_free_liters = _free_liters(nA, T, p_atm)
    plan.top_free_liters = _free_liters(nB, T, p_atm)
    plan.message = (f"Add gas ({100 * xA:.1f} % O2) to {plan.fill_add_to:.1f} bar, "
                    f"then top with {100 * xB:.1f} % O2 to {target_pressure:.1f} bar.")
    if gauge:
        plan.notes.append("Pressures are gauge readings at the settled temperature.")
    return plan


def ideal_o2_pressure(target_fo2: float, target_pressure: float,
                      start_pressure: float = 0.0, start_fo2: float = FO2_AIR,
                      top_fo2: float = FO2_AIR) -> float:
    """Classical textbook O2 pressure increment (Z = 1, gauge = absolute).

    ``dP_O2 = [Pf (xt - xB) - P0 (x0 - xB)] / (1 - xB)``.
    """
    return (target_pressure * (target_fo2 - top_fo2)
            - start_pressure * (start_fo2 - top_fo2)) / (1.0 - top_fo2)


def top_off(start_pressure: float, start_fo2: float, final_pressure: float, *,
            top_fo2: float = FO2_AIR, volume_l: float = 12.0, temperature_c: float = 20.0,
            model: str = "reference", gauge: bool = True, p_atm: float = P_ATM) -> float:
    """O2 fraction after topping a partial fill with ``top_fo2`` gas.

    Solves for the added amount ``nB`` in ``n(Pf, x(nB)) = n0 + nB`` with
    ``x(nB) = (n0 x0 + nB xB) / (n0 + nB)``.
    """
    T = temperature_c + T0_C
    P0, Pf = _abs(start_pressure, gauge, p_atm), _abs(final_pressure, gauge, p_atm)
    if Pf < P0:
        raise ValueError("final pressure must not be below start pressure")
    n0 = eos.moles(P0, volume_l, T, start_fo2, model)

    def mix(nB: float) -> float:
        return (n0 * start_fo2 + nB * top_fo2) / (n0 + nB)

    def f(nB: float) -> float:
        return eos.moles(Pf, volume_l, T, mix(nB), model) - (n0 + nB)

    hi = eos.moles(Pf, volume_l, T, top_fo2, model) * 1.5 + 1.0
    nB = brentq(f, 0.0, hi, xtol=1e-12)
    return mix(nB)
