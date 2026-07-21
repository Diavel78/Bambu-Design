#!/usr/bin/env python3
"""
Generate drawer-organizer boxes for filing drink-mix stick packets upright.

Real-world inputs (measured against a tape measure):
  - Drawer:  20 in x 14.5 in x ~2.4 in deep  (508 x 368 x 61 mm)
  - Sticks:  ~4.25 in x ~1.25 in x ~0.4 in   (e.g. ICEE, Liquid Death, LMNT)

Idea: the sticks are only ~1.25 in wide, so they stand up in a shallow box and
file front-to-back like index cards. A curved "scoop" in the front wall lets you
see the flavors and slide one out.

The drawer is tiled by an N x M grid of IDENTICAL boxes, so you only print ONE
file and repeat it. No baseplate -- the boxes just drop into the drawer and,
sized to fill it, they can't slide around.

Output (models/drawer_organizer/):
  - drink_stick_box.stl          <- the box to print (repeat COLS*ROWS times)
  - drawer_layout_preview.stl    <- all boxes arranged, just to eyeball the fit
  - (renders/drawer_layout.png   <- top-down map, if matplotlib is available)

Everything is parametric -- change the CONFIG block and re-run.
Units are millimeters.
"""

import os
import numpy as np
import trimesh
from trimesh.creation import box as _box, cylinder as _cyl

# --------------------------------------------------------------------------- #
# CONFIG -- change these and re-run to iterate.
# --------------------------------------------------------------------------- #
IN = 25.4  # mm per inch

# --- Drawer interior (measured) ---
DRAWER_L = 20.0 * IN     # 508.0 mm  (the "20 inch" run)
DRAWER_W = 14.5 * IN     # 368.3 mm  (the "14.5 inch" run)
DRAWER_D = 2.4 * IN      # ~61   mm  (just under 2.5 in deep)

# --- Stick packet (measured, with a little slack) ---
STICK_LEN = 4.25 * IN    # ~108 mm  laid horizontally in the box
STICK_TALL = 1.25 * IN   # ~32  mm  how tall it stands up
STICK_THICK = 0.40 * IN  # ~10  mm  used only to estimate capacity

# --- Grid: how many boxes tile the drawer ---
COLS = 4                 # boxes along the 20 in run
ROWS = 2                 # boxes along the 14.5 in run
DRAWER_GAP = 2.0         # total slack per box per axis (drop-in clearance)

# --- Box build ---
BOX_H = 38.0             # box height (drawer is ~61 mm, so lots of clearance)
WALL = 2.0              # wall thickness
FLOOR = 2.0             # floor thickness

# --- Front scoop (the curved dip you grab sticks through) ---
SCOOP_DIP = 22.0         # how far the front wall is lowered at its center
SCOOP_R = 80.0           # arc radius (bigger = shallower, wider U)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "drawer_organizer")
RENDER_DIR = os.path.join(os.path.dirname(__file__), "..", "renders")

# --------------------------------------------------------------------------- #
# Derived box footprint (fills the drawer exactly, minus drop-in clearance)
# --------------------------------------------------------------------------- #
BOX_L = DRAWER_L / COLS - DRAWER_GAP   # X, along the 20 in run
BOX_W = DRAWER_W / ROWS - DRAWER_GAP   # Y, along the 14.5 in run


def _engine_diff(a, b):
    """Boolean difference with whatever solid engine is installed."""
    return trimesh.boolean.difference([a, b])


