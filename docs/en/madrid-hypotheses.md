# Madrid: Simulation Hypotheses of the Ten Cases

This document lists every assumption behind the ten simulated Madrid dwellings. It starts with what differs between cases and then covers what is common to all of them. For each value it gives the source: **Sheet** means the C40 archetype spreadsheet (IDAE / ERESEE 2020 / CTE), and **Hyp.** means a modelling assumption made because the sheet does not provide the value.

The values below are those in `madrid/building-stock-madrid-archetypes.csv`, the file that was simulated. They are produced by `madrid/gen_madrid_archetypes.py`. For context and results, see [SimParc-R applied to Madrid: Summary](madrid-summary.md).

## 1. The ten cases

| Case | ID | Typology | Period (year modelled) | Modelled as |
|---|---|---|---|---|
| 1 | `MAD_SF_le1940` | Single-family | ≤1940 (1930) | 2-storey row house |
| 2 | `MAD_SF_1941_1960` | Single-family | 1941–1960 (1950) | 2-storey row house |
| 3 | `MAD_SF_1961_1980` | Single-family | 1961–1980 (1970) | 2-storey row house |
| 4 | `MAD_SF_1981_2007` | Single-family | 1981–2007 (1995) | 2-storey row house |
| 5 | `MAD_SF_2008_2011` | Single-family | 2008–2011 (2010) | 2-storey row house |
| 6 | `MAD_MF_le1940` | Multi-family block | ≤1940 (1930) | middle-floor apartment |
| 7 | `MAD_MF_1941_1960` | Multi-family block | 1941–1960 (1950) | middle-floor apartment |
| 8 | `MAD_MF_1961_1980` | Multi-family block | 1961–1980 (1970) | middle-floor apartment |
| 9 | `MAD_MF_1981_2007` | Multi-family block | 1981–2007 (1995) | middle-floor apartment |
| 10 | `MAD_MF_2008_2011` | Multi-family block | 2008–2011 (2010) | middle-floor apartment |

## 2. Parameters that vary between cases

| Case | Floor area (m²) | Storeys | Dwellings in building | U wall | U roof | U ground floor | U window | Airtightness (ACH50) | HRV sensible efficiency |
|---|---|---|---|---|---|---|---|---|---|
| 1 SF ≤1940 | 126.1 | 2 | 1 | 2.12 | 3.00 | 1.45 | 4.24 | 14 | none (0.02) |
| 2 SF 1941–60 | 105.1 | 2 | 1 | 2.12 | 2.47 | 1.45 | 4.24 | 9 | none (0.02) |
| 3 SF 1961–80 | 169.9 | 2 | 1 | 1.85 | 2.03 | 1.52 | 4.24 | 8 | none (0.02) |
| 4 SF 1981–2007 | 186.0 | 2 | 1 | 1.40 | 1.13 | 1.20 | 4.04 | 7 | none (0.02) |
| 5 SF 2008–11 | 194.8 | 2 | 1 | 0.83 | 0.47 | 1.39 | 3.37 | 6 | 0.40 |
| 6 MF ≤1940 | 87.0 | 1 | 24 | 1.94 | *(2.06)* | *(1.15)* | 4.24 | 13 | none (0.02) |
| 7 MF 1941–60 | 89.0 | 1 | 12 | 1.81 | *(1.74)* | *(1.14)* | 4.24 | 8 | none (0.02) |
| 8 MF 1961–80 | 91.3 | 1 | 28 | 1.68 | *(1.74)* | *(1.14)* | 4.24 | 7 | none (0.02) |
| 9 MF 1981–2007 | 102.6 | 1 | 12 | 1.40 | *(1.13)* | *(1.00)* | 4.04 | 6 | none (0.02) |
| 10 MF 2008–11 | 108.9 | 1 | 12 | 0.83 | *(0.47)* | *(1.39)* | 3.37 | 5 | 0.40 |

U-values are in W/m²K.

| Parameter | Source | Notes |
|---|---|---|
| Floor area | Sheet | "Madrid avg. dwelling floor area" (urban stock), not the national average |
| Storeys, dwellings in building | Sheet | SF: floors of the typical building. MF: OS-HPXML simulates one unit on one floor; *dwellings in building* = floors × dwellings per floor, for information only. |
| U-values | Sheet (ERESEE 2020, Table 7.9) | Converted to assembly R-values (R = 1/U) for walls and roof, IP units for windows. The ground-floor U is applied as full-width under-slab insulation. |
| *(Italic)* MF roof and floor | Sheet, **not active** | The apartment sits between two apartments (`AboveApartment` / `BelowApartment`), so its roof and floor are adiabatic and these U-values do not affect the results. |
| Airtightness | Hyp. (user-supplied) | Not in the sheet. Older buildings are assumed leakier; apartments get 1 ACH50 less than the house of the same period. Measured at 50 Pa on the unit's exterior envelope only. |
| HRV efficiency | Hyp. (user-supplied) | Only the 2008–2011 period is assumed to have effective heat recovery. HPXML requires a value above 0, so 0.02 stands for "no recovery". |

## 3. Hypotheses common to all ten cases

### 3.1 Geometry and typology

