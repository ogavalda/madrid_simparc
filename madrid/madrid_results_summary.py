# -*- coding: utf-8 -*-
"""Build a global summary table and demand charts (heating, cooling, domestic hot
water, natural gas, electricity, and electricity by end use) for the Madrid
archetype batch (results/results_job0.json.gz), joined back to
the archetype names from the input building-stock CSV by row position
(row i in the CSV == building_id i+1 in the results).

Usage:
    uv run python madrid/madrid_results_summary.py
"""
import gzip
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_JSON = PROJECT_ROOT / "results" / "results_job0.json.gz"
ARCHETYPES_CSV = PROJECT_ROOT / "madrid" / "building-stock-madrid-archetypes.csv"
OUT_DIR = PROJECT_ROOT / "results"
OUT_CSV = OUT_DIR / "madrid_results_summary.csv"
OUT_HTML = OUT_DIR / "madrid_demand_charts.html"

MBTU_TO_KWH = 293.0711
FT2_TO_M2 = 10.76391

# Okabe-Ito colorblind-safe categorical palette (fixed assignment, never cycled)
COLOR_SF = "#E69F00"  # orange
COLOR_MF = "#56B4E9"  # sky blue

# Electricity end uses (OS-HPXML "end_use_electricity_<name>") folded into at most
# 8 chart groups, so each group gets a fixed categorical slot. Every individual
# end use is still written to the CSV as elec_<name>_kwh; anything not listed
# here (heating fans/pumps, mech vent, ceiling fan, dishwasher, ...) goes to "Other".
ELEC_GROUPS = [
    ("Cooling", ["cooling", "cooling_fans_pumps"]),
    ("Hot water", ["hot_water", "hot_water_recirc_pump", "hot_water_solar_thermal_pump"]),
    ("Lighting", ["lighting_interior", "lighting_exterior", "lighting_garage"]),
    ("Refrigeration", ["refrigerator", "freezer"]),
    ("Laundry", ["clothes_washer", "clothes_dryer"]),
    ("Cooking", ["range_oven"]),
    ("TV & plug loads", ["television", "plug_loads"]),
    ("Other", None),
]
# Validated categorical palette (dataviz reference instance), fixed slot order
ELEC_GROUP_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                     "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
FUELS = ["electricity", "natural_gas", "fuel_oil", "propane", "wood_cord", "wood_pellets", "coal"]


def group_col(group):
    """CSV column name for an electricity chart group, e.g. 'TV & plug loads' -> elec_group_tv_plug_loads_kwh."""
    slug = "".join(ch if ch.isalnum() else "_" for ch in group.lower())
    return "elec_group_" + "_".join(filter(None, slug.split("_"))) + "_kwh"