def make_box():
    """One open-top box with a curved front scoop.

    Coordinates: box sits on z=0, centered on x/y.
      X spans BOX_L, Y spans BOX_W, Z spans 0..BOX_H.
      Sticks lie with their LENGTH along X and file along Y.
      The scoop is cut into the front wall at y = -BOX_W/2.
    """
    # Outer solid
    outer = _box(extents=[BOX_L, BOX_W, BOX_H])
    outer.apply_translation([0, 0, BOX_H / 2.0])

    # Inner cavity: open the top by making it taller than the box
    cav = _box(extents=[BOX_L - 2 * WALL, BOX_W - 2 * WALL, BOX_H])
    cav.apply_translation([0, 0, FLOOR + BOX_H / 2.0])
    shell = _engine_diff(outer, cav)

    # Scoop: a cylinder (axis along Y, through the front wall) whose circular
    # profile in the X-Z plane carves a downward arc into the wall's top edge.
    z_center = (BOX_H - SCOOP_DIP) + SCOOP_R          # circle bottom sits at BOX_H-DIP
    cyl = _cyl(radius=SCOOP_R, height=WALL + 6.0, sections=96)
    # cylinder default axis = Z; rotate so axis -> Y
    rot = trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0])
    cyl.apply_transform(rot)
    # place at front wall
    y_front = -BOX_W / 2.0 + WALL / 2.0
    cyl.apply_translation([0.0, y_front, z_center])
    box_mesh = _engine_diff(shell, cyl)

    box_mesh.remove_unreferenced_vertices()
    return box_mesh


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    box_mesh = make_box()
    box_path = os.path.join(OUT_DIR, "drink_stick_box.stl")
    box_mesh.export(box_path)

    # Capacity estimate
    inner_len = BOX_L - 2 * WALL
    inner_file = BOX_W - 2 * WALL
    per_box = int(inner_file // STICK_THICK)
    total = per_box * COLS * ROWS

    # Whole-drawer preview (not for printing -- just to look at the fit)
    combo = []
    for c in range(COLS):
        for r in range(ROWS):
            m = box_mesh.copy()
            x = -DRAWER_L / 2.0 + (c + 0.5) * (DRAWER_L / COLS)
            y = -DRAWER_W / 2.0 + (r + 0.5) * (DRAWER_W / ROWS)
            m.apply_translation([x, y, 0])
            combo.append(m)
    preview = trimesh.util.concatenate(combo)
    preview_path = os.path.join(OUT_DIR, "drawer_layout_preview.stl")
    preview.export(preview_path)

    # Optional top-down render
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle, FancyBboxPatch

        os.makedirs(RENDER_DIR, exist_ok=True)
        fig, ax = plt.subplots(figsize=(8, 8 * DRAWER_W / DRAWER_L))
        ax.add_patch(Rectangle((0, 0), DRAWER_L, DRAWER_W, fill=False, lw=3, ec="#444"))
        for c in range(COLS):
            for r in range(ROWS):
                x = c * (DRAWER_L / COLS) + DRAWER_GAP / 2
                y = r * (DRAWER_W / ROWS) + DRAWER_GAP / 2
                ax.add_patch(Rectangle((x, y), BOX_L, BOX_W, fc="#cfe8ff",
                                       ec="#2b6cb0", lw=2))
                ax.text(x + BOX_L / 2, y + BOX_W / 2,
                        f"~{per_box} sticks", ha="center", va="center", fontsize=11)
        ax.set_xlim(-10, DRAWER_L + 10)
        ax.set_ylim(-10, DRAWER_W + 10)
        ax.set_aspect("equal")
        ax.set_title(f'Drawer: 20 x 14.5 in  |  {COLS*ROWS} boxes '
                     f'({COLS} x {ROWS})  |  ~{total} sticks total')
        ax.set_xlabel("20 in (508 mm)")
        ax.set_ylabel("14.5 in (368 mm)")
        fig.tight_layout()
        fig.savefig(os.path.join(RENDER_DIR, "drawer_layout.png"), dpi=110)
        plt.close(fig)
        rendered = True
    except Exception as e:  # matplotlib not installed -> skip quietly
        rendered = False
        print(f"(skipped PNG render: {e})")

    print("=" * 62)
    print("Drawer organizer generated")
    print("=" * 62)
    print(f"Drawer inside : {DRAWER_L:.0f} x {DRAWER_W:.0f} x {DRAWER_D:.0f} mm "
          f"(20 x 14.5 x 2.4 in)")
    print(f"Grid          : {COLS} across x {ROWS} deep = {COLS*ROWS} boxes "
          f"(all identical)")
    print(f"Box outside   : {BOX_L:.1f} x {BOX_W:.1f} x {BOX_H:.1f} mm")
    print(f"Box inside    : {inner_len:.1f} x {inner_file:.1f} x "
          f"{BOX_H-FLOOR:.1f} mm")
    print(f"Stick fit     : {STICK_LEN:.0f} mm long fits the {inner_len:.0f} mm "
          f"inside length")
    print(f"Capacity      : ~{per_box} sticks/box  ->  ~{total} sticks total")
    print(f"Front scoop   : dips to {BOX_H-SCOOP_DIP:.0f} mm at center "
          f"(sticks stand {STICK_TALL:.0f} mm)")
    print("-" * 62)
    print(f"PRINT: {box_path}")
    print(f"       ...repeat {COLS*ROWS} times (fits ~4 per H2D plate).")
    print(f"PREVIEW (do not print): {preview_path}")
    if rendered:
        print(f"MAP: renders/drawer_layout.png")


if __name__ == "__main__":
    main()
