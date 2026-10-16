# API reference

The most used names are importable from the package itself:

```python
from antasena import (Nitrox, AIR, OXYGEN, Environment, mod, best_mix, ead, ead_exact, end,
                      po2, plan_dive, Level, Tank, DiverState, surface_interval,
                      plan_partial_pressure, top_off, free_gas, settled_pressure,
                      pressure_after_use, mod_bounds, ndl_bounds, Interval)
```

## Environment

```{eval-rst}
.. automodule:: antasena.environment
   :members: Environment, surface_pressure_isa
```

## Gases and depth limits

```{eval-rst}
.. automodule:: antasena.gas
   :members: Nitrox, po2, mod, best_mix, ead, ead_exact, end, hypoxic_floor
```

## Tissue model

```{eval-rst}
.. automodule:: antasena.buhlmann
   :members: Compartment, TissueState, schreiner, haldane, ndl_constant_depth
```

## Dive planning

```{eval-rst}
.. automodule:: antasena.planner
   :members: plan_dive, surface_interval, Level, Tank, Stop, Segment, DiverState, PlanResult, PlanError
```

## Oxygen toxicity

```{eval-rst}
.. automodule:: antasena.toxicity
   :members: cns_limit, cns_rate, cns_segment, otu_segment, cns_after_surface_interval, OxygenLimitError
```

## Equations of state

```{eval-rst}
.. automodule:: antasena.eos
   :members: z, moles, pressure_from_moles, free_gas_liters

.. automodule:: antasena.eos.pengrobinson
   :members: z_pr, pr_parameters

.. automodule:: antasena.eos.reference
   :members: z_reference
```

## Blending and cylinders

```{eval-rst}
.. automodule:: antasena.blending
   :members: plan_partial_pressure, top_off, ideal_o2_pressure, BlendPlan

.. automodule:: antasena.cylinder
   :members: Cylinder, free_gas, settled_pressure, pressure_after_use
```

## Uncertainty

```{eval-rst}
.. automodule:: antasena.uncertainty
   :members: Interval, mod_bounds, ndl_bounds, po2_bounds
```

## Derivations

```{eval-rst}
.. automodule:: antasena.explain
   :members: Derivation, explain_mod, explain_best_mix, explain_ead, explain_ndl, explain_blend, explain_free_gas, explain_oxygen
```

## Utilities

```{eval-rst}
.. automodule:: antasena.units
   :members: Units

.. automodule:: antasena.roots
   :members: brentq

.. automodule:: antasena.constants
```
