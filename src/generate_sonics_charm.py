#!/usr/bin/env python3
"""
Generate a multi-color "sonics" cheer-team charm for 3D printing.

Output, per attachment variant (keychain / bagcharm / croc):
  - 3 separate color bodies (plate=black, outline=white, text=red) as STL
  - one combined single-color STL
  - one STEP file (editable CAD)
Plus a colored top-view PNG preview per variant in ../renders/.

Designed for a Bambu Lab H2D + AMS (multi-color). Units are millimeters.

The whole thing is parametric -- tweak the CONFIG block and re-run.
"""

import os
import cadquery as cq
from cadquery import Vector, Wire, Face, Solid
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.affinity import scale as sscale, translate as stranslate

# --------------------------------------------------------------------------- #
# CONFIG -- change these and re-run to iterate.
# --------------------------------------------------------------------------- #
TEXT          = "sonics"
FONT_PATH     = os.path.join(os.path.dirname(__file__), "..", "fonts",
                             "UnifrakturCook-Bold.ttf")

TEXT_WIDTH    = 50.0   # width of the word in mm (the headline dimension)

PLATE_H       = 2.4    # black backing plate thickness
PLATE_MARGIN  = 3.2    # how far the black halo extends past the letters
OUT_MARGIN    = 1.2    # width of the white outline around the letters
OUTLINE_RAISE = 0.6    # how far the white outline sits above the plate
TEXT_RAISE    = 1.0    # how far the red text sits above the plate (taller = pops)

# Attachment loops (keychain / bag charm). Radii in mm.
LOOP = {
    "keychain": dict(outer_r=5.0,  hole_r=2.5),   # 5 mm hole: keyrings / split rings
    "bagcharm": dict(outer_r=7.0,  hole_r=4.0),   # 8 mm hole: lobster clasps
}
LOOP_BRIDGE_W = 7.0    # width of the bar that ties the loop to the plate

# Croc / Jibbitz rivet (EXPERIMENTAL -- expect to test-fit and tweak).
CROC = dict(
    neck_d   = 10.0,   # diameter of the part passing through the croc hole
    neck_h   = 3.0,    # croc material thickness
    back_d   = 13.0,   # back flange that grips inside the shoe
    back_h   = 1.4,
)

OUT_DIR_MODELS = os.path.join(os.path.dirname(__file__), "..", "models")
OUT_DIR_RENDER = os.path.join(os.path.dirname(__file__), "..", "renders")

COLORS = {"plate": "#101010", "outline": "#f2f2f2", "text": "#c8102e"}

# --------------------------------------------------------------------------- #
# Font -> 2D shapely polygon (with holes for letter counters)
# --------------------------------------------------------------------------- #
def _signed_area(coords):
    a = 0.0
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def text_to_polygon(text, font_path, size=200.0):
    """Convert text to a filled shapely polygon using non-zero winding.

    TrueType outer contours and inner counters (the holes in o, c, etc.) are
    wound in opposite directions. We pick the winding of the largest contour as
    "solid", union all solids, then subtract all opposite-wound holes. This is
    robust for fonts (like this blackletter) whose glyph strokes overlap.
    """
    fp = FontProperties(fname=font_path)
    tp = TextPath((0, 0), text, size=size, prop=fp)
    contours = [c for c in tp.to_polygons() if len(c) >= 4]
    areas = [_signed_area(c) for c in contours]
    solid_sign = 1.0 if areas[max(range(len(areas)),
                                  key=lambda i: abs(areas[i]))] > 0 else -1.0

    def poly(c):
        p = Polygon(c)
        return p if p.is_valid else p.buffer(0)

    shells = [poly(c) for c, a in zip(contours, areas)
              if (a > 0) == (solid_sign > 0)]
    holes  = [poly(c) for c, a in zip(contours, areas)
              if (a > 0) != (solid_sign > 0)]
    result = unary_union(shells)
    if holes:
        result = result.difference(unary_union(holes))
    return result


def normalize(poly, target_width):
    minx, miny, maxx, maxy = poly.bounds
    s = target_width / (maxx - minx)
    poly = sscale(poly, xfact=s, yfact=s, origin=(0, 0))
    minx, miny, maxx, maxy = poly.bounds
    return stranslate(poly, -(minx + maxx) / 2.0, -(miny + maxy) / 2.0)


# --------------------------------------------------------------------------- #
# shapely 2D -> CadQuery 3D extrusion
# --------------------------------------------------------------------------- #
def _wire(coords, z):
    pts = [Vector(float(x), float(y), z) for (x, y) in coords[:-1]]  # drop dup
    return Wire.makePolygon(pts, close=True)


