# -*- coding: utf-8 -*-
"""Generate 10 Madrid archetype rows (5 single-family attached + 5 apartment unit)
from data/C40_CleanHeat_Madrid_ThermalArchetypes_SIMPLIFIED.xlsx, using
data/template-common-inputs.csv as the base for every field the archetype sheet
does not inform (occupancy, appliances, DHW, ...).

All HPXML arguments that would otherwise silently fall back to the
BuildResidentialHPXML measure's own built-in defaults (many of which are
US-residential-survey conventions that don't apply to Madrid, e.g. a gas grill,
gas landscape lighting, or a well pump assumed present by default) are set
explicitly here instead, so the CSV is a complete, auditable record of every
assumption used for the Madrid case.

Usage (openpyxl is not a project dependency):
    uv run --with openpyxl python madrid/gen_madrid_archetypes.py
"""
from pathlib import Path

import pandas as pd
import numpy as np

MADRID_DIR = Path(__file__).resolve().parent
XLSX = MADRID_DIR / "data" / "C40_CleanHeat_Madrid_ThermalArchetypes_SIMPLIFIED.xlsx"
TEMPLATE_CSV = MADRID_DIR / "data" / "template-common-inputs.csv"
OUT_CSV = MADRID_DIR / "building-stock-madrid-archetypes.csv"

VINTAGES = ["<=1940", "1941-1960", "1961-1980", "1981-2007", "2008-2011"]

# Not in the archetype sheet: airtightness (ACH50) and mechanical ventilation
# assumptions per vintage (user-supplied).
SF_ACH50 = [14, 9, 8, 7, 6]
MF_ACH50 = [13, 8, 7, 6, 5]
SF_MECH_VENT_CFM = 72  # ~34 l/s
MF_MECH_VENT_CFM = 60  # ~28 l/s
# HRV sensible recovery: only the 2008-2011 vintage has effective heat recovery.
# HPXML requires a value > 0 for an HRV, so 0.02 stands for "no recovery".
HRV_SENSIBLE_EFF = [0.02, 0.02, 0.02, 0.02, 0.4]
M2_TO_FT2 = 10.76391
DELTAC_TO_DELTAF = 1.8


def r_ip(u_si):
    """Convert assembly U-value (W/m2K) to assembly R-value (h-ft2-F/Btu)."""
    return 5.678263337 / float(u_si)


def c_to_f(c):
    return float(c) * 9.0 / 5.0 + 32.0


def load_sheet(sheet):
    df = pd.read_excel(XLSX, sheet_name=sheet, header=None)

    def row(idx):
        return [df.iloc[idx, c] for c in range(3, 8)]

    return {
        "n_floors": row(4),
        "n_dw_fl": row(5),
        "A_dw_mad": row(7),
        "facade_win_pct": row(10),  # WWR proxy, % (m2/100m2 floor area)
        "medianera": row(11),
        "U_wall": row(17),
        "U_roof": row(18),
        "U_floor": row(19),
        "U_win": row(20),
    }


sf = load_sheet("Res-Uu Single-family dwelling")
mf = load_sheet("Res-Bb Multi-family block")

# 24h heating/cooling setpoint schedules per the archetype sheet (period-invariant)
# Heating: 17C 00:00-06:59 & 23:00-23:59 / 20C 07:00-22:59 (Oct-May)
heating_24h_f = [c_to_f(17) if (h <= 6 or h == 23) else c_to_f(20) for h in range(24)]
# Cooling: 25C 15:00-22:59 / 27C rest of day (Jun-Sep)
cooling_24h_f = [c_to_f(25) if 15 <= h <= 22 else c_to_f(27) for h in range(24)]
heating_sched = ",".join(f"{v:.1f}" for v in heating_24h_f)
cooling_sched = ",".join(f"{v:.1f}" for v in cooling_24h_f)

template = pd.read_csv(TEMPLATE_CSV)
base_row = template.iloc[0].to_dict()


