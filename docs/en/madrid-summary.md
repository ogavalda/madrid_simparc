# SimParc-R applied to Madrid: Summary

This document explains what SimParc-R is, what was changed to simulate Madrid's residential building stock, and how to reproduce the results. The assumptions behind each of the ten simulated cases are in [Madrid: Simulation Hypotheses](madrid-hypotheses.md).

## 1. What is SimParc-R?

SimParc-R is an open-source residential building-stock simulator developed by Hydro-Québec for the Quebec housing stock ([hq-opensource/simparc-r-simulator](https://github.com/hq-opensource/simparc-r-simulator)). It takes a CSV in which **each row describes one dwelling** (floor area, envelope U-values, HVAC system, occupancy, appliances…) and runs one annual EnergyPlus simulation per row.

Under the hood, it uses NREL's **OpenStudio-HPXML** workflow, the same engine behind ResStock. SimParc-R replaces ResStock's orchestration layer with a Python one:

```
building-stock CSV ──► local.py ──► per dwelling: OpenStudio workflow (5 measures) ──► EnergyPlus ──► results/
   (1 row = 1 dwelling)   │
                          ├─ preprocessing.py   validates columns against the HPXML argument schema
                          ├─ upgrading.py       optional retrofit scenarios (off for Madrid)
                          └─ building.py        Quebec-specific stochastic profiles (EV, pool, spa, heating setpoint)
```

The five measures run for each dwelling are:

1. `BuildResidentialHPXML`: turns the CSV row into an HPXML description.
2. `BuildResidentialScheduleFile`: builds stochastic occupancy schedules.
3. `ModifyStochasticFilePython`: injects SimParc-R's own profiles. It does nothing for Madrid.
4. `HPXMLtoOpenStudio`: builds the thermal model.
5. `ReportSimulationOutput`: runs EnergyPlus and writes annual and timeseries results.

The outputs are an annual summary per dwelling (`results_job0.json.gz`) and Parquet datasets with metadata and 15-minute timeseries.

## 2. What was done for Madrid

The goal was to use the SimParc-R pipeline unchanged on a new city: **10 representative Madrid dwellings**, crossing 2 typologies with 5 construction periods.

| | ≤1940 | 1941–1960 | 1961–1980 | 1981–2007 | 2008–2011 |
|---|---|---|---|---|---|
| **Single-family (row house)** | case 1 | case 2 | case 3 | case 4 | case 5 |
| **Multi-family (apartment, middle floor)** | case 6 | case 7 | case 8 | case 9 | case 10 |

### 2.1 Input data

The source is `madrid/data/C40_CleanHeat_Madrid_ThermalArchetypes_SIMPLIFIED.xlsx`, one sheet per typology. It draws on:

- **IDAE:** geometry (floors, dwellings per floor, Madrid average dwelling floor area, façade/window/party-wall ratios).
- **ERESEE 2020:** wall, roof, floor and window U-values by period.
- **CTE DB-HE / DB-HS3:** reference heating and cooling setpoint schedules and ventilation rates.
- **Ayuntamiento de Madrid registry:** heating fuel (almost entirely natural gas).

Everything the spreadsheet does not cover (window g-value, airtightness, systems, occupancy, appliances) was set by explicit hypothesis. See the [hypotheses document](madrid-hypotheses.md).

### 2.2 Changes to the pipeline

| Change | Where | Why |
|---|---|---|
| Spreadsheet → HPXML CSV generator | `madrid/gen_madrid_archetypes.py` | Converts SI units to HPXML (IP) arguments and writes one row per case. Every field is written explicitly, so no US default applies silently. |
| Madrid weather | `weather/ESP_MD_Madrid-Barajas-Suarez.AP.082210_TMYx.2009-2023.{epw,ddy}` + new `TMYx` entry in `weather/mapping/Mapping-Region-EPWfiles.json` | TMYx typical year 2009–2023 for Madrid-Barajas airport |
| Design days read from `.ddy` | `measures/HPXMLtoOpenStudio/resources/weather.rb` (`get_design_info_from_ddy`) | OpenStudio 3.9 cannot parse this EPW's design-conditions header, so the 99% heating / 1% cooling design days are read from the companion `.ddy` file instead |
| Tolerant CSV reading | `local.py` | Falls back to `;` when a CSV was re-saved by Excel under a European locale |
| Results summary and charts | `madrid/madrid_results_summary.py` | Demand and energy per case (kWh and kWh/m²), end-use breakdown, peaks, and interactive charts |
| Connected 3D geometry (optional) | `madrid/geometry/` | Rebuilds a closed 3D model per case for visual QA. The simulated `.osm` has its surfaces deliberately pulled apart. |

### 2.3 Issues found and fixed on the way

These are worth knowing before reusing SimParc-R anywhere outside Quebec:

1. **Quebec stochastic heating setpoint.** When the non-HPXML column `Heating Setpoint` is truthy, `building.py` generates a Quebec occupant-behaviour setpoint profile, and the CTE schedule is **silently ignored**. It is set to `False` for Madrid. Fixing this cut heating demand by 40–60%.
2. **US default loads.** `BuildResidentialHPXML` adds a gas grill, gas landscape lighting, a gas fireplace and a well pump by default. All are disabled explicitly.
3. **Slab insulation not applied.** The generator originally used wrong column names, so the floor U-value never reached the model. This is now fixed.
4. **Cooling system.** A cooling-only `mini-split` crashes the sizing code in this OS-HPXML version, so a `room air conditioner` (EER) is used instead.
5. **Heat recovery ventilator inputs.** The HRV needs `num_units_served ≥ 1` and a *sensible* recovery efficiency above 0. For "no recovery", 0.02 is used.

## 3. Headline results

Annual values from `results/madrid_results_summary.csv`. Demand is the thermal load met by the system; final energy is gas plus electricity.

| Case | Archetype | Floor area (m²) | Heating demand (kWh/m²·yr) | Cooling demand (kWh/m²·yr) | Final energy (kWh/m²·yr) |
|---|---|---|---|---|---|
| 1 | SF ≤1940 | 126 | 118 | 66 | 240 |
| 2 | SF 1941–1960 | 105 | 106 | 66 | 234 |
| 3 | SF 1961–1980 | 170 | 83 | 50 | 171 |
| 4 | SF 1981–2007 | 186 | 58 | 39 | 131 |
| 5 | SF 2008–2011 | 195 | 31 | 30 | 90 |
| 6 | MF ≤1940 | 87 | 52 | 40 | 159 |
| 7 | MF 1941–1960 | 89 | 43 | 39 | 145 |
| 8 | MF 1961–1980 | 91 | 40 | 37 | 138 |
| 9 | MF 1981–2007 | 103 | 33 | 32 | 121 |
| 10 | MF 2008–2011 | 109 | 15 | 30 | 93 |

How to read these results:

- Heating demand falls steadily with the construction period, as the envelope improves.
- Apartments have much lower heating demand than row houses, because a middle-floor unit has no roof or ground floor exposed.
- Electricity per dwelling is almost constant, at about 6.2 MWh/yr (MF) and 8–9 MWh/yr (SF). Occupancy (3 people) and appliances are the same in every case, so smaller dwellings show a higher kWh/m².

Interactive charts are in `results/madrid_demand_charts.html`.

## 4. Repository layout

```
madrid/                                   ◄ everything Madrid-specific
├── data/
│   ├── C40_CleanHeat_Madrid_ThermalArchetypes_SIMPLIFIED.xlsx   source archetypes
│   └── template-common-inputs.csv        inputs shared by all 10 cases (occupancy, appliances…)
├── gen_madrid_archetypes.py              xlsx + template → building-stock CSV
├── building-stock-madrid-archetypes.csv  the 10 simulated cases (SAMPLE_FILE)
├── madrid_results_summary.py             results → summary CSV + charts
└── geometry/                             optional connected 3D models
project.yaml                              full-year run (used for the results)
project-test.yaml                         quick 1-week debug run
weather/                                  Madrid EPW/DDY + region mapping
local.py, building.py, preprocessing.py…  SimParc-R core (unchanged except local.py CSV fallback)
measures/                                 OpenStudio-HPXML measures (weather.rb patched)
results/                                  simulation outputs (git-ignored)
```

The Quebec sample CSVs, Quebec weather files and French documentation were removed.

## 5. How to reproduce

Prerequisites: `uv sync`, and OpenStudio 3.9.0 available through `OPENSTUDIO_EXE` or `PATH`.

```bash
# 1. (only if the spreadsheet or hypotheses change) regenerate the 10-case CSV
uv run --with openpyxl python madrid/gen_madrid_archetypes.py

# 2. run the 10 simulations (TMYx Madrid weather, Jan 1 – Dec 31, 15-min timestep)
uv run local.py project.yaml

# 3. summary table + charts
uv run python madrid/madrid_results_summary.py

# 4. (optional) connected 3D geometry per case
uv run python madrid/geometry/build_connected_osms.py --extract-exploded
```

Things to keep in mind:

- Keep the CSV **comma-delimited**. Excel under a Spanish or French locale re-saves it with `;`. `local.py` tolerates this, but the summary script does not.
- The summary script joins results to cases **by row order**, so it must use the same CSV as the run.
- If a case fails, check `results/<n>/openstudio_output.log` first, then `run.log` / `eplusout.err` inside `data_point.zip`.
