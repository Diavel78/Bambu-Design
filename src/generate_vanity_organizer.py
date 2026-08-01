#!/usr/bin/env python3
"""Vanity drawer organizer boxes — a 5-size kit that tiles 3 drawers.

Drawers (interior, inches):
  * 1x big drawer:    11.5 front-to-back x 18.5 wide
  * 2x small drawers: 11.5 front-to-back x  8.0 wide

All boxes are 2.5 in tall. The kit shares one row system front-to-back
(3.5 + 3.5 + 4.375 = 11.375 in) so every drawer uses the same box sizes:

  size   W x FB (in)        use
  S      3.9375 x 3.5       lip gloss, hair ties, small stuff
  M      7.875  x 3.5       full-width tray (compacts, palettes)
  L      7.875  x 4.375     big back tray (palettes, bottles)
  LS     3.9375 x 4.375     half-width back bin
  BRUSH  2.625  x 11.375    full-length brush / pencil tray

Small drawer (8 in wide -> one 7.875 col):   [S S] [M] [L]
Big drawer (18.5 in wide -> 7.875 + 7.875 + 2.625 cols):
  col1 [S S][M][L]   col2 [M][S S][LS LS]   col3 [BRUSH]

Outputs models/vanity_organizer/*.stl (+ .step) and renders/vanity_layout.png
Run:  python3 src/generate_vanity_organizer.py
"""

import os

import cadquery as cq
from cadquery import exporters
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

IN = 25.4  # mm per inch

# ---------------------------------------------------------------- parameters
HEIGHT = 2.5 * IN          # 63.5 mm — all boxes
WALL = 1.6                 # side wall thickness (4 x 0.4 mm perimeters)
FLOOR = 1.2
CORNER_R = 4.0             # outer vertical-edge radius
RIM = 0.6                  # top-rim chamfer so edges aren't sharp

ROW_FB = [3.5, 3.5, 4.375]           # front-to-back row depths, sums 11.375
COL_W_SMALL = 7.875                  # small-drawer column width
COL_W_BRUSH = 2.625                  # slim brush-tray column in the big drawer

# name -> (width across drawer, front-to-back) in inches
SIZES = {
    "S": (COL_W_SMALL / 2, ROW_FB[0]),
    "M": (COL_W_SMALL, ROW_FB[0]),
    "L": (COL_W_SMALL, ROW_FB[2]),
    "LS": (COL_W_SMALL / 2, ROW_FB[2]),
    "BRUSH": (COL_W_BRUSH, sum(ROW_FB)),
}

DRAWERS = {
    "small drawer (x2)": (8.0, 11.5),
    "big drawer": (18.5, 11.5),
}

# (size, x, y) in inches, x = across the drawer from the left, y = from front
SMALL_COL = [
    ("S", 0.0, 0.0), ("S", COL_W_SMALL / 2, 0.0),
    ("M", 0.0, ROW_FB[0]),
    ("L", 0.0, ROW_FB[0] + ROW_FB[1]),
]
BIG_COL2 = [
    ("M", 0.0, 0.0),
    ("S", 0.0, ROW_FB[0]), ("S", COL_W_SMALL / 2, ROW_FB[0]),
    ("LS", 0.0, ROW_FB[0] + ROW_FB[1]), ("LS", COL_W_SMALL / 2, ROW_FB[0] + ROW_FB[1]),
]
LAYOUTS = {
    "small drawer (x2)": SMALL_COL,
    "big drawer": (
        SMALL_COL
        + [(n, x + COL_W_SMALL, y) for n, x, y in BIG_COL2]
        + [("BRUSH", 2 * COL_W_SMALL, 0.0)]
    ),
}


def check_layouts():
    for drawer, (dw, dfb) in DRAWERS.items():
        for name, x, y in LAYOUTS[drawer]:
            w, fb = SIZES[name]
            assert x + w <= dw + 1e-9 and y + fb <= dfb + 1e-9, (drawer, name)
        area = sum(SIZES[n][0] * SIZES[n][1] for n, _, _ in LAYOUTS[drawer])
        slack_w = dw - max(x + SIZES[n][0] for n, x, _ in LAYOUTS[drawer])
        slack_fb = dfb - max(y + SIZES[n][1] for n, _, y in LAYOUTS[drawer])
        print(f"{drawer}: {len(LAYOUTS[drawer])} boxes, "
              f"fill {area:.2f}/{dw * dfb:.2f} sq-in, "
              f"slack {slack_w:.3f} in across x {slack_fb:.3f} in front-to-back")


def make_box(w_in, fb_in):
    w, fb = w_in * IN, fb_in * IN
    box = (
        cq.Workplane("XY")
        .box(w, fb, HEIGHT, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
        .faces(">Z").shell(-WALL)
    )
    # shell leaves an open top; put the floor back at FLOOR thickness
    floor = (
        cq.Workplane("XY")
        .box(w, fb, FLOOR, centered=(True, True, False))
        .edges("|Z").fillet(CORNER_R)
    )
    box = box.union(floor)
    box = box.faces(">Z").chamfer(RIM)
    return box


def render_layout(path):
    colors = {"S": "#f6a6c1", "M": "#b39ddb", "L": "#80cbc4",
              "LS": "#ffcc80", "BRUSH": "#90caf9"}
    fig, axes = plt.subplots(
        1, 3, figsize=(14, 5.4),
        gridspec_kw={"width_ratios": [8, 8, 18.5]})
    order = ["small drawer (x2)", "small drawer (x2)", "big drawer"]
    titles = ["Small drawer #1", "Small drawer #2", "Big drawer"]
    for ax, drawer, title in zip(axes, order, titles):
        dw, dfb = DRAWERS[drawer]
        ax.add_patch(Rectangle((0, 0), dw, dfb, fill=False, lw=2.5,
                               edgecolor="#444"))
        for name, x, y in LAYOUTS[drawer]:
            w, fb = SIZES[name]
            ax.add_patch(Rectangle((x, y), w, fb, facecolor=colors[name],
                                   edgecolor="#333", lw=1.2))
            ax.text(x + w / 2, y + fb / 2, f"{name}\n{w:g}″x{fb:g}″",
                    ha="center", va="center", fontsize=8.5)
        ax.set_xlim(-0.4, dw + 0.4)
        ax.set_ylim(-0.9, dfb + 0.4)
        ax.set_aspect("equal")
        ax.set_title(f"{title}  ({dw:g}″ x {dfb:g}″)")
        ax.text(dw / 2, -0.55, "front of drawer", ha="center", fontsize=8,
                color="#777")
        ax.axis("off")
    fig.suptitle("Vanity drawer organizer layout — top view "
                 "(all boxes 2.5″ tall)", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"wrote {path}")


def main():
    check_layouts()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(here, "models", "vanity_organizer")
    os.makedirs(out, exist_ok=True)

    counts = {}
    for drawer, layout in LAYOUTS.items():
        mult = 2 if "x2" in drawer else 1
        for name, _, _ in layout:
            counts[name] = counts.get(name, 0) + mult

    for name, (w, fb) in SIZES.items():
        box = make_box(w, fb)
        stem = os.path.join(out, f"box_{name}")
        exporters.export(box, stem + ".stl")
        exporters.export(box, stem + ".step")
        print(f"box_{name}: {w:g} x {fb:g} in "
              f"({w * IN:.1f} x {fb * IN:.1f} mm), print {counts[name]}x")

    render_layout(os.path.join(here, "renders", "vanity_layout.png"))


if __name__ == "__main__":
    main()