def apply_common_hypotheses(row):
    """Set every HPXML-required argument that isn't informed by the archetype
    sheet, so nothing is left to the measure's own (US-centric) implicit
    defaults. Values chosen to reflect "no such feature present" for anything
    irrelevant to a Madrid dwelling, and the measure's own reasonable default
    otherwise.
    """
    # --- Misc fuel/plug loads: the measure defaults ALL of these to present=True
    # (gas grill, gas landscape lighting, gas fireplace, well pump) since it's
    # built around a US-suburban reference home. None of these apply to a Madrid
    # dwelling, so explicitly turn them off.
    row["misc_fuel_loads_grill_present"] = False
    row["misc_fuel_loads_grill_fuel_type"] = "natural gas"  # inert, present=False
    row["misc_fuel_loads_lighting_present"] = False
    row["misc_fuel_loads_lighting_fuel_type"] = "natural gas"  # inert, present=False
    row["misc_fuel_loads_fireplace_present"] = False
    row["misc_fuel_loads_fireplace_fuel_type"] = "natural gas"  # inert, present=False
    row["misc_plug_loads_well_pump_present"] = False
    row["holiday_lighting_present"] = False
    row["misc_plug_loads_television_present"] = True  # a TV is a normal assumption

    # --- CRITICAL: disable the Quebec-specific stochastic heating setpoint generator.
    # building.py checks non_hpxml_args['Heating Setpoint'] (truthy in the inherited
    # Quebec template row: "(23,23,23)") and, if truthy, generates a stochastic profile
    # from Tconsignes_chauffage_H1-H4 (Quebec occupant-behavior thresholds) that gets
    # injected as a schedule-file column -- which SILENTLY OVERRIDES the simple
    # hvac_control_heating_weekday/weekend_setpoint values below (confirmed in
    # HPXMLtoOpenStudio/resources/hvac.rb: "the latter will be ignored"), and also
    # overwrites hvac_control_cooling_weekday/weekend_setpoint with an unrelated
    # (stochastic heating max + 2F) value. Must be off for our explicit Madrid
    # schedule to actually take effect.
    row["Heating Setpoint"] = False

    # --- Second heating system / solar thermal / DWHR / pool heater: none present
    row["heating_system_2_type"] = "none"
    row["heating_system_2_fuel"] = "electricity"  # inert, type=none
    row["heating_system_2_heating_efficiency"] = 1.0  # inert, type=none
    row["heating_system_2_fraction_heat_load_served"] = 0.0
    row["solar_thermal_system_type"] = "none"
    row["solar_thermal_collector_area"] = 40.0  # inert, system_type=none
    row["solar_thermal_collector_loop_type"] = "liquid direct"
    row["solar_thermal_collector_type"] = "evacuated tube"
    row["solar_thermal_collector_azimuth"] = 180.0
    row["solar_thermal_collector_tilt"] = "RoofPitch"
    row["solar_thermal_collector_rated_optical_efficiency"] = 0.5
    row["solar_thermal_collector_rated_thermal_losses"] = 0.2799
    row["solar_thermal_solar_fraction"] = 0.0
    row["dwhr_facilities_connected"] = "none"
    row["pool_heater_type"] = "none"  # inert, pool_present already False

    # --- Single cooling/heating system explicitly serves 100% of the load
    row["cooling_system_fraction_cool_load_served"] = 1.0

    # --- DHW distribution / fixtures: standard (non-recirculating) distribution,
    # modern low-flow fixtures (reasonable regardless of envelope vintage, since
    # fixtures are typically replaced independently of the building shell)
    row["hot_water_distribution_system_type"] = "Standard"
    row["water_fixtures_shower_low_flow"] = True
    row["water_fixtures_sink_low_flow"] = True

    # --- Shading geometry: no overhangs, no adjacent-building shading modeled
    # (no Madrid-specific street-width/density data available to inform this)
    row["geometry_eaves_depth"] = 2.0  # ft, measure default
    for side in ["front", "back", "left", "right"]:
        row[f"neighbor_{side}_distance"] = 0.0
        row[f"overhangs_{side}_depth"] = 0.0
        row[f"overhangs_{side}_distance_to_top_of_window"] = 0.0
        row[f"overhangs_{side}_distance_to_bottom_of_window"] = 4.0

    return row


