# -*- coding: utf-8 -*-
"""End-to-end driver: produce a connected-geometry OSM for every Madrid archetype.

The in.osm stored in each results/<n>/data_point.zip has already gone through
HPXMLtoOpenStudio's explode_surfaces(), so its walls are spread apart. Instead of
trying to stitch those back together, this re-runs only BuildResidentialHPXML
with the exact same arguments, which yields the connected envelope directly:

    1. prepare_geometry_args.py      -> results/geometry_args/<archetype>.json
    2. extract_geometry_osm.rb (x N) -> results/osm_connected/<archetype>.osm
    3. check_geometry_connectivity.py -> reports orphaned surfaces

Optionally (--extract-exploded) also unzips the simulated in.osm of each
building to results/osm_exploded/<archetype>.osm for side-by-side comparison.

Usage:
    uv run python madrid/geometry/build_connected_osms.py [--extract-exploded]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import check_geometry_connectivity
import prepare_geometry_args

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"
ARGS_DIR = RESULTS_DIR / "geometry_args"
CONNECTED_DIR = RESULTS_DIR / "osm_connected"
EXPLODED_DIR = RESULTS_DIR / "osm_exploded"
EXTRACT_SCRIPT = Path(__file__).resolve().parent / "extract_geometry_osm.rb"


def find_openstudio():
    """Same lookup order as local.py, plus the default Windows install dirs."""
    exe = os.environ.get("OPENSTUDIO_EXE", "").strip().strip('"')
    if exe:
        return exe
    exe = shutil.which("openstudio")
    if exe:
        return exe
    candidates = sorted(Path("C:/").glob("openstudio-*/bin/openstudio.exe"), reverse=True)
    if candidates:
        return str(candidates[0])
    sys.exit("OpenStudio not found. Set OPENSTUDIO_EXE or add OpenStudio bin to PATH.")


def building_dirs():
    return sorted(
        [p for p in RESULTS_DIR.iterdir() if p.is_dir() and p.name.isdigit()],
        key=lambda p: int(p.name),
    )


def archetype_id(building_dir):
    metadata_path = building_dir / f"{building_dir.name}_metadata.json"
    if not metadata_path.exists():
        return building_dir.name
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return metadata["non_hpxml_args"].get("Archetype_ID", building_dir.name)


def extract_exploded_osms():
    EXPLODED_DIR.mkdir(exist_ok=True)
    for building_dir in building_dirs():
        zip_path = building_dir / "data_point.zip"
        if not zip_path.exists():
            print(f"Skipping building {building_dir.name}: no data_point.zip")
            continue
        with zipfile.ZipFile(zip_path) as zf:
            if "in.osm" not in zf.namelist():
                print(f"Skipping building {building_dir.name}: no in.osm in zip")
                continue
            out_path = EXPLODED_DIR / f"{archetype_id(building_dir)}.osm"
            out_path.write_bytes(zf.read("in.osm"))
        print(f"Wrote {out_path}")


def build_connected_osms(openstudio_exe):
    CONNECTED_DIR.mkdir(exist_ok=True)
    failures = []
    for args_path in sorted(ARGS_DIR.glob("*.json")):
        out_path = CONNECTED_DIR / f"{args_path.stem}.osm"
        log_path = CONNECTED_DIR / f"{args_path.stem}.log"
        with open(log_path, "w", encoding="utf-8") as f_log:
            result = subprocess.run(
                [openstudio_exe, str(EXTRACT_SCRIPT), str(args_path), str(out_path)],
                cwd=PROJECT_ROOT, stdout=f_log, stderr=subprocess.STDOUT,
            )
        if result.returncode != 0 or not out_path.exists():
            failures.append(args_path.stem)
            print(f"FAILED {args_path.stem} (see {log_path})")
        else:
            print(f"Wrote {out_path}")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--extract-exploded", action="store_true",
                        help="also unzip each simulated in.osm to results/osm_exploded/")
    args = parser.parse_args()

    openstudio_exe = find_openstudio()
    print(f"Using OpenStudio: {openstudio_exe}")

    if args.extract_exploded:
        print("\n== Extracting simulated (exploded) OSMs ==")
        extract_exploded_osms()

    print("\n== Preparing BuildResidentialHPXML arguments ==")
    prepare_geometry_args.main()

    print("\n== Building connected-geometry OSMs ==")
    failures = build_connected_osms(openstudio_exe)

    print("\n== Checking connectivity ==")
    check_geometry_connectivity.main()

    if failures:
        sys.exit(f"\n{len(failures)} archetype(s) failed: {failures}")


if __name__ == "__main__":
    main()
