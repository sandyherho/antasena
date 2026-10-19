"""antasena: rigorous, educational nitrox diving calculations in pure Python.

Named after Antasena, the son of Bima in Javanese wayang, who lives in the
depths of the ocean and breathes underwater.

Quick start::

    >>> from antasena import Nitrox, mod, plan_dive
    >>> round(mod(Nitrox.ean(32), 1.4), 1)
    33.4

antasena is a planning and teaching tool. It is not a dive computer and does
not replace training, certified equipment, or an analyzed gas label.
"""
from .blending import plan_partial_pressure, top_off
from .buhlmann import ZHL16C_N2, TissueState
from .cylinder import free_gas, pressure_after_use, settled_pressure
from .environment import Environment
from .gas import AIR, OXYGEN, Nitrox, best_mix, ead, ead_exact, end, mod, po2
from .planner import DiverState, Level, Tank, plan_dive, surface_interval
from .toxicity import cns_segment, otu_segment
from .uncertainty import Interval, mod_bounds, ndl_bounds

__version__ = "0.0.2"
__author__ = ("Sandy H. S. Herho, Faruq Khadami, Iwan P. Anwar, "
              "Karina A. Sujatmiko, Sito F. Biosa, Alfita P. Handayani, Dasapta E. Irawan")
__license__ = "MIT"
__copyright__ = "Copyright (c) 2026 Bandung Institute of Technology"

__all__ = [
    "AIR", "OXYGEN", "Nitrox", "Environment", "mod", "best_mix", "ead", "ead_exact", "end", "po2",
    "plan_partial_pressure", "top_off", "free_gas", "settled_pressure", "pressure_after_use",
    "ZHL16C_N2", "TissueState", "plan_dive", "Level", "Tank", "DiverState", "surface_interval",
    "cns_segment", "otu_segment", "Interval", "mod_bounds", "ndl_bounds", "__version__",
]