rows = []
for i, vintage in enumerate(VINTAGES):
    row = dict(base_row)
    row["Archetype_ID"] = f"MAD_SF_{vintage.replace('<=', 'le').replace('-', '_')}"
    row["geometry_unit_type"] = "single-family attached"
    row["heating_system_heating_efficiency"] = 0.78
    row["geometry_unit_num_floors_above_grade"] = int(sf["n_floors"][i])
    row["geometry_building_num_units"] = 1  # single-family: 1 unit per building
    row["geometry_unit_cfa"] = round(float(sf["A_dw_mad"][i]) * M2_TO_FT2, 1)
    row["geometry_average_ceiling_height"] = 8.53  # ~2.6m, CTE-typical (not in sheet)
    row["geometry_unit_aspect_ratio"] = 2.0  # not in sheet; OS-HPXML tool default
    row["geometry_foundation_type"] = "SlabOnGrade"
    row["geometry_attic_type"] = "FlatRoof"
    row["geometry_unit_left_wall_is_adiabatic"] = "true"
    row["geometry_unit_right_wall_is_adiabatic"] = "true"
    row["wall_type"] = "StructuralBrick"
    row["wall_assembly_r"] = round(r_ip(sf["U_wall"][i]), 2)
    row["roof_assembly_r"] = round(r_ip(sf["U_roof"][i]), 2)
    row["ceiling_assembly_r"] = round(r_ip(sf["U_roof"][i]), 2)  # FlatRoof: attic floor N/A, mirror roof
    row["slab_under_insulation_r"] = round(r_ip(sf["U_floor"][i]), 2)
    row["slab_under_insulation_width"] = 999  # >=999 ft signals full-slab coverage (measure.rb:5325)
    row["slab_perimeter_insulation_r"] = 0
    row["slab_perimeter_insulation_depth"] = 0
    row["window_ufactor"] = round(float(sf["U_win"][i]) * 0.1761, 3)  # W/m2K -> Btu/h-ft2-F
    row["window_shgc"] = 0.75
    wwr = round(float(sf["facade_win_pct"][i]) / 100.0, 4)
    for side in ["front", "back", "left", "right"]:
        row[f"window_{side}_wwr"] = wwr
    row["heating_system_type"] = "Boiler"
    row["heating_system_fuel"] = "natural gas"
    row["cooling_system_type"] = "room air conditioner"
    row["cooling_system_cooling_efficiency_type"] = "EER"
    row["cooling_system_cooling_efficiency"] = 9.8
    row["hvac_control_heating_weekday_setpoint"] = heating_sched
    row["hvac_control_heating_weekend_setpoint"] = heating_sched
    row["hvac_control_cooling_weekday_setpoint"] = cooling_sched
    row["hvac_control_cooling_weekend_setpoint"] = cooling_sched
    row["hvac_control_heating_season_period"] = "Oct 1 - May 31"
    row["hvac_control_cooling_season_period"] = "Jun 1 - Sep 30"
    row["year_built"] = {"<=1940": 1930, "1941-1960": 1950, "1961-1980": 1970,
                          "1981-2007": 1995, "2008-2011": 2010}[vintage]
    row["Region_Administrative"] = "Madrid"
    row["Territoire_HQ"] = "Madrid"
    row["site_time_zone_utc_offset"] = np.nan
    row["air_leakage_value"] = SF_ACH50[i]
    row["Infiltration"] = f"{SF_ACH50[i]} ACH50"  # descriptive only, kept consistent
    row["mech_vent_flow_rate"] = SF_MECH_VENT_CFM
    row["mech_vent_sensible_recovery_efficiency"] = HRV_SENSIBLE_EFF[i]
    row["mech_vent_total_recovery_efficiency"] = HRV_SENSIBLE_EFF[i]
    row = apply_common_hypotheses(row)
    rows.append(row)

