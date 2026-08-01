#!/usr/bin/env python3
"""Vanity drawer organizer boxes — a kit that tiles 2 drawers.

Drawers (interior, inches):
  * 1x big drawer:   11.5 front-to-back x 18.5 wide
  * 1x small drawer: 11.5 front-to-back x  8.0 wide

All boxes are 2.5 in tall. Each drawer fills to 11.375 x (width - 0.125)
so the set drops in with ~1/8 in of wiggle room.

Small drawer (8 in wide, 5 boxes):
  front: [DEEP DEEP SLIML]   back: [BACK SLIM]

Big drawer (18.5 in wide, 8 boxes), columns left to right:
  col1 (5.5): A (5.5x7.375, grown from 5.5x5 min) front, E (5.5x4) back
  col2 (5):   D (5x6) front, B1 (5x5.375) back
  col3 (4.375): C (4.375x6.375) front, B2 (4.375x5) back
  col4 (3.5): BRUSH (3.5 x full length)

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

FB = 11.375                # front-to-back fill in every drawer

# name -> (width across drawer, front-to-back) in inches
SIZES = {
    # small drawer
    "DEEP": (3.4375, 7.375),
    "BACK": (6.875, 4.0),
    "SLIM": (1.0, 4.0),
    "SLIML": (1.0, 7.375),
    # big drawer
    "A": (5.5, 7.375),       # grown from the 5.5 x 5 minimum
    "B1": (5.0, 5.375),      # grown from 5 x 3.5 to fill its column
    "B2": (4.375, 5.0),      # grown from 5 x 3.5 (rotated) to fill its column
    "C": (4.375, 6.375),     # grown from 4.5 x 4.5 to fill its column
    "D": (5.0, 6.0),
    "E": (5.5, 4.0),
    "BRUSH": (3.5, FB),      # full-length brush tray
}

DRAWERS = {
    "small drawer": (8.0, 11.5),
    "big drawer": (18.5, 11.5),
}

# (size, x, y[, rotated]) in inches, x = across the drawer from the left,
# y = from the front. rotated=True swaps the footprint 90 degrees in place.
SMALL_DRAWER = [
    ("DEEP", 0.0, 0.0), ("DEEP", 3.4375, 0.0),
    ("SLIML", 6.875, 0.0),
    ("BACK", 0.0, 7.375),
    ("SLIM", 6.875, 7.375),
]
BIG_DRAWER = [
    ("A", 0.0, 0.0), ("E", 0.0, 7.375),
    ("D", 5.5, 0.0), ("B1", 5.5, 6.0),
    ("C", 10.5, 0.0), ("B2", 10.5, 6.375),
    ("BRUSH", 14.875, 0.0),
]
LAYOUTS = {
    "small drawer": SMALL_DRAWER,
    "big drawer": BIG_DRAWER,
}


def footprint(entry):
    name, x, y = entry[0], entry[1], entry[2]
    w, fb = SIZES[name]
    if len(entry) > 3 and entry[3]:
        w, fb = fb, w
    return name, x, y, w, fb


def check_layouts():
    for drawer, (dw, dfb) in DRAWERS.items():
        boxes = [footprint(e) for e in LAYOUTS[drawer]]
        for name, x, y, w, fb in boxes:
            assert x + w <= dw + 1e-9 and y + fb <= dfb + 1e-9, (drawer, name)
        # no overlaps
        for i, (n1, x1, y1, w1, f1) in enumerate(boxes):
            for n2, x2, y2, w2, f2 in boxes[i + 1:]:
                assert (x1 + w1 <= x2 + 1e-9 or x2 + w2 <= x1 + 1e-9
                        or y1 + f1 <= y2 + 1e-9 or y2 + f2 <= y1 + 1e-9), \
                    (drawer, n1, n2)
        area = sum(w * fb for _, _, _, w, fb in boxes)
        slack_w = dw - max(x + w for _, x, _, w, _ in boxes)
        slack_fb = dfb - max(y + fb for _, _, y, _, fb in boxes)
        print(f"{drawer}: {len(boxes)} boxes, "
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
    colors = {"DEEP": "#f6a6c1", "BACK": "#b39ddb", "SLIM": "#c5e1a5",
              "SLIML": "#c5e1a5", "A": "#80cbc4", "B1": "#f6a6c1",
              "B2": "#f6a6c1", "C": "#ffcc80", "D": "#b39ddb",
              "E": "#ffab91", "BRUSH": "#90caf9"}
    fig, axes = plt.subplots(
        1, 2, figsize=(11, 5.4),
        gridspec_kw={"width_ratios": [8, 18.5]})
    for ax, drawer, title in zip(axes, LAYOUTS, ["Small drawer", "Big drawer"]):
        dw, dfb = DRAWERS[drawer]
        ax.add_patch(Rectangle((0, 0), dw, dfb, fill=False, lw=2.5,
                               edgecolor="#444"))
        for entry in LAYOUTS[drawer]:
            name, x, y, w, fb = footprint(entry)
            ax.add_patch(Rectangle((x, y), w, fb, facecolor=colors[name],
                                   edgecolor="#333", lw=1.2))
            rot = 90 if w < 1.5 else 0
            fs = 7 if min(w, fb) < 2 else 8.5
            ax.text(x + w / 2, y + fb / 2, f"{name} {w:g}″x{fb:g}″",
                    ha="center", va="center", fontsize=fs, rotation=rot)
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
    for layout in LAYOUTS.values():
        for entry in layout:
            counts[entry[0]] = counts.get(entry[0], 0) + 1

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
