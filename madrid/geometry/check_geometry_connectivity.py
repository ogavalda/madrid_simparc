# -*- coding: utf-8 -*-
"""Sanity-check that each connected-geometry OSM is a closed, edge-matched
shell: every wall/roof/floor surface should share at least one full edge
(two coincident vertices) with another surface in the same space.
"""
import re
from pathlib import Path

OSM_DIR = Path(__file__).resolve().parents[2] / "results" / "osm_connected"


def round_pt(pt, ndigits=4):
    return tuple(round(float(x), ndigits) for x in pt)


def parse_surfaces(text):
    blocks = re.findall(r"OS:Surface,.*?(?=\n\nOS:|\Z)", text, re.S)
    surfaces = []
    for b in blocks:
        name_m = re.search(r"Handle\n\s*[^,]+,\s*!- Name\n?", b)
        name_m = re.search(r"!- Handle\n\s*([^,]+),\s*!- Name", b)
        name = name_m.group(1).strip() if name_m else "?"
        verts = re.findall(
            r"(-?\d+\.?\d*(?:[eE][+-]?\d+)?), (-?\d+\.?\d*(?:[eE][+-]?\d+)?), "
            r"(-?\d+\.?\d*(?:[eE][+-]?\d+)?)[,;]? +!- X,Y,Z Vertex", b)
        points = [round_pt(v) for v in verts]
        edges = set()
        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            edges.add(frozenset([p1, p2]))
        surfaces.append({"name": name, "points": points, "edges": edges})
    return surfaces


def check_file(path):
    text = path.read_text(encoding="utf-8")
    surfaces = parse_surfaces(text)
    n = len(surfaces)
    orphans = []
    for i, s in enumerate(surfaces):
        matched = False
        for j, other in enumerate(surfaces):
            if i == j:
                continue
            if s["edges"] & other["edges"]:
                matched = True
                break
        if not matched:
            orphans.append(s["name"])
    return n, orphans


def main():
    for osm_path in sorted(OSM_DIR.glob("*.osm")):
        n, orphans = check_file(osm_path)
        status = "OK - fully connected" if not orphans else f"ORPHANED: {orphans}"
        print(f"{osm_path.stem:20s} {n:2d} surfaces  ->  {status}")


if __name__ == "__main__":
    main()
