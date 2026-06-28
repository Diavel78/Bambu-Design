#!/usr/bin/env python3
"""
Generate a multi-color cheer-bow charm with a printed snap clip.

Real cheer-bow shape: two puffy loops splaying UP and out from a small
center knot, with two tails hanging DOWN with fishtail (V-notch) ends.

Layout:
  LEFT loop  : gym name      (default "Sonics", blackletter)
  RIGHT loop : team name     (default "XOXO") over athlete name (default "Eden")
Colors: white ribbon faces, red text + red center knot, black trim/tails.
Attachment: a flat, fully-printed carabiner-style snap clip at the top.

Change the name fast:
    python3 generate_bow.py --name Eden
    python3 generate_bow.py --name Harper --team XOXO --gym Sonics
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
TARGET_W   = 92.0     # final overall bow width (scaled at the end)

# loops (modeled as tilted ellipses that meet only at the center knot)
LOOP_A     = 22.0     # ellipse half-width
LOOP_B     = 27.0     # ellipse half-height
LOOP_CX    = 21.0     # how far out each loop center sits (apart -> two puffs)
LOOP_CY    = 16.0     # how far up each loop center sits
LOOP_TILT  = 30.0     # degrees each loop splays up-and-out

KNOT_W     = 16.0     # small center cinch
KNOT_TOP   = 9.0
KNOT_BOT   = -9.0

TAIL_LEN   = 42.0
TAIL_W     = 18.0
TAIL_SPLAY = 13.0     # degrees the tails splay apart
TAIL_X     = 9.0      # tail center offset from middle
TAIL_NOTCH = 9.0      # depth of the fishtail V

TRIM        = 2.4     # black border around white faces
PLATE_H     = 2.6
WHITE_RAISE = 0.8
TEXT_RAISE  = 1.2
TEXT_MOAT   = 0.7

# carabiner snap clip + stem
CLIP_ROUT   = 9.5
CLIP_RIN    = 5.8
CLIP_GATE_W = 1.8
CLIP_GAP_A  = (58.0, 122.0)
CLIP_GATE_A = (54.0, 120.0)
STEM_W      = 6.0

COLORS = g.COLORS


# --------------------------------------------------------------------------- #
# helpers
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


def ellipse(a, b, n=72):
    c = Point(0, 0).buffer(1.0, resolution=n // 4)
    return sscale(c, xfact=a, yfact=b, origin=(0, 0))


def loop_shape(sign):
    el = ellipse(LOOP_A, LOOP_B)
    el = srot(el, -sign * LOOP_TILT, origin=(0, 0))   # splay up-and-out
    return stranslate(el, sign * LOOP_CX, LOOP_CY)


def tail_shape(sign):
    w = TAIL_W
    rect = box(-w / 2, -TAIL_LEN, w / 2, 0)
    notch = Polygon([(-w / 2, -TAIL_LEN), (w / 2, -TAIL_LEN),
                     (0, -TAIL_LEN + TAIL_NOTCH)])
    tail = round_poly(rect.difference(notch), 2.5)
    tail = srot(tail, sign * TAIL_SPLAY, origin=(0, 0))
    return stranslate(tail, sign * TAIL_X, -4)


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
    left  = loop_shape(-1)
    right = loop_shape(+1)
    knot  = round_poly(box(-KNOT_W / 2, KNOT_BOT, KNOT_W / 2, KNOT_TOP), 5.0)
    tails = unary_union([tail_shape(-1), tail_shape(+1)])

    # clip on a short stem rising from the top of the loops
    loop_top = max(left.bounds[3], right.bounds[3])
    clip_y = loop_top + CLIP_ROUT - 2.0
    stem = round_poly(box(-STEM_W / 2, LOOP_CY, STEM_W / 2, clip_y), 2.0)
    clip = stranslate(carabiner(), 0, clip_y)

    plate_poly = unary_union([left, right, knot, tails, stem, clip])

    # ---- text -------------------------------------------------------------
    # anchors placed in the meat of each loop puff, clear of the knot
    tw = LOOP_A * 1.1
    LX, RX = -25.0, 27.0
    t_sonics = stranslate(fit_text(gym, FONT_BLACK, tw, max_h=14), LX, 7)
    t_team   = stranslate(fit_text(team, FONT_NAME, tw * 0.80, max_h=9), RX, 14)
    t_name   = stranslate(fit_text(name, FONT_NAME, tw, max_h=10), RX, 1)
    text_all = unary_union([t_sonics, t_team, t_name])

    # red center knot face
    knot_face = knot.buffer(-TRIM)
    red_all = unary_union([text_all, knot_face])

    # white loop faces: inset loops minus the red moat and the knot
    panel = unary_union([left.buffer(-TRIM), right.buffer(-TRIM)])
    moat = text_all.buffer(TEXT_MOAT)
    white_all = panel.difference(moat).difference(knot.buffer(0.6))

    # ---- scale whole design to TARGET_W, recenter ------------------------
    bb = plate_poly.bounds
    s = TARGET_W / (bb[2] - bb[0])
    def fix(p):
        p = sscale(p, xfact=s, yfact=s, origin=(0, 0))
        b = p.bounds
        return stranslate(p, -(b[0] + b[2]) / 2.0, 0)  # x-center only here
    # center x using the plate; apply same shift to all
    pb = sscale(plate_poly, xfact=s, yfact=s, origin=(0, 0)).bounds
    dx = -(pb[0] + pb[2]) / 2.0
    def app(p):
        return stranslate(sscale(p, xfact=s, yfact=s, origin=(0, 0)), dx, 0)
    plate_poly, red_all, white_all = app(plate_poly), app(red_all), app(white_all)

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
