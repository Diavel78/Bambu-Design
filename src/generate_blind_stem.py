#!/usr/bin/env python3
"""
Generate a replacement VERTICAL BLIND VANE STEM (a.k.a. carrier clip / vane
hanger) for 3D printing.

This is the little clear plastic hook that sticks out of each carrier
(traveler) in the headrail and that the vane (slat) hangs from. The hook end
snaps off constantly and the whole blind piece falls down.

Output (in ../models/blind_stem/):
  - blind_stem.stl          one replacement stem (duplicate in the slicer!)
  - blind_stem.step         editable CAD file
  - blind_stem_fit_test.stl three short shank-only test pieces (S/M/L) to
                            check the fit in the carrier socket before
                            committing to full prints. 1 notch = small,
                            2 = medium (default size), 3 = large.
Plus a dimensioned side-view diagram in ../renders/blind_stem.png so you can
compare against your broken part with a ruler/calipers.

Everything is parametric -- measure your blind, tweak the CONFIG block,
re-run:  python3 src/generate_blind_stem.py

Units are millimeters.
"""

import os
import cadquery as cq

# --------------------------------------------------------------------------- #
# CONFIG -- measure the broken stem / carrier socket and tweak these.
# --------------------------------------------------------------------------- #

# ---- Shank: the part that pushes into the rectangular socket in the carrier.
# Pull the broken stub out with needle-nose pliers and measure it, or measure
# the socket opening itself. Print the fit-test piece first!
SHANK_L = 12.0   # how deep it inserts into the carrier
SHANK_W = 9.5    # width of the socket opening (side to side)
SHANK_T = 3.0    # thickness of the socket opening (top to bottom)
BARB    = True   # small ridge on top that clicks in so it can't slide out
BARB_H  = 0.5

# ---- Collar: flat plate that stops against the carrier face.
COLLAR_T = 2.0
COLLAR_W = 12.0
COLLAR_H = 10.0

# ---- Blade: the flat hook arm the vane actually hangs from.
# Standard US vane punch hole is ~14.3 x 6.4 mm (9/16" x 1/4"), so the
# defaults below pass through it with room to spare.
BLADE_L   = 22.0  # collar face to tip
BLADE_W   = 9.5   # blade width (must be narrower than the vane hole width)
BLADE_T0  = 3.2   # thickness at the collar (thicker = stronger)
BLADE_T1  = 1.6   # thickness at the tip (thinner = easy to thread the vane on)

# ---- Notch & bump: the vane's hole edge rests in the notch; the bump in
# front keeps it from sliding back off.
NOTCH_X = 4.5   # where the notch starts (from the collar face)
NOTCH_W = 2.6   # notch width -- must swallow the vane material (~1 mm)
NOTCH_D = 1.6   # notch depth
BUMP_W  = 3.5   # retention bump right after the notch
BUMP_H  = 1.2

# ---- Fit-test size steps (S/M/L = default -/+ these amounts)
FIT_STEP_W = 0.3
FIT_STEP_T = 0.2

OUT_DIR    = os.path.join(os.path.dirname(__file__), "..", "models", "blind_stem")
RENDER_DIR = os.path.join(os.path.dirname(__file__), "..", "renders")

# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #

def build_stem(shank_w=SHANK_W, shank_t=SHANK_T, full=True):
    """Build one stem. full=False -> shank + collar only (fit test)."""
    # Collar, centered on the blade root
    z_mid = -BLADE_T0 / 2.0
    collar = (
        cq.Workplane("XY")
        .box(COLLAR_T, COLLAR_W, COLLAR_H, centered=True)
        .translate((-COLLAR_T / 2.0, 0, z_mid))
    )

    # Shank
    shank = (
        cq.Workplane("XY")
        .box(SHANK_L, shank_w, shank_t, centered=True)
        .translate((-COLLAR_T - SHANK_L / 2.0, 0, z_mid))
    )
    # chamfer the leading (insertion) end
    shank = shank.edges("|Y and <X").chamfer(min(0.8, shank_t / 3.0))

    body = collar.union(shank)

    if BARB:
        # small triangular ridge on top of the shank, near the far end:
        # ramps up going in, square face pointing back out so it clicks in.
        bx = -COLLAR_T - SHANK_L + 3.0   # barb face position
        barb = (
            cq.Workplane("XZ")
            .moveTo(bx, z_mid + shank_t / 2.0)
            .lineTo(bx - 2.5, z_mid + shank_t / 2.0)
            .lineTo(bx, z_mid + shank_t / 2.0 + BARB_H)
            .close()
            .extrude(shank_w * 0.6, both=False)
            .translate((0, shank_w * 0.3, 0))
        )
        body = body.union(barb)

    if not full:
        return body

    # Blade: 2D side profile extruded across the width, then centered on Y
    n0, n1 = NOTCH_X, NOTCH_X + NOTCH_W
    b1 = n1 + BUMP_W
    tip = BLADE_L
    profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(n0, 0)
        .sagittaArc((n1, 0), -NOTCH_D)    # notch scoop (XZ plane: -sag = dip)
        .sagittaArc((b1, 0), BUMP_H)      # retention bump
        .lineTo(tip - 1.2, -0.5)
        .lineTo(tip, -1.0)                # blunt rounded-ish tip edge
        .lineTo(tip - 2.5, -BLADE_T1 - 0.9)   # underside chamfer at the tip
        .lineTo(0, -BLADE_T0)             # tapered underside back to the collar
        .close()
    )
    blade = profile.extrude(BLADE_W / 2.0, both=True)
    return body.union(blade)