| Item | Value | Source |
|---|---|---|
| SF typology | Single-family **attached** (row house). Both side walls adiabatic, front and back exposed. | Hyp.: the sheet's large party-wall (*medianera*) areas point to terraced houses |
| SF foundation / roof | Slab on grade / flat roof | Hyp.: sheet mentions *solera*; flat roofs are typical in Madrid |
| MF typology | Apartment on an intermediate floor. Side walls adiabatic, front and back exposed, floor and ceiling adjacent to other dwellings. | Hyp.: a representative mid-floor unit |
| Ceiling height | 2.6 m | Hyp.: typical CTE value |
| Footprint aspect ratio | 2.0 (front/side) | Hyp.: OS-HPXML default |
| Orientation | Front façade facing east (90°) | Inherited template value |
| Wall construction | Structural brick | Hyp.: typical Madrid masonry |
| Window area | 13.5% of each exposed façade, all orientations | Sheet gives 13.5 m² of window per 100 m² of floor area. It is used directly as the window-to-wall ratio (approximation). |
| Window g-value (SHGC) | 0.75 | Hyp.: uncoated double glazing. The sheet flags "no public source". |
| Window interior shading | 0.70 in summer, 0.85 in winter (shading multipliers) | OS-HPXML defaults (curtains/blinds) |
| Operable windows | 67% of window area (natural ventilation allowed) | Template value |
| Overhangs, neighbouring buildings | None | Hyp.: no street-geometry data available |
| Doors | 1.86 m² (20 ft²), R = 0.88 m²K/W | Template value |
| Roof finish | Asphalt/fibreglass shingles, medium colour (solar absorptance) | Template value (US default, only affects the SF roof) |

### 3.2 Heating, cooling and ventilation

| Item | Value | Source |
|---|---|---|
| Heating system | Individual **natural-gas boiler**, 78% efficiency (AFUE), serves 100% of the heating load | Sheet (fuel: ~1.17 M individual gas connections in Madrid). Efficiency is Hyp. (OS-HPXML default). |
| Cooling system | **Room air conditioner**, EER 9.8 (COP ≈ 2.9), serves 100% of the cooling load | Hyp.: the sheet flags "no public source". Chosen over a mini-split because of a crash in the model's sizing code. |
| Heating setpoint | 20 °C from 07:00 to 23:00, 17 °C from 23:00 to 07:00, every day | Sheet (CTE DB-HE Annex D) |
| Heating season | 1 October – 31 May | Sheet (CTE) |
| Cooling setpoint | 25 °C from 15:00 to 23:00, 27 °C the rest of the day, every day | Sheet (CTE DB-HE Annex D) |
| Cooling season | 1 June – 30 September | Sheet (CTE) |
| Stochastic Quebec setpoint model | **Disabled** (`Heating Setpoint = False`) | Required for the CTE schedule to apply |
| System sizing | Automatic (OS-HPXML / ACCA method, from the Madrid design days) | Model default |
| Mechanical ventilation | Balanced HRV running 24 h/day, 15 W fan. SF: 34 l/s (72 cfm). MF: 28 l/s (60 cfm). | Hyp. based on the CTE DB-HS3 room rates in the sheet |
| Local extraction | Kitchen and bathroom spot fans (OS-HPXML default schedules) | Model default |
| Ceiling fan | 1 per dwelling | Template value |

### 3.3 Domestic hot water

| Item | Value | Source |
|---|---|---|
| Water heater | **Natural-gas storage tank**, energy factor 0.92, setpoint 51.7 °C (125 °F) | Template value (see open items) |
| Distribution | Standard (no recirculation), low-flow showers and taps, fixture use × 0.7 | Hyp. / template |
| Solar thermal, drain-water heat recovery | None | Hyp. |

### 3.4 Occupancy, appliances and lighting

The same in all ten cases, taken from the template row (`madrid/data/template-common-inputs.csv`).

| Item | Value |
|---|---|
| Occupants / bedrooms | 3 / 3 |
| Occupancy and appliance schedules | Stochastic OS-HPXML schedules (seed 100, reproducible) |
| Cooking | Electric range/oven (not induction), use × 0.8 |
| Laundry | Washer (IMEF 0.95) and **electric** dryer (CEF 2.7), use × 0.8 |
| Dishwasher | None |
| Refrigerator / freezer | 383 kWh/yr / separate freezer 935 kWh/yr rated × 0.342 |
| Television and plug loads | Present, OS-HPXML defaults |
| Lighting | Interior 70% LED + 30% linear fluorescent. Exterior CFL. |
| Not present | Gas grill, gas lighting, fireplace, well pump, holiday lighting, pool, spa, EV, PV, battery, dehumidifier, second heating system |

### 3.5 Weather and simulation settings

| Item | Value |
|---|---|
| Weather | TMYx Madrid-Barajas-Suárez airport (WMO 082210), typical year built from 2009–2023 (climate.onebuilding.org) |
| Design days | 99% heating / 1% cooling, from the companion `.ddy` file |
| Period, timestep | 1 January – 31 December (calendar year 2023), 15 minutes |
| Time | Local time from the EPW (UTC+1), daylight saving time enabled |
| Retrofit scenarios | None (baseline only) |

## 4. Known limitations and open items

- **Airtightness and ventilation** values are user-supplied assumptions. The sheet only gives room-level CTE ventilation rates.
- **Occupancy, DHW and appliances** are identical in the ten cases and come from the template row, not from Madrid statistics. This is why electricity per dwelling barely changes between cases.
- **DHW efficiency 0.92** is high for a gas storage tank (typically about 0.6). The tank is placed in a "multifamily buffer space" even for the row houses. Both should be reviewed; the second is probably closer to an individual combi boiler.
- **Window-to-floor ratio used as window-to-wall ratio**, and the g-value of 0.75 with no external shading. Cooling demand is sensitive to both.
- **Ground floor:** the U-value is applied as under-slab insulation, and the model adds the soil resistance on top, so ground losses of the SF cases are probably underestimated.
- **Apartments** represent a middle-floor unit only. Ground-floor and top-floor apartments, which have higher demand, are not simulated.
- Columns inherited from the Quebec template (`Tconsignes_chauffage_*`, `Piscine_*`, `Vehicule_*`, ResStock-style descriptive columns such as `Windows` or `Geometry Stories`) remain in the CSV. They are **not used** by the simulation.
