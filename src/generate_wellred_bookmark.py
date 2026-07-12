#!/usr/bin/env python3
"""
Generate a "Well Red Book Club" page-slide bookmark for 3D printing.

The bookmark is a flat clip that slides over the top (or side) edge of a
page: three rounded prongs hang below a round logo badge, and the paper
weaves between them -- in front of the two outer prongs, behind the center
one. Paper's own stiffness holds it in place; nothing to bend or break.
The badge and the center prong face the reader.

Output (models/bookmark/ or models/bookmark_<name>/):
  - 3 separate color bodies (plate=cream, art=burgundy ring+glass,
    text=burgundy lettering) as STL
  - one combined single-color STL
  - one STEP file (editable CAD)
Plus a colored top-view PNG preview in ../renders/.

Designed for a Bambu Lab H2D + AMS (multi-color). Units are millimeters.

Optionally put a member's name on the center prong:
    python3 src/generate_wellred_bookmark.py --name Rob
"""

import argparse
import os

import cadquery as cq
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.affinity import rotate as srotate, scale as sscale, \
    translate as stranslate

from generate_sonics_charm import text_to_polygon, normalize, extrude

# --------------------------------------------------------------------------- #
# CONFIG -- change these and re-run to iterate.
# --------------------------------------------------------------------------- #
FONT_DIR    = os.path.join(os.path.dirname(__file__), "..", "fonts")
FONT_SCRIPT = os.path.join(FONT_DIR, "Pacifico-Regular.ttf")       # "Well"
FONT_SERIF  = os.path.join(FONT_DIR, "PlayfairDisplay-Bold.ttf")   # "RED"
FONT_SMALL  = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")        # "BOOK CLUB"

BADGE_R      = 23.0    # badge radius -> 46 mm logo circle
RING_OUT_W   = 1.4     # outer burgundy ring width
RING_IN_W    = 0.7     # inner (thin) ring width
RING_GAP     = 1.6     # gap between the two rings

PLATE_H      = 1.6     # flat body thickness (whole bookmark)
ART_RAISE    = 0.6     # how far the burgundy details sit above the body

PRONG_LEN    = 48.0    # outer prong length below the crossbar
PRONG_EXTRA  = 6.0     # center prong is this much longer (easier to thread)
PRONG_W_MID  = 13.0    # center prong width (faces the reader)
PRONG_W_OUT  = 7.0     # outer prong width
PRONG_GAP    = 3.5     # gap the paper weaves through
BAR_H        = 8.0     # crossbar joining prongs to the badge

OUT_DIR_MODELS = os.path.join(os.path.dirname(__file__), "..", "models")
OUT_DIR_RENDER = os.path.join(os.path.dirname(__file__), "..", "renders")

COLORS = {"plate": "#f6efe3", "art": "#6e1423", "text": "#6e1423"}

# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def stadium(x, y0, y1, half_w):
    """Vertical rounded-end bar (a buffered line segment)."""
    return LineString([(x, y0), (x, y1)]).buffer(half_w, resolution=32)


def placed_text(text, font, width, cx, cy, min_stroke=0.0):
    """Text polygon scaled to `width` mm, centered at (cx, cy).

    min_stroke > 0 dilates the glyphs slightly so hairline serifs survive
    a 0.4 mm nozzle.
    """
    poly = normalize(text_to_polygon(text, font), width)
    if min_stroke:
        poly = poly.buffer(min_stroke / 2.0, join_style=1)
    return stranslate(poly, cx, cy)


def wine_glass(cx, cy, height):
    """Solid wine-glass silhouette, base sitting at (cx, cy)."""
    s = height / 7.0                       # design is 7 units tall
    bowl_r = 2.05 * s
    bowl_c = 4.6 * s
    bowl = Point(0, bowl_c).buffer(bowl_r, resolution=48)
    bowl = bowl.union(box(-bowl_r, bowl_c, bowl_r, 6.4 * s))
    bowl = bowl.intersection(box(-bowl_r, 0, bowl_r, 6.4 * s))
    stem = box(-0.35 * s, 0.6 * s, 0.35 * s, bowl_c)
    foot = sscale(Point(0, 0.55 * s).buffer(1.7 * s, resolution=48),
                  xfact=1.0, yfact=0.32, origin=(0, 0.55 * s))
    foot = foot.union(box(-1.7 * s, 0.25 * s, 1.7 * s, 0.55 * s))
    return stranslate(unary_union([bowl, stem, foot]), cx, cy)


