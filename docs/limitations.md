# Scope and limitations

```{danger}
antasena is a planning and education tool. It is not a dive computer, has not been certified by any authority, and must not be used as the sole basis for a dive. Analyze every gas, follow your training agency's procedures, and carry independent means of monitoring depth, time and decompression.
```

## Model scope

- **Gases.** Oxygen and nitrogen only; argon is lumped with nitrogen. No helium, no closed-circuit rebreathers.
- **Decompression model.** Bühlmann ZH-L16C with gradient factors is one model among several. No model removes the risk of decompression sickness. Individual factors (exertion, temperature, hydration, patent foramen ovale, age) are not represented.
- **No-stop limits** are computed for an instantaneous descent on the Gas tab and including the descent on the Plan tab. A direct ascent at 9 m/min is assumed; safety stops are extra margin.
- **Repetitive and altitude dives.** Surface intervals breathe air at the surface. At altitude the diver is assumed to be acclimatized (tissues saturated at the local surface pressure).
- **Oxygen toxicity.** The CNS clock uses the NOAA single-exposure limits, with Baker's extension between 0.5 and 0.6 bar. Plans that exceed 1.6 bar are rejected. CNS and OTU are bookkeeping indices, not predictions of an individual's response.

## Thermodynamics

- The reference equation of state covers −20 to 80 °C and 0 to 400 bar. Its accuracy, about 0.25 % in Z near 300 bar, is set by the underlying mixture model.
- Blending assumes the cylinder is read at a settled, uniform temperature. Gas added quickly heats the cylinder; use the cylinder tool to convert hot readings.
- Gauge accuracy, valve losses and incomplete mixing are not modeled.

## Conventions to be aware of

- In sea water at sea level, pure oxygen at 6 m gives PO₂ 1.616 bar. With the default 1.6 bar deco limit, antasena therefore schedules the oxygen switch at 3 m. The 10 m/bar table convention (`Environment.training_tables()`) restores the 6 m switch.
- Free-gas volumes are expressed at 1.01325 bar, not at the rounded 1 bar used by many tables; the difference is 1.3 %.
- Imperial stop depths are the metric 3 m grid displayed in feet.
