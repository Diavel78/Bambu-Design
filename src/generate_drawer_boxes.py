#!/usr/bin/env python3
"""
Generate a set of open-top organizer bins that tile a drawer.

Default layout is the hand-drawn sketch: a 20" x 16.4" drawer, 2" deep, split
into 8 compartments -- two 6" columns of two, then an 8" column of four.

Any compartment too big for the build plate is automatically sliced into equal
segments that DO fit. Each segment is one printable bin, and segments sit end to
end in the drawer so they read as one long compartment.

Output (all in mm, the unit slicers expect):
  - models/drawer_boxes/bin_<id>.stl     one per printable bin
  - models/drawer_boxes/bin_<id>.step    editable CAD
  - models/drawer_boxes/bambu/plate_*.3mf  ready-to-slice Bambu Studio plates
  - models/drawer_boxes/drawer_assembly.step   every bin, positioned in the drawer
  - models/drawer_boxes/PRINT_LIST.md    what to print, how many, est. filament
  - renders/drawer_layout.png            top-down plan of the drawer
  - renders/drawer_bins_3d.png           the bins in place

Everything is parametric -- edit the CONFIG block (or pass CLI flags) and re-run.

    python3 generate_drawer_boxes.py                # H2D plates
    python3 generate_drawer_boxes.py --printer x1c  # 256 x 256 plates
"""

import argparse
import math
import os

import cadquery as cq
from cadquery import exporters

# --------------------------------------------------------------------------- #
# CONFIG -- change these and re-run to iterate.
# --------------------------------------------------------------------------- #
MM = 25.4  # inches -> mm

# The drawer being filled (inches), straight off the sketch.
DRAWER_W = 20.0   # along the drawer
DRAWER_D = 16.4   # across the drawer
DRAWER_H = 2.0    # "2" deep"

# The sketch layout: columns across the 20", each split into rows.
# Column widths must sum to DRAWER_W; each column's rows must sum to DRAWER_D.
LAYOUT = [
    dict(name="A", width=6.0, rows=[8.2, 8.2]),
    dict(name="B", width=6.0, rows=[8.2, 8.2]),
    dict(name="C", width=8.0, rows=[4.1, 4.1, 4.1, 4.1]),
]

# Printer build volume (mm). Pick with --printer; H2D is the default.
PRINTERS = {
    "h2d":    (350.0, 320.0, 325.0),
    "x1c":    (256.0, 256.0, 256.0),
    "p1s":    (256.0, 256.0, 256.0),
    "p1p":    (256.0, 256.0, 256.0),
    "a1":     (256.0, 256.0, 256.0),
    "a1mini": (180.0, 180.0, 180.0),
}
PRINTER = "h2d"
PLATE_X, PLATE_Y, PLATE_Z = PRINTERS[PRINTER]
PLATE_MARGIN = 8.0     # keep bins off the very edge of the plate
PLATE_SPACING = 6.0    # gap between bins arranged on the same plate

# Bin construction (mm).
WALL       = 2.0       # side wall thickness
FLOOR      = 1.6       # floor thickness
CORNER_R   = 4.0       # outside corner radius
RIM_CHAMF  = 0.5       # little chamfer on the top rim so it feels finished
BIN_GAP    = 0.8       # gap between neighbouring bins (and at the drawer walls)
LID_GAP    = 2.8       # how far the bin top sits below the drawer lip

FILAMENT_DENSITY = 1.24  # g/cm3, PLA -- for the filament estimate only

HERE       = os.path.dirname(os.path.abspath(__file__))
OUT_MODELS = os.path.join(HERE, "..", "models", "drawer_boxes")
OUT_RENDER = os.path.join(HERE, "..", "renders")


