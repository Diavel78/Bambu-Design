#!/usr/bin/env python3
"""
Generate a multi-color cheer-bow charm with a printed snap clip.

Layout:
  LEFT loop  : gym name      (default "Sonics", blackletter)
  RIGHT loop : team name     (default "XOXO")  over  athlete name (default "Eden")
Colors: white ribbon faces, red text, black trim/outline/knot/tails.
Attachment: a flat, fully-printed carabiner-style snap clip at the top.

Change the name fast:
    python3 generate_bow.py --name Eden
    python3 generate_bow.py --name Harper --team XOXO --gym Sonics
Outputs go to ../models/bow_<name>/ and a preview to ../renders/.

Everything is parametric -- tweak CONFIG and re-run.
"""

import os
import math
import argparse
import cadquery as cq
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import scale as sscale, translate as stranslate, rotate as srot
from shapely.ops import unary_union

import generate_sonics_charm as g  # reuse text_to_polygon, extrude, COLORS

HERE = os.path.dirname(__file__)
FONT_BLACK = os.path.join(HERE, "..", "fonts", "UnifrakturCook-Bold.ttf")
FONT_NAME  = os.path.join(HERE, "..", "fonts", "DejaVuSans-Bold.ttf")

# --------------------------------------------------------------------------- #
# CONFIG (mm)
# --------------------------------------------------------------------------- #
BOW_W      = 90.0     # overall bow width target

KNOT_W     = 15.0     # center knot width
LOOP_OUT_H = 52.0     # loop height at the outer edge
LOOP_IN_H  = 34.0     # loop height where it meets the knot
LOOP_ROUND = 6.0      # corner rounding of the loops
TAIL_LEN   = 26.0
TAIL_W     = 16.0

TRIM        = 2.2     # black border width around white faces
PLATE_H     = 2.6
WHITE_RAISE = 0.8
TEXT_RAISE  = 1.2
TEXT_MOAT   = 0.7     # thin black gap around red letters

# carabiner snap clip
CLIP_ROUT   = 9.5
CLIP_RIN    = 5.8
CLIP_GATE_W = 1.8
CLIP_GAP_A  = (58.0, 122.0)   # angular opening (deg) where ring is removed
CLIP_GATE_A = (54.0, 120.0)   # gate span (anchored < opening, free tip inside)

COLORS = g.COLORS


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def round_poly(poly, r):
    return poly.buffer(r, join_style=1).buffer(-r, join_style=1)


def fit_text(text, font_path, target_w):
    """Return text as a shapely polygon scaled to target_w, centered at origin."""
    raw = g.text_to_polygon(text, font_path)
    minx, miny, maxx, maxy = raw.bounds
    s = target_w / (maxx - minx)
    p = sscale(raw, xfact=s, yfact=s, origin=(0, 0))
    minx, miny, maxx, maxy = p.bounds
    return stranslate(p, -(minx + maxx) / 2.0, -(miny + maxy) / 2.0)


def loop_shape(sign):
    """A ribbon loop fanning outward. sign=-1 left, +1 right."""
    inner_x = sign * (KNOT_W / 2 - 1.0)        # slight overlap into knot
    outer_x = sign * (BOW_W / 2)
    pts = [(inner_x,  LOOP_IN_H / 2),
           (outer_x,  LOOP_OUT_H / 2),
           (outer_x, -LOOP_OUT_H / 2),
           (inner_x, -LOOP_IN_H / 2)]
    return round_poly(Polygon(pts), LOOP_ROUND)


def tail_shape(sign):
    """A fishtail ribbon tail hanging down and out from the knot."""
    w = TAIL_W
    top_y = -LOOP_IN_H / 2 + 4
    rect = box(-w / 2, -TAIL_LEN, w / 2, 0)
    notch = Polygon([(-w / 2, -TAIL_LEN), (w / 2, -TAIL_LEN),
                     (0, -TAIL_LEN + 7)])          # V cut for fishtail
    tail = round_poly(rect.difference(notch), 2.0)
    tail = srot(tail, sign * 18, origin=(0, 0))     # splay outward
    return stranslate(tail, sign * (KNOT_W / 2 - 2), top_y)


def carabiner():
    """Flat snap clip: open ring + cantilever gate, centered at origin."""
    ring = Point(0, 0).buffer(CLIP_ROUT).difference(Point(0, 0).buffer(CLIP_RIN))
    # remove the top arc to create the opening
    a0, a1 = map(math.radians, CLIP_GAP_A)
    wedge = Polygon([(0, 0)] +
                    [(math.cos(a0 + (a1 - a0) * t / 24) * (CLIP_ROUT + 1),
                      math.sin(a0 + (a1 - a0) * t / 24) * (CLIP_ROUT + 1))
                     for t in range(25)])
    ring = ring.difference(wedge)
    # gate: an arc bar at mid radius, anchored before the opening, free tip inside
    rg = (CLIP_ROUT + CLIP_RIN) / 2
    g0, g1 = map(math.radians, CLIP_GATE_A)
    arc = LineString([(math.cos(g0 + (g1 - g0) * t / 40) * rg,
                       math.sin(g0 + (g1 - g0) * t / 40) * rg) for t in range(41)])
    gate = arc.buffer(CLIP_GATE_W / 2, cap_style=1)
    return unary_union([ring, gate])


# --------------------------------------------------------------------------- #
def build(name, team, gym):
    left  = loop_shape(-1)
    right = loop_shape(+1)
    knot  = round_poly(box(-KNOT_W / 2, -LOOP_OUT_H * 0.40,
                            KNOT_W / 2,  LOOP_OUT_H * 0.40), 4.0)
    tails = unary_union([tail_shape(-1), tail_shape(+1)])

    # clip sits above the knot
    knot_top = LOOP_OUT_H * 0.40
    clip = stranslate(carabiner(), 0, knot_top + CLIP_ROUT - 3.0)

    plate_poly = unary_union([left, right, knot, tails, clip])

    # white faces = each loop, inset by TRIM
    panel_l = left.buffer(-TRIM)
    panel_r = right.buffer(-TRIM)

    # text -------------------------------------------------------------------
    lc_x = (KNOT_W / 2 + BOW_W / 2) / 2 * -1   # left loop center x
    rc_x = (KNOT_W / 2 + BOW_W / 2) / 2        #
    loop_text_w = (BOW_W / 2 - KNOT_W / 2) * 0.62

    t_sonics = stranslate(fit_text(gym, FONT_BLACK, loop_text_w * 1.05), lc_x, 0)

    t_team = fit_text(team, FONT_NAME, loop_text_w * 0.85)
    t_name = fit_text(name, FONT_NAME, loop_text_w * 0.95)
    # cap name height so long names don't get huge
    nb = t_name.bounds
    if (nb[3] - nb[1]) > 11:
        s = 11 / (nb[3] - nb[1])
        t_name = sscale(t_name, xfact=s, yfact=s, origin=(0, 0))
    t_team = stranslate(t_team, rc_x,  9)
    t_name = stranslate(t_name, rc_x, -8)

    text_all = unary_union([t_sonics, t_team, t_name])

    # red center knot face (raised), inset for a black trim border
    knot_face = knot.buffer(-TRIM)
    red_all = unary_union([text_all, knot_face])

    # white loop faces: inset loops, minus the red moat, minus the knot region
    moat = text_all.buffer(TEXT_MOAT)
    white_all = (unary_union([panel_l, panel_r])
                 .difference(moat).difference(knot.buffer(0.6)))

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