def build_fit_test():
    """Three short shank+collar pieces (S/M/L), notch-marked, on one plate."""
    pieces = []
    for i, (dw, dt) in enumerate([(-FIT_STEP_W, -FIT_STEP_T), (0, 0),
                                  (FIT_STEP_W, FIT_STEP_T)]):
        p = build_stem(shank_w=SHANK_W + dw, shank_t=SHANK_T + dt, full=False)
        # notch marks on the collar face: 1=S, 2=M, 3=L
        for k in range(i + 1):
            mark = (
                cq.Workplane("XY")
                .box(1.2, 1.2, 2.0, centered=True)
                .translate((0.0, -4.0 + k * 3.0, -BLADE_T0 / 2.0 + COLLAR_H / 2.0))
            )
            p = p.cut(mark)
        pieces.append(p.translate((0, 0, i * 0)))  # placeholder, spaced below
    plate = pieces[0].translate((0, -16, 0))
    plate = plate.union(pieces[1])
    plate = plate.union(pieces[2].translate((0, 16, 0)))
    return plate


def diagram(path):
    """Dimensioned side-view sketch so the user can sanity-check sizes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(9, 4.5))
    n0, n1 = NOTCH_X, NOTCH_X + NOTCH_W
    b1 = n1 + BUMP_W

    # blade outline (matches build_stem)
    xs, zs = [0, n0], [0, 0]
    t = np.linspace(0, np.pi, 24)
    xs += list(n0 + (n1 - n0) * (1 - np.cos(t)) / 2); zs += list(-NOTCH_D * np.sin(t))
    xs += list(n1 + (b1 - n1) * (1 - np.cos(t)) / 2); zs += list(BUMP_H * np.sin(t))
    xs += [BLADE_L - 1.2, BLADE_L, BLADE_L - 2.5, 0, 0]
    zs += [-0.5, -1.0, -BLADE_T1 - 0.9, -BLADE_T0, 0]
    ax.fill(xs, zs, color="#9ecbff", ec="#1f5fa8", lw=1.5, zorder=3)

    # collar + shank
    zm = -BLADE_T0 / 2
    ax.fill([-COLLAR_T, 0, 0, -COLLAR_T],
            [zm - COLLAR_H / 2, zm - COLLAR_H / 2, zm + COLLAR_H / 2, zm + COLLAR_H / 2],
            color="#cfe3f7", ec="#1f5fa8", lw=1.5, zorder=2)
    x0 = -COLLAR_T - SHANK_L
    ax.fill([x0, -COLLAR_T, -COLLAR_T, x0],
            [zm - SHANK_T / 2, zm - SHANK_T / 2, zm + SHANK_T / 2, zm + SHANK_T / 2],
            color="#cfe3f7", ec="#1f5fa8", lw=1.5, zorder=2)

    def dim(x0_, x1_, y, label):
        ax.annotate("", (x0_, y), (x1_, y), arrowprops=dict(arrowstyle="<->", color="k"))
        ax.text((x0_ + x1_) / 2, y - 0.9, label, ha="center", fontsize=9)

    dim(x0, -COLLAR_T, zm - SHANK_T / 2 - 2.5, f"shank {SHANK_L} × {SHANK_W}w × {SHANK_T}t")
    dim(0, BLADE_L, -BLADE_T0 - 3.5, f"blade {BLADE_L} × {BLADE_W}w")
    ax.annotate("vane hole edge\nrests here", (n0 + NOTCH_W / 2, -NOTCH_D),
                xytext=(n0 + 2, 4.5), fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="->", color="k"))
    ax.annotate("bump keeps it\nfrom sliding off", ((n1 + b1) / 2, BUMP_H),
                xytext=(b1 + 6, 4.5), fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="->", color="k"))
    ax.text(x0 - 1, zm, "into\ncarrier →", ha="right", va="center", fontsize=9)

    ax.set_aspect("equal"); ax.set_xlim(x0 - 10, BLADE_L + 12); ax.set_ylim(-12, 8)
    ax.set_title("Replacement vertical-blind vane stem — side view (mm)")
    ax.axis("off")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    print("wrote", path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RENDER_DIR, exist_ok=True)

    stem = build_stem()
    cq.exporters.export(stem, os.path.join(OUT_DIR, "blind_stem.stl"))
    cq.exporters.export(stem, os.path.join(OUT_DIR, "blind_stem.step"))
    print("wrote blind_stem.stl / .step")

    fit = build_fit_test()
    cq.exporters.export(fit, os.path.join(OUT_DIR, "blind_stem_fit_test.stl"))
    print("wrote blind_stem_fit_test.stl")

    diagram(os.path.join(RENDER_DIR, "blind_stem.png"))


if __name__ == "__main__":
    main()