for i, vintage in enumerate(VINTAGES):
    row = dict(base_row)
    row["Archetype_ID"] = f"MAD_MF_{vintage.replace('<=', 'le').replace('-', '_')}"
    row["geometry_unit_type"] = "apartment unit"
    row["heating_system_heating_efficiency"] = 0.78
    row["geometry_unit_num_floors_above_grade"] = 1  # OS-HPXML: 1 simulated unit, forced to 1 floor
    row["geometry_building_num_units"] = int(mf["n_floors"][i]) * int(mf["n_dw_fl"][i])
    row["geometry_unit_cfa"] = round(float(mf["A_dw_mad"][i]) * M2_TO_FT2, 1)
    row["geometry_average_ceiling_height"] = 8.53
    row["geometry_unit_aspect_ratio"] = 2.0
    row["geometry_foundation_type"] = "AboveApartment"  # middle-floor representative unit
    row["geometry_attic_type"] = "BelowApartment"
    row["geometry_unit_left_wall_is_adiabatic"] = "true"
    row["geometry_unit_right_wall_is_adiabatic"] = "true"
    row["wall_type"] = "StructuralBrick"
    row["wall_assembly_r"] = round(r_ip(mf["U_wall"][i]), 2)
    row["roof_assembly_r"] = round(r_ip(mf["U_roof"][i]), 2)
    row["ceiling_assembly_r"] = round(r_ip(mf["U_roof"][i]), 2)
    row["slab_under_insulation_r"] = round(r_ip(mf["U_floor"][i]), 2)
    row["slab_under_insulation_width"] = 999
    row["slab_perimeter_insulation_r"] = 0
    row["slab_perimeter_insulation_depth"] = 0
    row["window_ufactor"] = round(float(mf["U_win"][i]) * 0.1761, 3)
    row["window_shgc"] = 0.75
    wwr = round(float(mf["facade_win_pct"][i]) / 100.0, 4)
    for side in ["front", "back", "left", "right"]:
        row[f"window_{side}_wwr"] = wwr
    row["heating_system_type"] = "Boiler"
    row["heating_system_fuel"] = "natural gas"
    row["cooling_system_type"] = "room air conditioner"
    row["cooling_system_cooling_efficiency_type"] = "EER"
    row["cooling_system_cooling_efficiency"] = 9.8
    row["hvac_control_heating_weekday_setpoint"] = heating_sched
    row["hvac_control_heating_weekend_setpoint"] = heating_sched
    row["hvac_control_cooling_weekday_setpoint"] = cooling_sched
    row["hvac_control_cooling_weekend_setpoint"] = cooling_sched
    row["hvac_control_heating_season_period"] = "Oct 1 - May 31"
    row["hvac_control_cooling_season_period"] = "Jun 1 - Sep 30"
    row["year_built"] = {"<=1940": 1930, "1941-1960": 1950, "1961-1980": 1970,
                          "1981-2007": 1995, "2008-2011": 2010}[vintage]
    row["Region_Administrative"] = "Madrid"
    row["Territoire_HQ"] = "Madrid"
    row["site_time_zone_utc_offset"] = np.nan
    row["air_leakage_value"] = MF_ACH50[i]
    row["Infiltration"] = f"{MF_ACH50[i]} ACH50"  # descriptive only, kept consistent
    row["mech_vent_flow_rate"] = MF_MECH_VENT_CFM
    row["mech_vent_sensible_recovery_efficiency"] = HRV_SENSIBLE_EFF[i]
    row["mech_vent_total_recovery_efficiency"] = HRV_SENSIBLE_EFF[i]
    row = apply_common_hypotheses(row)
    rows.append(row)

out_df = pd.DataFrame(rows)
out_df.to_csv(OUT_CSV, index=False)
print("Wrote", OUT_CSV, out_df.shape)
print(out_df[["Archetype_ID", "geometry_unit_type", "geometry_unit_cfa", "wall_assembly_r",
              "roof_assembly_r", "slab_under_insulation_r", "slab_under_insulation_width",
              "window_ufactor", "window_front_wwr", "geometry_building_num_units"]].to_string())
