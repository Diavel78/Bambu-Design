#!/usr/bin/env python3
"""
Generate drawer-organizer bins that file drink-mix packets ON EDGE.

Real-world inputs (measured against a tape measure):
  - Drawer:  20 in x 14.5 in x ~2.4 in deep  (508 x 368 x 61 mm)
  - Packets: ~4.25 in x ~1.25 in x ~0.2 in   (ICEE, Holloway, Laura Beverlin...)

The packets STAND ON EDGE (on their long 4.25 in edge, so ~1.25 in tall) and
file front-to-back like folders in a filing cabinet. You flip through them and
pull one out. A curved scoop in the front wall gives finger access.

Layout: 2 long trays running the length of the drawer, side by side across the
width. A full 20 in tray is too long for the H2D bed, so each tray is 2 pieces
-> a 2 x 2 grid of 4 identical bins that fills the whole drawer.

Output (models/drawer_organizer/):
  - drink_stick_box.stl          <- the bin to print (repeat 4 times)
  - drawer_layout_preview.stl    <- all bins arranged, just to eyeball the fit
  - renders/*.png                <- previews (bin WITH packets, + top-down map)

Parametric -- change the CONFIG block and re-run. Units are millimeters.
"""

import os
import numpy as np
import trimesh
from trimesh.creation import box as _box, cylinder as _cyl

# --------------------------------------------------------------------------- #
# CONFIG
# --------------------------------------------------------------------------- #
IN = 25.4  # mm per inch

# --- Drawer interior (measured) ---
DRAWER_L = 20.0 * IN     # 508 mm  (the 20 in run = filing direction)
DRAWER_W = 14.5 * IN     # 368 mm  (the 14.5 in run)
DRAWER_D = 2.4 * IN      # ~61 mm  (just under 2.5 in deep)

# --- Packet, standing on its long edge ---
PKT_BASE = 4.25 * IN     # ~108 mm  long edge sits on the floor (across the bin)
PKT_TALL = 1.25 * IN     # ~32 mm   how tall it stands
PKT_THICK = 0.20 * IN    # ~5 mm    thickness -> how tightly they file

# --- Grid: 2 trays down the length x 2 across the width = 4 bins ---
COLS = 2                 # bins along the 20 in run  (each ~10 in, prints on bed)
ROWS = 2                 # bins across the 14.5 in run
DRAWER_GAP = 2.0         # total slack per bin per axis (drop-in clearance)

# --- Bin build ---
BOX_H = 40.0             # ~1.6 in tall; packets stand 32 mm and peek out
WALL = 2.0              # wall thickness
FLOOR = 2.0             # floor thickness

# --- Front scoop (curved dip you flip through / pull a packet out) ---
SCOOP_DIP = 22.0         # how far the front wall is lowered at its center
SCOOP_R = 100.0          # arc radius (bigger = shallower, wider U)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "drawer_organizer")
RENDER_DIR = os.path.join(os.path.dirname(__file__), "..", "renders")

# --------------------------------------------------------------------------- #
# Derived bin footprint (tiles the drawer, minus drop-in clearance)
# --------------------------------------------------------------------------- #
BOX_L = DRAWER_L / COLS - DRAWER_GAP   # X, along the 20 in run (filing dir)
BOX_W = DRAWER_W / ROWS - DRAWER_GAP   # Y, across the 14.5 in run


def _diff(a, b):
    return trimesh.boolean.difference([a, b])


