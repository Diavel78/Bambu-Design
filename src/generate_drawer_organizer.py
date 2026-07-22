#!/usr/bin/env python3
"""
Generate a simple open box, 5 x 7 x 2 inches, for organizing a drawer.

Placed like the sketch: boxes sit 2 side by side across the 14.5 in width
(each 5 in across), 7 in front-to-back. Two rows front-to-back = 4 boxes.

Everything is in INCHES. (STL is written at the matching millimeter size so it
imports at true 5 x 7 x 2 in in Bambu Studio.)

Output (models/drawer_organizer/):
  - drink_box.stl                <- the box to print (repeat up to 4 times)
  - drawer_layout_preview.stl    <- boxes placed in the drawer (do not print)
  - renders/*.png                <- previews, labeled in inches
"""

import os
import numpy as np
import trimesh
from trimesh.creation import box as _box

IN = 25.4  # mm per inch (STL is mm so slicers read true inches)

# --- Box size, in inches ---
BOX_ACROSS_IN = 5.0    # across the 14.5 in width
BOX_DEEP_IN = 7.0      # front-to-back
BOX_H_IN = 2.0         # tall
WALL_IN = 0.1
FLOOR_IN = 0.1

# --- Drawer + arrangement, in inches ---
DRAWER_L_IN = 20.0     # front-to-back
DRAWER_W_IN = 14.5     # across
N_ACROSS = 2           # 2 across the width  (2 x 5 in = 10 in)
N_DEEP = 2             # 2 rows front-to-back (2 x 7 in = 14 in)  -> 4 boxes

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "drawer_organizer")
RENDER_DIR = os.path.join(os.path.dirname(__file__), "..", "renders")


def make_box():
    # local X = across (5 in), local Y = deep (7 in), Z = tall
    L, W, H = BOX_ACROSS_IN * IN, BOX_DEEP_IN * IN, BOX_H_IN * IN
    wall, floor = WALL_IN * IN, FLOOR_IN * IN
    outer = _box(extents=[L, W, H]); outer.apply_translation([0, 0, H / 2])
    cav = _box(extents=[L - 2 * wall, W - 2 * wall, H])
    cav.apply_translation([0, 0, floor + H / 2])
    m = trimesh.boolean.difference([outer, cav])
    m.remove_unreferenced_vertices()
    return m


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    box = make_box()
    box_path = os.path.join(OUT_DIR, "drink_box.stl")
    box.export(box_path)

    # Layout, as drawn on the sketch:
    #   FRONT row: 2 boxes turned SIDEWAYS -> 7 in across x 5 in deep (fills width)
    #   BACK row : 2 boxes normal          -> 5 in across x 7 in deep
    # (x0, y0) = lower-left corner in inches; (w, d) = across, deep; rot = sideways?
    rects = [
        (0.0, 0.0, BOX_DEEP_IN,   BOX_ACROSS_IN, True),   # front-left sideways
        (7.0, 0.0, BOX_DEEP_IN,   BOX_ACROSS_IN, True),   # front-right sideways
        (0.0, 5.0, BOX_ACROSS_IN, BOX_DEEP_IN,   False),  # back-left
        (5.0, 5.0, BOX_ACROSS_IN, BOX_DEEP_IN,   False),  # back-right
    ]

    combo = []
    for (x0, y0, w, d, rot) in rects:
        m = box.copy()
        if rot:
            m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
        cx = (-DRAWER_W_IN / 2 + x0 + w / 2) * IN
        cy = (-DRAWER_L_IN / 2 + y0 + d / 2) * IN
        m.apply_translation([cx, cy, 0])
        combo.append(m)
    trimesh.util.concatenate(combo).export(
        os.path.join(OUT_DIR, "drawer_layout_preview.stl"))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        from matplotlib.patches import Rectangle
        os.makedirs(RENDER_DIR, exist_ok=True)

        # 3D box (labeled in inches)
        fig = plt.figure(figsize=(7, 6)); ax = fig.add_subplot(111, projection="3d")
        tris = box.vertices[box.faces] / IN
        n = box.face_normals
        sh = 0.55 + 0.45 * np.clip(n @ np.array([0.3, -0.5, 0.8]), 0, 1)
        cols = np.zeros((len(tris), 4)); cols[:, 0] = 0.30 * sh; cols[:, 1] = 0.55 * sh
        cols[:, 2] = 0.85 * sh; cols[:, 3] = 1
        ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none"))
        ax.set_xlim(-BOX_ACROSS_IN/2, BOX_ACROSS_IN/2); ax.set_ylim(-BOX_DEEP_IN/2, BOX_DEEP_IN/2)
        ax.set_zlim(0, 6)
        try: ax.set_box_aspect((BOX_ACROSS_IN, BOX_DEEP_IN, 6))
        except Exception: pass
        ax.view_init(elev=26, azim=-58)
        ax.set_xlabel("5 in"); ax.set_ylabel("7 in"); ax.set_zlabel("2 in")
        ax.set_title("drink_box.stl  -  5 x 7 x 2 inches")
        fig.tight_layout(); fig.savefig(os.path.join(RENDER_DIR, "drink_box.png"), dpi=110)
        plt.close(fig)

        # Top-down: WIDTH horizontal (14.5 in), LENGTH vertical (20 in), front at bottom
        fig, ax = plt.subplots(figsize=(8 * DRAWER_W_IN / DRAWER_L_IN * 1.3, 8))
        ax.add_patch(Rectangle((0, 0), DRAWER_W_IN, DRAWER_L_IN, fill=False, lw=3, ec="#444"))
        for (x0, y0, w, d, rot) in rects:
            ax.add_patch(Rectangle((x0, y0), w, d, fc="#cfe8ff", ec="#2b6cb0", lw=2))
            label = "7 wide\n5 deep" if rot else "5 wide\n7 deep"
            ax.text(x0 + w/2, y0 + d/2, label, ha="center", va="center", fontsize=11)
        ax.text(DRAWER_W_IN/2, (12 + DRAWER_L_IN)/2, "(space for other stuff)",
                ha="center", va="center", fontsize=10, color="#888", style="italic")
        ax.set_xlim(-1, DRAWER_W_IN + 1); ax.set_ylim(-1, DRAWER_L_IN + 1); ax.set_aspect("equal")
        ax.set_xlabel("14.5 in (across)"); ax.set_ylabel("20 in (front-to-back)")
        ax.set_title(f"{N_ACROSS*N_DEEP} boxes, 5 x 7 x 2 in each")
        fig.tight_layout(); fig.savefig(os.path.join(RENDER_DIR, "drawer_layout.png"), dpi=110)
        plt.close(fig)
    except Exception as e:
        print(f"(skipped renders: {e})")

    print("Box : 5 x 7 x 2 in  ->", os.path.basename(box_path))
    print(f"Fit : {N_ACROSS} across (2 x 5 = 10 in) x {N_DEEP} deep (2 x 7 = 14 in) "
          f"= {N_ACROSS*N_DEEP} boxes")


if __name__ == "__main__":
    main()