def load_summary():
    with gzip.open(RESULTS_JSON, "rt") as f:
        records = json.load(f)
    df_results = pd.DataFrame(records)

    df_arch = pd.read_csv(ARCHETYPES_CSV)
    if len(df_arch) != len(df_results):
        raise ValueError(
            f"Row count mismatch: {len(df_arch)} archetypes vs {len(df_results)} results. "
            "Row-position join assumes the same building-stock CSV was used for the run."
        )

    df = pd.DataFrame({
        "building_id": range(1, len(df_results) + 1),
        "archetype_id": df_arch["Archetype_ID"].values,
        "cfa_m2": df_arch["geometry_unit_cfa"].values / FT2_TO_M2,
        "geometry_unit_type": df_arch["geometry_unit_type"].values,
        "geometry_building_num_units": df_arch["geometry_building_num_units"].values,
    })
    # building_type: read from the real HPXML field, not parsed from our own label
    unit_type_map = {"single-family attached": "SF", "single-family detached": "SF",
                      "apartment unit": "MF", "manufactured home": "SF"}
    df["building_type"] = df["geometry_unit_type"].map(unit_type_map)
    # vintage: no HPXML field carries this label directly (year_built is the closest,
    # but only as a single representative year) -- kept derived from our own archetype
    # naming convention, which is fine since it's a display label, not a modeling input
    df["vintage"] = df["archetype_id"].str.replace(r"MAD_(SF|MF)_", "", regex=True) \
        .str.replace("le1940", "<=1940").str.replace("_", "-")

    def kwh(col):
        return pd.to_numeric(df_results[f"ReportSimulationOutput.{col}"], errors="coerce") * MBTU_TO_KWH

    df["heating_demand_kwh"] = kwh("load_heating_delivered_m_btu")
    df["cooling_demand_kwh"] = kwh("load_cooling_delivered_m_btu")
    df["electricity_total_kwh"] = kwh("fuel_use_electricity_total_m_btu")
    df["natural_gas_total_kwh"] = kwh("fuel_use_natural_gas_total_m_btu")
    df["total_energy_kwh"] = kwh("energy_use_total_m_btu")

    # Domestic hot water: delivered load (the "demand") and energy consumed by fuel
    df["dhw_demand_kwh"] = kwh("load_hot_water_delivered_m_btu")
    df["dhw_tank_losses_kwh"] = kwh("load_hot_water_tank_losses_m_btu")
    dhw_by_fuel = {fuel: kwh(f"end_use_{fuel}_hot_water_m_btu") for fuel in FUELS}
    df["dhw_electricity_kwh"] = dhw_by_fuel["electricity"]
    df["dhw_natural_gas_kwh"] = dhw_by_fuel["natural_gas"]
    df["dhw_energy_kwh"] = sum(dhw_by_fuel.values())

    # Natural gas by end use
    df["natural_gas_heating_kwh"] = kwh("end_use_natural_gas_heating_m_btu")
    df["natural_gas_hot_water_kwh"] = df["dhw_natural_gas_kwh"]
    df["natural_gas_other_kwh"] = (df["natural_gas_total_kwh"] - df["natural_gas_heating_kwh"]
                                   - df["natural_gas_hot_water_kwh"])

    # Electricity by individual end use (only the ones that are non-zero somewhere)
    prefix = "ReportSimulationOutput.end_use_electricity_"
    elec_end_uses = [c[len(prefix):-len("_m_btu")] for c in df_results.columns
                     if c.startswith(prefix) and c.endswith("_m_btu")]
    elec_cols = []
    for end_use in elec_end_uses:
        values = kwh(f"end_use_electricity_{end_use}_m_btu").fillna(0.0)
        if (values.abs() > 0.5).any():
            df[f"elec_{end_use}_kwh"] = values
            elec_cols.append(end_use)

    # Electricity by chart group; "Other" = everything not explicitly grouped
    grouped = set()
    for group, end_uses in ELEC_GROUPS:
        if end_uses is None:
            continue
        present = [e for e in end_uses if e in elec_cols]
        grouped.update(present)
        df[group_col(group)] = df[[f"elec_{e}_kwh" for e in present]].sum(axis=1) if present else 0.0
    others = [e for e in elec_cols if e not in grouped]
    df[group_col("Other")] = df[[f"elec_{e}_kwh" for e in others]].sum(axis=1) if others else 0.0
    group_sum = df[[group_col(g) for g, _ in ELEC_GROUPS]].sum(axis=1)
    mismatch = (group_sum - df["electricity_total_kwh"]).abs().max()
    if mismatch > 1.0:
        print(f"WARNING: electricity end uses differ from total by up to {mismatch:.1f} kWh")

    per_m2_cols = ["heating_demand_kwh", "cooling_demand_kwh", "electricity_total_kwh",
                   "natural_gas_total_kwh", "total_energy_kwh", "dhw_demand_kwh",
                   "dhw_energy_kwh", "natural_gas_heating_kwh", "natural_gas_hot_water_kwh"]
    per_m2_cols += [group_col(g) for g, _ in ELEC_GROUPS]
    for col in per_m2_cols:
        df[col.replace("_kwh", "_kwh_m2")] = df[col] / df["cfa_m2"]
    df["peak_electricity_summer_w"] = pd.to_numeric(
        df_results["ReportSimulationOutput.peak_electricity_summer_total_w"], errors="coerce")
    df["peak_electricity_winter_w"] = pd.to_numeric(
        df_results["ReportSimulationOutput.peak_electricity_winter_total_w"], errors="coerce")
    df["status"] = df_results["ReportSimulationOutput.applicable"] if \
        "ReportSimulationOutput.applicable" in df_results.columns else None

    # vintage sort order (chronological, not alphabetical)
    vintage_order = ["<=1940", "1941-1960", "1961-1980", "1981-2007", "2008-2011"]
    df["vintage"] = pd.Categorical(df["vintage"], categories=vintage_order, ordered=True)
    df = df.sort_values(["building_type", "vintage"]).reset_index(drop=True)
    return df