def extrude(geom, z0, h):
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    solids = []
    for p in polys:
        if p.is_empty:
            continue
        outer = _wire(list(p.exterior.coords), z0)
        inner = [_wire(list(r.coords), z0) for r in p.interiors]
        face = Face.makeFromWires(outer, inner)
        solids.append(Solid.extrudeLinear(face, Vector(0, 0, h)))
    if not solids:
        return None
    body = solids[0]
    for s in solids[1:]:
        body = body.fuse(s)
    return body


# --------------------------------------------------------------------------- #
# Build the three color bodies for a given variant
# --------------------------------------------------------------------------- #
def build_variant(text_poly, variant):
    outline_poly = text_poly.buffer(OUT_MARGIN, join_style=1)
    plate_poly   = text_poly.buffer(PLATE_MARGIN, join_style=1)
    white_ring   = outline_poly.difference(text_poly)

    rivet = None  # extra solid added later (croc)

    if variant in LOOP:
        spec = LOOP[variant]
        top_y = plate_poly.bounds[3]
        cy = top_y + spec["outer_r"] - 1.0           # 1 mm overlap onto plate
        disc = Point(0.0, cy).buffer(spec["outer_r"])
        bridge = Polygon([(-LOOP_BRIDGE_W / 2, top_y - 2.0),
                          ( LOOP_BRIDGE_W / 2, top_y - 2.0),
                          ( LOOP_BRIDGE_W / 2, cy),
                          (-LOOP_BRIDGE_W / 2, cy)])
        plate_poly = unary_union([plate_poly, disc, bridge])
        plate_poly = plate_poly.difference(Point(0.0, cy).buffer(spec["hole_r"]))

    plate   = extrude(plate_poly,   0.0,      PLATE_H)
    outline = extrude(white_ring,   PLATE_H,  OUTLINE_RAISE)
    text    = extrude(text_poly,    PLATE_H,  TEXT_RAISE)

    if variant == "croc":
        cx, cyc = plate_poly.centroid.x, plate_poly.centroid.y
        neck = (cq.Workplane("XY", origin=(cx, cyc, 0))
                .circle(CROC["neck_d"] / 2).extrude(-CROC["neck_h"]))
        back = (cq.Workplane("XY", origin=(cx, cyc, -CROC["neck_h"]))
                .circle(CROC["back_d"] / 2).extrude(-CROC["back_h"]))
        rivet = neck.val().fuse(back.val())
        plate = plate.fuse(rivet)

    bodies = {"plate": plate, "outline": outline, "text": text}

    # For the croc variant, flip it rivet-up / face-down so it prints with no
    # supports (smooth front against the build plate).
    if variant == "croc":
        zmin = min(b.BoundingBox().zmin for b in bodies.values())
        bodies = {k: v.mirror("XY").translate((0, 0, -zmin))
                  for k, v in bodies.items()}

    return bodies, dict(text=text_poly, outline=white_ring, plate=plate_poly)


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def export_variant(name, bodies):
    d = os.path.join(OUT_DIR_MODELS, name)
    os.makedirs(d, exist_ok=True)

    for color, body in bodies.items():
        cq.exporters.export(cq.Workplane(obj=body),
                            os.path.join(d, f"{name}_{color}.stl"))

    combined = bodies["plate"].fuse(bodies["outline"]).fuse(bodies["text"])
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

    def patch(geom, color, z):
        polylist = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in polylist:
            verts, codes = [], []
            for ring in [p.exterior, *p.interiors]:
                c = np.asarray(ring.coords)
                verts.extend(c)
                codes.extend([Path.MOVETO] + [Path.LINETO] * (len(c) - 2)
                             + [Path.CLOSEPOLY])
            ax.add_patch(PathPatch(Path(verts, codes), facecolor=color,
                                   edgecolor="none", zorder=z))

    fig, ax = plt.subplots(figsize=(6, 4))
    patch(polys["plate"],   COLORS["plate"],   1)
    patch(polys["outline"], COLORS["outline"], 2)
    patch(polys["text"],    COLORS["text"],    3)
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    ax.margins(0.05)
    os.makedirs(OUT_DIR_RENDER, exist_ok=True)
    out = os.path.join(OUT_DIR_RENDER, f"{name}.png")
    fig.savefig(out, dpi=160, bbox_inches="tight",
                facecolor="#bfbfbf")
    plt.close(fig)
    print(f"  preview  -> renders/{name}.png")


# --------------------------------------------------------------------------- #
def main():
    raw = text_to_polygon(TEXT, FONT_PATH)
    text_poly = normalize(raw, TEXT_WIDTH)
    print(f"Text outline ready. Letters connect into "
          f"{'one piece' if raw.geom_type == 'Polygon' else 'multiple pieces'}.")

    for variant in ("keychain", "bagcharm", "croc"):
        print(f"[{variant}]")
        bodies, polys = build_variant(text_poly, variant)
        export_variant(variant, bodies)
        render_preview(variant, polys)


if __name__ == "__main__":
    main()