# --------------------------------------------------------------------------- #
# Build the three color bodies
# --------------------------------------------------------------------------- #
def build(name=None):
    # ---- flat body: badge + crossbar + three prongs ----------------------- #
    badge = Point(0, 0).buffer(BADGE_R, resolution=128)

    bar_top = -BADGE_R + 4.0                       # overlap into the badge
    bar_bot = bar_top - BAR_H
    x_out = PRONG_W_MID / 2 + PRONG_GAP + PRONG_W_OUT / 2
    bar_w2 = x_out + PRONG_W_OUT / 2
    bar = box(-bar_w2, bar_bot, bar_w2, bar_top)

    tip = bar_bot - PRONG_LEN
    prongs = [
        stadium(0, bar_bot, tip - PRONG_EXTRA, PRONG_W_MID / 2),
        stadium(-x_out, bar_bot, tip, PRONG_W_OUT / 2),
        stadium(x_out, bar_bot, tip, PRONG_W_OUT / 2),
    ]
    # round the bar's outer corners too
    bar = bar.buffer(-1.5, join_style=1).buffer(1.5, join_style=1)
    plate_poly = unary_union([badge, bar, *prongs])

    # ---- burgundy artwork: double ring + wine glass + BOOK CLUB dashes ---- #
    def ring(r_outer, w):
        return (Point(0, 0).buffer(r_outer, resolution=128)
                .difference(Point(0, 0).buffer(r_outer - w, resolution=128)))

    art = [
        ring(BADGE_R - 1.0, RING_OUT_W),
        ring(BADGE_R - 1.0 - RING_OUT_W - RING_GAP, RING_IN_W),
        wine_glass(0.0, -17.5, 7.0),
    ]
    # em-dashes flanking "BOOK CLUB", like the logo
    for sx in (-1, 1):
        art.append(box(sx * 13.2 - 1.8, -9.55, sx * 13.2 + 1.8, -8.85))
    art_poly = unary_union(art)

    # ---- lettering --------------------------------------------------------#
    texts = [
        placed_text("Well", FONT_SCRIPT, 21.0, 0.0, 9.0),
        placed_text("RED", FONT_SERIF, 24.0, 0.0, -1.5, min_stroke=0.25),
        placed_text("B O O K  C L U B", FONT_SMALL, 21.0, 0.0, -9.2,
                    min_stroke=0.15),
    ]
    if name:
        # vertical name on the center prong, reading downward
        max_len = PRONG_LEN + PRONG_EXTRA - 10.0
        label = normalize(text_to_polygon(name, FONT_SCRIPT), 10.0)
        w = label.bounds[2] - label.bounds[0]
        h = label.bounds[3] - label.bounds[1]
        target_h = min(PRONG_W_MID - 4.5, 8.0)
        s = min(target_h / h, max_len / w)
        label = sscale(label, xfact=s, yfact=s, origin=(0, 0))
        label = srotate(label, -90, origin=(0, 0))
        label = stranslate(label, 0, bar_bot - (PRONG_LEN + PRONG_EXTRA) / 2)
        texts.append(label)
    text_poly = unary_union(texts)

    # keep raised details strictly inside the flat body
    art_poly = art_poly.intersection(plate_poly)
    text_poly = text_poly.intersection(plate_poly)

    bodies = {
        "plate": extrude(plate_poly, 0.0, PLATE_H),
        "art":   extrude(art_poly,  PLATE_H, ART_RAISE),
        "text":  extrude(text_poly, PLATE_H, ART_RAISE),
    }
    return bodies, dict(plate=plate_poly, art=art_poly, text=text_poly)


# --------------------------------------------------------------------------- #
# Export + preview
# --------------------------------------------------------------------------- #
def export(name, bodies):
    d = os.path.join(OUT_DIR_MODELS, name)
    os.makedirs(d, exist_ok=True)
    for color, body in bodies.items():
        cq.exporters.export(cq.Workplane(obj=body),
                            os.path.join(d, f"{name}_{color}.stl"))
    combined = bodies["plate"].fuse(bodies["art"]).fuse(bodies["text"])
    cq.exporters.export(cq.Workplane(obj=combined),
                        os.path.join(d, f"{name}_combined.stl"))
    cq.exporters.export(cq.Workplane(obj=combined),
                        os.path.join(d, f"{name}.step"))
    print(f"  exported -> models/{name}/")


def render_preview(name, polys):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    import numpy as np

    fig, ax = plt.subplots(figsize=(4, 8))

    def patch(geom, color, z):
        geoms = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in geoms:
            verts, codes = [], []
            for ring in [p.exterior, *p.interiors]:
                c = np.asarray(ring.coords)
                verts.extend(c)
                codes.extend([Path.MOVETO] + [Path.LINETO] * (len(c) - 2)
                             + [Path.CLOSEPOLY])
            ax.add_patch(PathPatch(Path(verts, codes), facecolor=color,
                                   edgecolor="none", zorder=z))

    patch(polys["plate"], COLORS["plate"], 1)
    patch(polys["art"],   COLORS["art"],   2)
    patch(polys["text"],  COLORS["text"],  3)
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    ax.margins(0.04)
    os.makedirs(OUT_DIR_RENDER, exist_ok=True)
    out = os.path.join(OUT_DIR_RENDER, f"{name}.png")
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor="#2b2126")
    plt.close(fig)
    print(f"  preview  -> renders/{name}.png")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None,
                    help="optional member name on the center prong")
    args = ap.parse_args()

    out = "bookmark" if not args.name else f"bookmark_{args.name.lower()}"
    print(f"[{out}]")
    bodies, polys = build(args.name)
    export(out, bodies)
    render_preview(out, polys)


if __name__ == "__main__":
    main()