def make_bin():
    """One open-top bin with a curved scoop cut into its FRONT (-X) wall.

    Packets file along +X; their base (PKT_BASE) lies along Y; they stand PKT_TALL
    in Z. The scoop is on the -X wall so you reach in from the front.
    """
    outer = _box(extents=[BOX_L, BOX_W, BOX_H])
    outer.apply_translation([0, 0, BOX_H / 2.0])

    cav = _box(extents=[BOX_L - 2 * WALL, BOX_W - 2 * WALL, BOX_H])
    cav.apply_translation([0, 0, FLOOR + BOX_H / 2.0])
    shell = _diff(outer, cav)

    # Scoop: cylinder with axis along X, carving a downward arc into the -X wall.
    z_center = (BOX_H - SCOOP_DIP) + SCOOP_R
    cyl = _cyl(radius=SCOOP_R, height=WALL + 6.0, sections=96)
    cyl.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [0, 1, 0]))
    cyl.apply_translation([-BOX_L / 2.0 + WALL / 2.0, 0.0, z_center])
    binm = _diff(shell, cyl)
    binm.remove_unreferenced_vertices()
    return binm


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    binm = make_bin()
    box_path = os.path.join(OUT_DIR, "drink_stick_box.stl")
    binm.export(box_path)

    inner_len = BOX_L - 2 * WALL      # filing run (X)
    inner_wide = BOX_W - 2 * WALL     # across (Y)
    per_bin = max(1, int(inner_len // PKT_THICK))     # single file along X
    fits_base = inner_wide >= PKT_BASE
    total = per_bin * COLS * ROWS

    # Placement preview
    combo = []
    for c in range(COLS):
        for r in range(ROWS):
            m = binm.copy()
            x = -DRAWER_L / 2.0 + (c + 0.5) * (DRAWER_L / COLS)
            y = -DRAWER_W / 2.0 + (r + 0.5) * (DRAWER_W / ROWS)
            m.apply_translation([x, y, 0])
            combo.append(m)
    preview = trimesh.util.concatenate(combo)
    preview.export(os.path.join(OUT_DIR, "drawer_layout_preview.stl"))

    # ---- Renders ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        from matplotlib.patches import Rectangle
        os.makedirs(RENDER_DIR, exist_ok=True)

        # (1) One bin WITH packets standing on edge inside it
        fig = plt.figure(figsize=(7.5, 6))
        ax = fig.add_subplot(111, projection="3d")

        def add_mesh(mesh, base_rgb, light=(0.3, -0.5, 0.8)):
            tris = mesh.vertices[mesh.faces]
            n = mesh.face_normals
            sh = 0.55 + 0.45 * np.clip(n @ np.array(light), 0, 1)
            cols = np.zeros((len(tris), 4))
            for i in range(3):
                cols[:, i] = base_rgb[i] * sh
            cols[:, 3] = 1
            ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none"))

        add_mesh(binm, (0.32, 0.55, 0.85))
        # a handful of packets, standing on edge, filed from the front
        n_show = min(9, per_bin)
        x0 = -BOX_L / 2.0 + WALL + PKT_THICK
        for i in range(n_show):
            p = _box(extents=[PKT_THICK, PKT_BASE, PKT_TALL])
            p.apply_translation([x0 + i * (PKT_THICK + 7.0), 0.0, FLOOR + PKT_TALL / 2.0])
            shade = 0.75 if i % 2 else 0.9
            add_mesh(p, (shade, 0.18, 0.18))
        b = binm.bounds
        ax.set_xlim(b[0, 0], b[1, 0]); ax.set_ylim(b[0, 1], b[1, 1]); ax.set_zlim(0, 130)
        try: ax.set_box_aspect((BOX_L, BOX_W, 130))
        except Exception: pass
        ax.view_init(elev=24, azim=-72); ax.set_axis_off()
        ax.set_title(f"One bin ({BOX_L:.0f} x {BOX_W:.0f} x {BOX_H:.0f} mm)\n"
                     f"packets STAND ON EDGE, filed front-to-back")
        fig.tight_layout()
        fig.savefig(os.path.join(RENDER_DIR, "drink_stick_box.png"), dpi=110)
        plt.close(fig)

        # (2) Top-down map
        fig, ax = plt.subplots(figsize=(8, 8 * DRAWER_W / DRAWER_L))
        ax.add_patch(Rectangle((0, 0), DRAWER_L, DRAWER_W, fill=False, lw=3, ec="#444"))
        for c in range(COLS):
            for r in range(ROWS):
                x = c * (DRAWER_L / COLS) + DRAWER_GAP / 2
                y = r * (DRAWER_W / ROWS) + DRAWER_GAP / 2
                ax.add_patch(Rectangle((x, y), BOX_L, BOX_W, fc="#cfe8ff", ec="#2b6cb0", lw=2))
                # hint the filed packets as thin lines
                for k in range(6):
                    px = x + 10 + k * 12
                    ax.plot([px, px], [y + 12, y + 12 + PKT_BASE], color="#c53030", lw=3)
                ax.text(x + BOX_L / 2, y + BOX_W - 22, "file on edge  →",
                        ha="center", va="center", fontsize=9, color="#2b6cb0")
        ax.set_xlim(-10, DRAWER_L + 10); ax.set_ylim(-10, DRAWER_W + 10)
        ax.set_aspect("equal")
        ax.set_title(f"Drawer 20 x 14.5 in  |  {COLS*ROWS} bins (2 trays, split to print)  "
                     f"|  packets on edge")
        ax.set_xlabel("20 in (508 mm) - filing direction"); ax.set_ylabel("14.5 in (368 mm)")
        fig.tight_layout()
        fig.savefig(os.path.join(RENDER_DIR, "drawer_layout.png"), dpi=110)
        plt.close(fig)
        rendered = True
    except Exception as e:
        rendered = False
        print(f"(skipped renders: {e})")

    print("=" * 62)
    print("Drawer organizer generated  (STAND-ON-EDGE filing)")
    print("=" * 62)
    print(f"Drawer inside : {DRAWER_L:.0f} x {DRAWER_W:.0f} x {DRAWER_D:.0f} mm")
    print(f"Layout        : 2 trays down the length, split into {COLS*ROWS} bins "
          f"({COLS} x {ROWS})")
    print(f"Bin outside   : {BOX_L:.1f} x {BOX_W:.1f} x {BOX_H:.1f} mm "
          f"({BOX_L/IN:.1f} x {BOX_W/IN:.1f} x {BOX_H/IN:.1f} in)")
    print(f"Packet on edge: base {PKT_BASE:.0f} mm along Y "
          f"(fits {inner_wide:.0f} mm: {'YES' if fits_base else 'NO'}), "
          f"stands {PKT_TALL:.0f} mm")
    print(f"Capacity      : up to ~{per_bin} packets/bin filed on edge -> ~{total} total")
    print(f"Front scoop   : dips to {BOX_H-SCOOP_DIP:.0f} mm at center")
    print("-" * 62)
    print(f"PRINT: {box_path}  (x{COLS*ROWS})")
    if rendered:
        print("RENDERS: renders/drink_stick_box.png , renders/drawer_layout.png")


if __name__ == "__main__":
    main()