def make_charts(df):
    row_labels = ["Heating demand (delivered load)", "Cooling demand (delivered load)",
                  "Domestic hot water demand (delivered load)",
                  "Total natural gas consumption", "Total electricity consumption"]
    col_labels = ["Absolute (kWh/yr)", "Per floor area (kWh/m²/yr)"]
    titles = [f"{r} — {c}" for r in row_labels for c in col_labels]

    metrics = ["heating_demand_kwh", "cooling_demand_kwh", "dhw_demand_kwh",
               "natural_gas_total_kwh", "electricity_total_kwh"]
    fig = make_subplots(
        rows=len(metrics), cols=2,
        subplot_titles=titles,
        vertical_spacing=0.05,
        horizontal_spacing=0.10,
    )

    for row, metric in enumerate(metrics, start=1):
        for col, (suffix, y_title) in enumerate(
                [("_kwh", "kWh/yr"), ("_kwh_m2", "kWh/m²/yr")], start=1):
            col_name = metric.replace("_kwh", suffix)
            for btype, color, name in [("SF", COLOR_SF, "Single-family attached"),
                                        ("MF", COLOR_MF, "Apartment unit")]:
                sub = df[df["building_type"] == btype]
                fig.add_trace(
                    go.Bar(
                        x=sub["vintage"].astype(str),
                        y=sub[col_name],
                        name=name,
                        marker_color=color,
                        legendgroup=name,
                        showlegend=(row == 1 and col == 1),
                        text=sub[col_name].round(1),
                        texttemplate="%{text:,.0f}",
                        textposition="outside",
                        hovertemplate=f"{name}<br>Vintage: %{{x}}<br>%{{y:,.1f}} {y_title}<extra></extra>",
                    ),
                    row=row, col=col,
                )
            fig.update_yaxes(title_text=y_title, gridcolor="#e5e5e5", row=row, col=col)
            fig.update_xaxes(title_text="Construction vintage" if row == len(metrics) else None,
                              gridcolor="#e5e5e5", row=row, col=col)

    fig.update_layout(
        barmode="group",
        title="Madrid archetypes — annual heating, cooling, hot water, gas and electricity",
        height=1900,
        width=1300,
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
        font=dict(size=12),
    )
    return fig


def make_electricity_breakdown_chart(df):
    """Stacked electricity consumption by end-use group, per dwelling and per m²."""
    type_labels = {"SF": "Single-family attached", "MF": "Apartment unit"}
    x = [df["building_type"].map(type_labels).tolist(), df["vintage"].astype(str).tolist()]

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.08,
                        subplot_titles=["Per dwelling (kWh/yr)", "Per floor area (kWh/m²/yr)"])
    for col, (suffix, unit) in enumerate([("_kwh", "kWh/yr"), ("_kwh_m2", "kWh/m²/yr")], start=1):
        for (group, _), color in zip(ELEC_GROUPS, ELEC_GROUP_COLORS):
            values = df[group_col(group).replace("_kwh", suffix)]
            share = values / df["electricity_total" + suffix] * 100
            fig.add_trace(
                go.Bar(
                    x=x, y=values, name=group, marker_color=color,
                    marker_line=dict(color="white", width=2),
                    legendgroup=group, showlegend=(col == 1),
                    customdata=share,
                    hovertemplate=(f"{group}<br>%{{x}}<br>%{{y:,.1f}} {unit}"
                                   "<br>%{customdata:.0f}% of electricity<extra></extra>"),
                ),
                row=1, col=col,
            )
        # total on top of each stack
        fig.add_trace(
            go.Scatter(
                x=x, y=df["electricity_total" + suffix], mode="text",
                text=df["electricity_total" + suffix].map("{:,.0f}".format),
                textposition="top center", textfont=dict(color="#52514e"),
                showlegend=False, hoverinfo="skip",
            ),
            row=1, col=col,
        )
        fig.update_yaxes(title_text=unit, gridcolor="#e5e5e5", row=1, col=col)

    fig.update_layout(
        barmode="stack",
        title="Madrid archetypes — electricity consumption by end use",
        height=650,
        width=1300,
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1,
                    traceorder="normal"),
        font=dict(size=12),
    )
    return fig


def main():
    df = load_summary()
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote summary table: {OUT_CSV}  ({len(df)} rows)")
    print(df[["archetype_id", "building_type", "geometry_building_num_units", "vintage",
              "cfa_m2", "heating_demand_kwh_m2", "cooling_demand_kwh_m2",
              "electricity_total_kwh_m2", "dhw_demand_kwh", "natural_gas_total_kwh"]]
          .round(1).to_string(index=False))
    print("\nElectricity by end-use group (kWh/yr):")
    print(df[["archetype_id"] + [group_col(g) for g, _ in ELEC_GROUPS] + ["electricity_total_kwh"]]
          .rename(columns={group_col(g): g for g, _ in ELEC_GROUPS})
          .round(0).to_string(index=False))

    fig = make_charts(df)
    fig_elec = make_electricity_breakdown_chart(df)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'><title>Madrid archetype results</title></head><body>")
        f.write(fig.to_html(full_html=False, include_plotlyjs=True))
        f.write(fig_elec.to_html(full_html=False, include_plotlyjs=False))
        f.write("</body></html>")
    print(f"Wrote interactive charts: {OUT_HTML}")


if __name__ == "__main__":
    main()