# --------------------------------------------------------------------------- #
# Layout: sketch -> compartments -> printable bins
# --------------------------------------------------------------------------- #
def compartments(layout, drawer_d):
    """Walk the column/row spec and yield placed compartments, in inches.

    Origin is the front-left corner of the drawer; y grows toward the back, so
    the first row of a column (top of the sketch) lands at the back.
    """
    total_w = sum(c["width"] for c in layout)
    if abs(total_w - DRAWER_W) > 1e-6:
        raise ValueError(f"columns sum to {total_w}\", drawer is {DRAWER_W}\"")

    out = []
    x = 0.0
    for col in layout:
        if abs(sum(col["rows"]) - drawer_d) > 1e-6:
            raise ValueError(f"column {col['name']} rows sum to "
                             f"{sum(col['rows'])}\", drawer is {drawer_d}\"")
        y = drawer_d
        for i, h in enumerate(col["rows"], start=1):
            y -= h
            cid = f"{col['name']}{i}"
            out.append(dict(id=cid, comp_id=cid, col=col["name"],
                            x=x, y=y, w=col["width"], d=h))
        x += col["width"]
    return out


def fits_plate(w_mm, d_mm):
    """A bin fits if it fits the plate in either orientation."""
    ux, uy = PLATE_X - 2 * PLATE_MARGIN, PLATE_Y - 2 * PLATE_MARGIN
    return (w_mm <= ux and d_mm <= uy) or (w_mm <= uy and d_mm <= ux)


def split_to_fit(comp):
    """Slice one compartment into the fewest equal segments that fit the plate.

    Splits along whichever axis is longer, which is what you want for the long
    skinny compartments in this drawer.
    """
    for n in range(1, 25):
        for axis in ("x", "y"):
            w = comp["w"] / n if axis == "x" else comp["w"]
            d = comp["d"] / n if axis == "y" else comp["d"]
            if fits_plate(w * MM - BIN_GAP, d * MM - BIN_GAP):
                if n == 1:
                    return [dict(comp, seg=1, of=1, w=w, d=d)]
                segs = []
                for i in range(n):
                    segs.append(dict(
                        comp,
                        id=f"{comp['id']}-{i + 1}", seg=i + 1, of=n, w=w, d=d,
                        x=comp["x"] + (i * w if axis == "x" else 0.0),
                        y=comp["y"] + (i * d if axis == "y" else 0.0),
                    ))
                return segs
    raise ValueError(f"compartment {comp['id']} cannot be split to fit the plate")


def plan(layout=LAYOUT, drawer_d=DRAWER_D):
    comps = compartments(layout, drawer_d)
    bins = [b for c in comps for b in split_to_fit(c)]
    return comps, bins


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #
def make_bin(w_mm, d_mm, h_mm):
    """An open-top bin: filleted outside corners, flat floor, chamfered rim."""
    outer = (cq.Workplane("XY")
             .rect(w_mm, d_mm).extrude(h_mm)
             .edges("|Z").fillet(min(CORNER_R, w_mm / 2 - 0.1, d_mm / 2 - 0.1)))

    iw, idp = w_mm - 2 * WALL, d_mm - 2 * WALL
    inner_r = max(0.6, CORNER_R - WALL)
    cavity = (cq.Workplane("XY").workplane(offset=FLOOR)
              .rect(iw, idp).extrude(h_mm)
              .edges("|Z").fillet(min(inner_r, iw / 2 - 0.1, idp / 2 - 0.1)))

    body = outer.cut(cavity)
    try:
        body = body.faces(">Z").chamfer(RIM_CHAMF)
    except Exception:
        pass  # chamfer is cosmetic -- never let it sink the build
    return body


