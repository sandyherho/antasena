# antasena

**Rigorous, educational nitrox diving calculations and a desktop app in pure Python.**

antasena computes what a nitrox diver and a gas blender need, and shows how every number is obtained. Each result can print its own derivation: the governing equation, every intermediate value with your inputs substituted, the assumptions, and where the model stops being valid.

```{image} img/gas.png
:alt: The Gas & limits tab of the antasena desktop app
:class: screenshot
```

```{warning}
antasena is a planning and teaching tool. It is not a dive computer, it is not certified, and it does not replace training, an analyzed gas label, or your own judgment. Verify every plan.
```

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} Exact, not approximate
Tissue loading, no-stop limits, CNS and OTU are evaluated in closed form on every dive segment. Nothing is time-stepped.
:::

:::{grid-item-card} Real-gas thermodynamics
Blending and cylinder contents use a reference-quality equation of state, interpolated in pure Python to 1.5 × 10⁻⁶.
:::

:::{grid-item-card} Guaranteed limits
MOD and no-stop limits that hold for every oxygen fraction inside your analyzer's tolerance.
:::

:::{grid-item-card} Every number explained
`--why` on the command line, **Why?** buttons and a **Learn** tab in the app.
:::

:::{grid-item-card} Zero dependencies
Standard library only, including the Tkinter app. Stand-alone executables for Windows, macOS and Linux.
:::

:::{grid-item-card} Checked twice
113 automated tests plus an independent re-implementation that shares no mathematics with the package.
:::
::::

## At a glance

```console
$ pip install antasena
$ antasena              # opens the desktop app
$ antasena mod 32 --analyzer 1
EAN32: MOD at PO2 1.40 bar = 33.4 m
  with analyzer error +/-1.0 %: guaranteed MOD 32.1 m (range 32.1 to 34.8 m)
```

```python
>>> from antasena import Nitrox, mod
>>> round(mod(Nitrox.ean(32), 1.4), 2)
33.44
```

```{toctree}
:caption: Getting started
:maxdepth: 2

installation
quickstart
app
cli
```

```{toctree}
:caption: Science
:maxdepth: 2

theory
equations
validation
limitations
```

```{toctree}
:caption: Reference
:maxdepth: 2

api
changelog
citing
license
```

## Name

Antasena is the son of Bima in Javanese wayang. He lives in the depths of the ocean and breathes underwater. The logo pairs the sea with a keris, the Javanese dagger, whose blade carries seven *luk* (bends) drawn from a decaying sine wave.

## Authors

Sandy H. S. Herho, Faruq Khadami, Iwan P. Anwar, Karina A. Sujatmiko, Sito F. Biosa, Alfita P. Handayani, Dasapta E. Irawan.

## Acknowledgments

This work was funded by the ITB 3P Research Program 2026 (Talenta Unggul Scheme) through the Directorate of Research and Innovation at the Bandung Institute of Technology (Project ID: DRI.PN-6-64-2026). We thank the Indonesian Subaquatic Sport Association (POSSI) instructors Jemi Godjali (INA.F00.B3.0091, POSSI Board of Instructors), Saep Saepudin (INA.F00.B1.0396, Indonesian Navy), Mat Ningrum (INA.F00.B1.0375, Instrument Dive Adventure), and Subagiyo (INA.F00.B1.0412, Indonesian Navy) for their guidance during the basic and advanced scuba diving training. We are especially grateful to Andini Alifah (SSI PRO 124122, Mazu Divers) for her exceptional support, insight, and expertise regarding Enriched Air Nitrox 40 course.