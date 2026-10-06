# -*- coding: utf-8 -*-
"""Reconstruct the exact BuildResidentialHPXML argument set used for each Madrid
archetype (from results/<n>/<n>_metadata.json, filling back in the 4 fields that
local.py injects at runtime after that metadata was written), so it can be fed
to a standalone Ruby script that runs *just* BuildResidentialHPXML and saves the
resulting connected OpenStudio model (geometry envelope, before HPXMLtoOpenStudio's
explode_surfaces() spreads walls apart for shading-safe simulation).

Usage:
    uv run python madrid/geometry/prepare_geometry_args.py
"""
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))  # hpxml_input_schema lives at the repo root

from hpxml_input_schema import extract_arguments_from_xml
RESULTS_DIR = PROJECT_ROOT / "results"
OUT_DIR = PROJECT_ROOT / "results" / "geometry_args"
PROJECT_YAML = PROJECT_ROOT / "project.yaml"


def get_cfg():
    with open(PROJECT_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_weather_epw_path(cfg, region):
    with open(PROJECT_ROOT / "weather" / "mapping" / "Mapping-Region-EPWfiles.json",
              "r", encoding="utf-8") as f:
        mapping = json.load(f)
    return str(PROJECT_ROOT / "weather" /
               mapping[cfg["WEATHER_FILE_TYPE"]][str(cfg["SIMULATION_YEAR"])][region])


def main():
    cfg = get_cfg()
    OUT_DIR.mkdir(exist_ok=True)

    # Args required by the measure but not present in our sample CSV rely on the
    # OSW runner's own default-value fallback in the real batch run. apply_measures
    # (used by extract_geometry_osm.rb) is stricter and requires every required
    # arg to be explicitly present, so backfill any gaps with the measure's own
    # declared default value -- exactly what the real run implicitly used.
    args_constraints = extract_arguments_from_xml(
        PROJECT_ROOT / cfg["HPXML_SCHEMA_FILE"])

    building_dirs = sorted(
        [p for p in RESULTS_DIR.iterdir() if p.is_dir() and p.name.isdigit()],
        key=lambda p: int(p.name),
    )

    for building_dir in building_dirs:
        n = building_dir.name
        metadata_path = building_dir / f"{n}_metadata.json"
        if not metadata_path.exists():
            print(f"Skipping building {n}: no metadata json found")
            continue

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        hpxml_args = dict(metadata["hpxml_args"])
        non_hpxml_args = metadata["non_hpxml_args"]

        for arg_name, spec in args_constraints.items():
            if not spec.get("Required"):
                continue
            if arg_name in hpxml_args:
                continue
            default = spec.get("Default Value")
            if default is None or (isinstance(default, float) and default != default):  # NaN check
                continue
            hpxml_args[arg_name] = default

        # Re-inject the 4 fields local.py normally adds after metadata is written
        hpxml_args["hpxml_path"] = str(building_dir / "built.xml")
        hpxml_args["weather_station_epw_filepath"] = get_weather_epw_path(
            cfg, non_hpxml_args["Region_Administrative"])
        hpxml_args["simulation_control_timestep"] = cfg["SIMULATION_TIMESTEP"]
        hpxml_args["simulation_control_run_period"] = cfg["SIMULATION_RUN_PERIOD"]

        archetype_id = non_hpxml_args.get("Archetype_ID", n)
        out_path = OUT_DIR / f"{archetype_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(hpxml_args, f)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