def grams(solid):
    return solid.val().Volume() / 1000.0 * FILAMENT_DENSITY


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build(args):
    os.makedirs(OUT_MODELS, exist_ok=True)
    os.makedirs(OUT_RENDER, exist_ok=True)

    # Clear bins from a previous layout so stale files can't get printed.
    for f in os.listdir(OUT_MODELS):
        if f.startswith("bin_") and f.endswith((".stl", ".step")):
            os.remove(os.path.join(OUT_MODELS, f))

    comps, bins = plan()
    bin_h = DRAWER_H * MM - LID_GAP

    rows, total_g = [], 0.0
    assy = cq.Assembly(name="drawer")
    shapes = {}

    for b in bins:
        w_mm = b["w"] * MM - BIN_GAP
        d_mm = b["d"] * MM - BIN_GAP
        key = (round(w_mm, 3), round(d_mm, 3))
        if key not in shapes:
            shapes[key] = make_bin(w_mm, d_mm, bin_h)
        body = shapes[key]

        stl = os.path.join(OUT_MODELS, f"bin_{b['id']}.stl")
        stp = os.path.join(OUT_MODELS, f"bin_{b['id']}.step")
        exporters.export(body, stl, tolerance=0.01, angularTolerance=0.1)
        exporters.export(body, stp)

        # Place a copy in the drawer assembly (centre of its slot).
        cx = (b["x"] + b["w"] / 2) * MM
        cy = (b["y"] + b["d"] / 2) * MM
        assy.add(body, name=f"bin_{b['id']}", loc=cq.Location(cq.Vector(cx, cy, 0)))

        g = grams(body)
        total_g += g
        rows.append(dict(id=b["id"], comp=b["comp_id"], seg=b["seg"], of=b["of"],
                         w_in=b["w"], d_in=b["d"], w_mm=w_mm, d_mm=d_mm, g=g))
        print(f"  bin_{b['id']:<6} {b['w']:>5.2f} x {b['d']:>5.2f} in   "
              f"{w_mm:>6.1f} x {d_mm:>5.1f} x {bin_h:.1f} mm   ~{g:.0f} g")

    assy.save(os.path.join(OUT_MODELS, "drawer_assembly.step"))

    print(f"\n  Bambu Studio plates ({PRINTER.upper()}, "
          f"{PLATE_X:.0f} x {PLATE_Y:.0f} mm):")
    plates = export_plates(rows)

    write_print_list(rows, comps, bin_h, total_g, plates)
    if not args.no_render:
        render_plan(comps, bins)
        render_3d(comps, bins)
    print(f"\n  {len(rows)} bins on {len(plates)} plates, "
          f"~{total_g:.0f} g of filament total")
    print(f"  models -> {os.path.normpath(OUT_MODELS)}")


