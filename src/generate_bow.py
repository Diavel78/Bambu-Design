#!/usr/bin/env python3
"""
Generate a multi-color cheer-bow charm from a traced bow image, with a
printed snap clip.

Bow shape is traced from assets/cheer_bow_source.png (see trace_bow.py):
white loop faces, red center knot + red text, black tails/trim.

Layout:
  LEFT loop  : gym name  (default "Sonics", blackletter)
  RIGHT loop : team name (default "XOXO") over athlete name (default "Eden")

Change the name fast:
    python3 generate_bow.py --name Eden
    python3 generate_bow.py --name Harper --team XOXO --gym Sonics
"""

import os
import math
import argparse
import cadquery as cq
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import scale as sscale, translate as stranslate
from shapely.ops import unary_union

import generate_sonics_charm as g     # text_to_polygon, extrude, COLORS
import trace_bow

HERE = os.path.dirname(__file__)
FONT_BLACK = os.path.join(HERE, "..", "fonts", "UnifrakturCook-Bold.ttf")
FONT_NAME  = os.path.join(HERE, "..", "fonts", "DejaVuSans-Bold.ttf")
IMG        = os.path.join(HERE, "..", "assets", "cheer_bow_source.png")

# --------------------------------------------------------------------------- #
# CONFIG (mm)
# --------------------------------------------------------------------------- #
TARGET_W    = 95.0
TRIM        = 2.2     # black border around the white/red faces
PLATE_H     = 2.6
WHITE_RAISE = 0.8
TEXT_RAISE  = 1.2
BRIDGE      = 1.8     # close the thin gaps between traced pieces -> one plate

# carabiner snap clip + stem
CLIP_ROUT   = 9.5
CLIP_RIN    = 5.8
CLIP_GATE_W = 1.8
CLIP_GAP_A  = (58.0, 122.0)
CLIP_GATE_A = (54.0, 120.0)
STEM_W      = 6.5

COLORS = g.COLORS


# --------------------------------------------------------------------------- #
def round_poly(poly, r):
    return poly.buffer(r, join_style=1).buffer(-r, join_style=1)


def fit_text(text, font_path, target_w, max_h=None):
    raw = g.text_to_polygon(text, font_path)
    minx, miny, maxx, maxy = raw.bounds
    s = target_w / (maxx - minx)
    if max_h and (maxy - miny) * s > max_h:
        s = max_h / (maxy - miny)
    p = sscale(raw, xfact=s, yfact=s, origin=(0, 0))
    minx, miny, maxx, maxy = p.bounds
    return stranslate(p, -(minx + maxx) / 2.0, -(miny + maxy) / 2.0)


def carabiner():
    ring = Point(0, 0).buffer(CLIP_ROUT).difference(Point(0, 0).buffer(CLIP_RIN))
    a0, a1 = map(math.radians, CLIP_GAP_A)
    wedge = Polygon([(0, 0)] +
                    [(math.cos(a0 + (a1 - a0) * t / 24) * (CLIP_ROUT + 1),
                      math.sin(a0 + (a1 - a0) * t / 24) * (CLIP_ROUT + 1))
                     for t in range(25)])
    ring = ring.difference(wedge)
    rg = (CLIP_ROUT + CLIP_RIN) / 2
    g0, g1 = map(math.radians, CLIP_GATE_A)
    arc = LineString([(math.cos(g0 + (g1 - g0) * t / 40) * rg,
                       math.sin(g0 + (g1 - g0) * t / 40) * rg) for t in range(41)])
    gate = arc.buffer(CLIP_GATE_W / 2, cap_style=1)
    return unary_union([ring, gate])


# --------------------------------------------------------------------------- #
def build(name, team, gym):
    parts = trace_bow.trace(IMG, TARGET_W)
    loop_l, loop_r = parts["loop_l"], parts["loop_r"]
    knot = parts["knot"]
    pieces = [loop_l, loop_r, knot, parts["tail_l"], parts["tail_r"]]

    # one solid black plate (bridge the thin separators between pieces)
    plate_poly = unary_union(pieces).buffer(BRIDGE).buffer(-BRIDGE + 0.2)

    # ---- text -------------------------------------------------------------
    lc, rc = loop_l.centroid, loop_r.centroid
    tw = (loop_r.bounds[2] - loop_r.bounds[0]) * 0.62
    t_sonics = stranslate(fit_text(gym, FONT_BLACK, tw, max_h=15), lc.x, lc.y + 1)
    t_team   = stranslate(fit_text(team, FONT_NAME, tw * 0.78, max_h=9),
                          rc.x, rc.y + 8)
    t_name   = stranslate(fit_text(name, FONT_NAME, tw, max_h=11),
                          rc.x, rc.y - 7)
    text_all = unary_union([t_sonics, t_team, t_name])

    # red = knot face + text;  white = loop faces minus the red moat
    knot_face = knot.buffer(-TRIM)
    red_all = unary_union([text_all, knot_face])
    panel = unary_union([loop_l.buffer(-TRIM), loop_r.buffer(-TRIM)])
    white_all = panel.difference(text_all.buffer(0.7)).difference(knot.buffer(0.6))

    plate = g.extrude(plate_poly, 0.0,     PLATE_H)
    white = g.extrude(white_all,  PLATE_H, WHITE_RAISE)
    red   = g.extrude(red_all,    PLATE_H, TEXT_RAISE)

    bodies = {"plate": plate, "outline": white, "text": red}
    polys  = {"plate": plate_poly, "outline": white_all, "text": red_all}
    return bodies, polys


def export(name, bodies):
    folder = f"bow_{name.lower()}"
    d = os.path.join(HERE, "..", "models", folder)
    os.makedirs(d, exist_ok=True)
    for color, body in bodies.items():
        cq.exporters.export(cq.Workplane(obj=body), os.path.join(d, f"{folder}_{color}.stl"))
    combined = bodies["plate"].fuse(bodies["outline"]).fuse(bodies["text"])
    cq.exporters.export(cq.Workplane(obj=combined), os.path.join(d, f"{folder}_combined.stl"))
    cq.exporters.export(cq.Workplane(obj=combined), os.path.join(d, f"{folder}.step"))
    print(f"  exported -> models/{folder}/")


def render(name, polys):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    import numpy as np

    def patch(ax, geom, color, z):
        gs = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in gs:
            if p.is_empty:
                continue
            verts, codes = [], []
            for ring in [p.exterior, *p.interiors]:
                c = np.asarray(ring.coords)
                verts.extend(c); codes.extend([Path.MOVETO] + [Path.LINETO]*(len(c)-2) + [Path.CLOSEPOLY])
            ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor="none", zorder=z))

    fig, ax = plt.subplots(figsize=(6, 6))
    patch(ax, polys["plate"],   COLORS["plate"],   1)
    patch(ax, polys["outline"], COLORS["outline"], 2)
    patch(ax, polys["text"],    COLORS["text"],    3)
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off"); ax.margins(0.04)
    out = os.path.join(HERE, "..", "renders", f"bow_{name.lower()}.png")
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="#bfbfbf")
    plt.close(fig)
    print(f"  preview  -> renders/bow_{name.lower()}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="Eden")
    ap.add_argument("--team", default="XOXO")
    ap.add_argument("--gym",  default="Sonics")
    a = ap.parse_args()
    print(f"[bow] gym={a.gym} team={a.team} name={a.name}")
    bodies, polys = build(a.name, a.team, a.gym)
    export(a.name, bodies)
    render(a.name, polys)


if __name__ == "__main__":
    main()