# --------------------------------------------------------------------------- #
# Bambu Studio plates (.3mf)
# --------------------------------------------------------------------------- #
def grid_fit(w, d):
    """How many of one bin size fit on a plate, and in which orientation."""
    ux, uy = PLATE_X - 2 * PLATE_MARGIN, PLATE_Y - 2 * PLATE_MARGIN
    sp = PLATE_SPACING
    best = None
    for a, b, rot in ((w, d, False), (d, w, True)):
        nx = int((ux + sp) // (a + sp))
        ny = int((uy + sp) // (b + sp))
        if nx >= 1 and ny >= 1 and (best is None or nx * ny > best[0]):
            best = (nx * ny, nx, ny, a, b, rot)
    if best is None:
        raise ValueError(f"a {w:.1f} x {d:.1f} mm bin does not fit the plate")
    return best


def grid_positions(n, nx, a, b):
    """Bed centres for n bins in a row-major grid, centred on the plate."""
    sp = PLATE_SPACING
    cols = min(n, nx)
    rows_used = math.ceil(n / nx)
    block_w = cols * a + (cols - 1) * sp
    block_d = rows_used * b + (rows_used - 1) * sp
    x0 = PLATE_X / 2 - block_w / 2 + a / 2
    y0 = PLATE_Y / 2 - block_d / 2 + b / 2
    return [(x0 + (i % nx) * (a + sp), y0 + (i // nx) * (b + sp))
            for i in range(n)]


def export_plates(rows):
    """Write one ready-to-slice .3mf per build plate."""
    import trimesh
    from threemf import write_3mf

    out_dir = os.path.join(OUT_MODELS, "bambu")
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.endswith(".3mf"):
            os.remove(os.path.join(out_dir, f))

    groups = {}
    for r in rows:
        groups.setdefault((round(r["w_mm"], 2), round(r["d_mm"], 2)), []).append(r)

    plates, n = [], 0
    for (w, d), members in groups.items():
        cap, nx, _ny, a, b, rot = grid_fit(w, d)
        rep = members[0]["id"]
        mesh = trimesh.load(os.path.join(OUT_MODELS, f"bin_{rep}.stl"))
        if rot:
            mesh = mesh.copy()
            mesh.apply_transform(trimesh.transformations.rotation_matrix(
                math.pi / 2, [0, 0, 1]))
        key = f"bin_{rep}"

        # Spread evenly over the fewest plates rather than filling each to the
        # brim -- 2 + 2 beats 3 + 1 for a lonely last print.
        n_plates = math.ceil(len(members) / cap)
        per = math.ceil(len(members) / n_plates)

        for i in range(0, len(members), per):
            chunk = members[i:i + per]
            n += 1
            name = f"plate_{n}_{key}_x{len(chunk)}.3mf"
            path = os.path.join(out_dir, name)
            write_3mf(path, {key: mesh},
                      [(key, x, y) for x, y in grid_positions(len(chunk), nx, a, b)],
                      title=f"{key} x{len(chunk)}")
            plates.append(dict(file=name, bin=key, qty=len(chunk),
                               fills=[c["comp"] for c in chunk],
                               rotated=rot))
            print(f"  {name:<34} {len(chunk)} x {key}"
                  f"{'  (rotated 90deg to fit)' if rot else ''}")

    verify_plates(out_dir, plates)
    return plates


def verify_plates(out_dir, plates):
    """Re-read every .3mf and prove it's valid and inside the build volume.

    Parsed with the stdlib rather than a mesh library, so this checks the bytes
    that actually got written -- indices in range, one item per bin, nothing
    hanging off the plate.
    """
    import xml.etree.ElementTree as ET
    import zipfile
    from threemf import NS

    tag = lambda t: f"{{{NS}}}{t}"  # noqa: E731

    for p in plates:
        with zipfile.ZipFile(os.path.join(out_dir, p["file"])) as z:
            missing = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
            missing -= set(z.namelist())
            if missing:
                raise ValueError(f"{p['file']}: missing {sorted(missing)}")
            root = ET.fromstring(z.read("3D/3dmodel.model"))

        objects = {}
        for o in root.iter(tag("object")):
            verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z")))
                     for v in o.iter(tag("vertex"))]
            for t in o.iter(tag("triangle")):
                for k in ("v1", "v2", "v3"):
                    if not 0 <= int(t.get(k)) < len(verts):
                        raise ValueError(f"{p['file']}: triangle index out of range")
            objects[o.get("id")] = verts

        items = list(root.iter(tag("item")))
        if len(items) != p["qty"]:
            raise ValueError(f"{p['file']}: {len(items)} items, expected {p['qty']}")

        for it in items:
            verts = objects[it.get("objectid")]
            tx, ty, tz = (float(v) for v in it.get("transform").split()[-3:])
            xs = [v[0] + tx for v in verts]
            ys = [v[1] + ty for v in verts]
            zs = [v[2] + tz for v in verts]
            if min(xs) < 0 or max(xs) > PLATE_X or min(ys) < 0 or max(ys) > PLATE_Y:
                raise ValueError(f"{p['file']}: bin off the {PLATE_X:.0f} x "
                                 f"{PLATE_Y:.0f} mm plate")
            if min(zs) < -1e-6 or max(zs) > PLATE_Z:
                raise ValueError(f"{p['file']}: bin outside the Z envelope")


def write_print_list(rows, comps, bin_h, total_g, plates=None):
    """One markdown table telling you exactly what to print."""
    lines = [
        "# Drawer bins — print list",
        "",
        f"Drawer: **{DRAWER_W}\" x {DRAWER_D}\" x {DRAWER_H}\" deep** "
        f"({DRAWER_W * MM:.0f} x {DRAWER_D * MM:.0f} x {DRAWER_H * MM:.0f} mm).",
        f"Bin height **{bin_h:.1f} mm**, walls {WALL} mm, floor {FLOOR} mm, "
        f"{BIN_GAP} mm gap between bins.",
        "",
        "## Compartments (as drawn)",
        "",
        "| Compartment | Size | Printed as |",
        "|---|---|---|",
    ]
    by_comp = {}
    for r in rows:
        by_comp.setdefault(r["comp"], []).append(r)
    for c in comps:
        segs = by_comp.get(c["id"], [])
        n = segs[0]["of"] if segs else 1
        how = "1 bin" if n == 1 else f"{n} bins end to end"
        lines.append(f"| {c['id']} | {c['w']}\" x {c['d']}\" | {how} |")

    # Group identical footprints -- one STL printed N times.
    groups = {}
    for r in rows:
        key = (round(r["w_mm"], 2), round(r["d_mm"], 2))
        groups.setdefault(key, []).append(r)

    lines += [
        "",
        "## What to print",
        "",
        "Bins of the same size are the same model — print the one STL as many "
        "times as the quantity says.",
        "",
        "| Print this | Size (in) | Size (mm) | Qty | Fills | Filament |",
        "|---|---|---|---|---|---|",
    ]
    for g in groups.values():
        first = g[0]
        fills = ", ".join(sorted({r["comp"] for r in g}))
        lines.append(
            f"| `bin_{first['id']}.stl` | {first['w_in']:.2f} x {first['d_in']:.2f} "
            f"| {first['w_mm']:.1f} x {first['d_mm']:.1f} | **{len(g)}x** "
            f"| {fills} | ~{first['g'] * len(g):.0f} g |")
    lines += [
        "",
        f"**Total: {len(rows)} bins from {len(groups)} unique models, "
        f"~{total_g:.0f} g (~{total_g / 1000:.1f} kg) of filament.**",
        "",
    ]

    if plates:
        lines += [
            "## Straight into Bambu Studio",
            "",
            f"`bambu/` holds one **.3mf per build plate**, already arranged for "
            f"the **{PRINTER.upper()}** ({PLATE_X:.0f} x {PLATE_Y:.0f} mm). Open "
            "one, pick your filament, slice, print. No arranging needed.",
            "",
            "| Plate file | Holds | Fills |",
            "|---|---|---|",
        ]
        for p in plates:
            lines.append(f"| `bambu/{p['file']}` | {p['qty']} x `{p['bin']}.stl`"
                         f"{' (rotated to fit)' if p['rotated'] else ''} "
                         f"| {', '.join(p['fills'])} |")
        lines += [
            "",
            "Prefer to arrange yourself? Every bin is also exported as its own "
            "`bin_<id>.stl` and `.step`.",
            "",
        ]
    path = os.path.join(OUT_MODELS, "PRINT_LIST.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))


# --------------------------------------------------------------------------- #
# Top-down plan drawing
# --------------------------------------------------------------------------- #
def render_plan(comps, bins):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(13, 8.8))
    palette = ["#dbe9f6", "#e6f0dc", "#fbe7d5", "#ece0f2",
               "#d9efee", "#fae3e6", "#f6f0cd", "#e6ded6"]

    ax.add_patch(Rectangle((0, 0), DRAWER_W, DRAWER_D, facecolor="#f7f7f7",
                           edgecolor="#222", lw=2.5, zorder=0))

    for i, c in enumerate(comps):
        ax.add_patch(Rectangle((c["x"], c["y"]), c["w"], c["d"],
                               facecolor=palette[i % len(palette)],
                               edgecolor="#222", lw=2.0, zorder=1))
        halo = dict(boxstyle="round,pad=0.22", facecolor="white",
                    edgecolor="none", alpha=0.88)
        ax.text(c["x"] + c["w"] / 2, c["y"] + c["d"] / 2 + 0.34, c["id"],
                ha="center", va="center", fontsize=15, weight="bold",
                color="#222", zorder=4, bbox=halo)
        ax.text(c["x"] + c["w"] / 2, c["y"] + c["d"] / 2 - 0.44,
                f'{c["w"]}" x {c["d"]}"', ha="center", va="center",
                fontsize=11, color="#444", zorder=4, bbox=halo)

    # Dashed lines where a compartment is split into separate printed bins.
    for b in bins:
        if b["of"] > 1 and b["seg"] > 1:
            ax.plot([b["x"], b["x"]], [b["y"], b["y"] + b["d"]],
                    ls=(0, (5, 4)), color="#b1252f", lw=1.8, zorder=3)

    split = [b for b in bins if b["of"] > 1]
    if split:
        ax.plot([], [], ls=(0, (5, 4)), color="#b1252f", lw=1.8,
                label="split — separate printed bins, sit end to end")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.13),
                  frameon=False, fontsize=11)

    # Overall dimensions.
    ax.annotate("", xy=(0, -0.75), xytext=(DRAWER_W, -0.75),
                arrowprops=dict(arrowstyle="<->", color="#222", lw=1.4))
    ax.text(DRAWER_W / 2, -1.25, f'{DRAWER_W}"', ha="center", va="top", fontsize=13)
    ax.annotate("", xy=(-0.75, 0), xytext=(-0.75, DRAWER_D),
                arrowprops=dict(arrowstyle="<->", color="#222", lw=1.4))
    ax.text(-1.25, DRAWER_D / 2, f'{DRAWER_D}"', ha="right", va="center",
            fontsize=13, rotation=90)

    ax.set_title(f'Drawer organizer — {DRAWER_W}" x {DRAWER_D}" x '
                 f'{DRAWER_H}" deep   ({len(bins)} printable bins)',
                 fontsize=16, weight="bold", pad=14)
    ax.set_xlim(-2.6, DRAWER_W + 0.8)
    ax.set_ylim(-2.6, DRAWER_D + 0.8)
    ax.set_aspect("equal")
    ax.axis("off")
    path = os.path.join(OUT_RENDER, "drawer_layout.png")
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  plan   -> {os.path.normpath(path)}")


def render_3d(comps, bins):
    """Isometric preview of every bin sitting in the drawer, from the STLs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    wheel = [(0.42, 0.60, 0.78), (0.55, 0.70, 0.42), (0.90, 0.62, 0.33),
             (0.62, 0.48, 0.76), (0.35, 0.68, 0.66), (0.85, 0.44, 0.48),
             (0.45, 0.55, 0.85), (0.80, 0.70, 0.35)]
    base = {c["id"]: wheel[i % len(wheel)] for i, c in enumerate(comps)}
    light = np.array([0.42, -0.55, 0.72])
    light /= np.linalg.norm(light)

    elev, azim = 38.0, -62.0
    e, a = math.radians(elev), math.radians(azim)
    eye = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a),
                    math.sin(e)])

    tris, cols = [], []
    for b in bins:
        m = trimesh.load(os.path.join(OUT_MODELS, f"bin_{b['id']}.stl"))
        m.apply_translation([(b["x"] + b["w"] / 2) * MM,
                             (b["y"] + b["d"] / 2) * MM, 0.0])
        n = np.asarray(m.face_normals)
        keep = (n @ eye) > 1e-6          # cull back faces -- mpl's painter
        v = np.asarray(m.triangles)[keep]  # sort alone leaves artifacts
        shade = 0.30 + 0.70 * np.clip(n[keep] @ light, 0.0, 1.0)
        c = np.array(base[b["comp_id"]])
        tris.append(v)
        cols.append(np.clip(c[None, :] * shade[:, None], 0, 1))

    tris = np.concatenate(tris)
    cols = np.concatenate(cols)
    order = np.argsort(-(tris.mean(axis=1) @ eye))  # far faces drawn first
    tris, cols = tris[order], cols[order]

    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111, projection="3d")
    # Matching edge colour closes the antialiasing hairlines between triangles.
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors=cols,
                                         linewidths=0.3))

    W, D = DRAWER_W * MM, DRAWER_D * MM
    ax.set_xlim(0, W)
    ax.set_ylim(0, D)
    ax.set_zlim(0, max(W, D) * 0.42)
    ax.set_box_aspect((W, D, max(W, D) * 0.42))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(f'{len(bins)} bins in place — {DRAWER_W}" x {DRAWER_D}" drawer',
                 fontsize=16, weight="bold", y=0.90)
    path = os.path.join(OUT_RENDER, "drawer_bins_3d.png")
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  3d     -> {os.path.normpath(path)}")


def main():
    global PRINTER, PLATE_X, PLATE_Y, PLATE_Z

    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-render", action="store_true",
                   help="skip the PNG plan (no matplotlib needed)")
    p.add_argument("--printer", default=PRINTER, choices=sorted(PRINTERS),
                   help="build plate to arrange the .3mf plates for "
                        f"(default: {PRINTER})")
    args = p.parse_args()

    PRINTER = args.printer
    PLATE_X, PLATE_Y, PLATE_Z = PRINTERS[PRINTER]

    print(f'Drawer {DRAWER_W}" x {DRAWER_D}" x {DRAWER_H}" deep\n')
    build(args)


if __name__ == "__main__":
    main()
