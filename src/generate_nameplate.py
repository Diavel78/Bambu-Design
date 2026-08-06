#!/usr/bin/env python3
"""
Generate a big multi-color wall NAME PLATE for 3D printing.

Inspired by the layered "bubble letter" nursery signs: a chunky back plate with
an offset drop shadow, a colored halo/outline hugging the letters, and tall
cream letters sitting proud on top.

Output, per name, into ../models/nameplate_<name>/:
  - 3 separate color bodies (plate / outline / text) as STL
  - one combined single-color STL
  - one STEP file (editable CAD)
Plus a shaded 3/4-view PNG preview in ../renders/.

Designed for a Bambu Lab H2D + AMS (multi-color). Units are millimeters.

    python3 src/generate_nameplate.py --name Elise
    python3 src/generate_nameplate.py --name Elise --width 300 --font TitanOne
    python3 src/generate_nameplate.py --name Elise --colors mint
"""

import argparse
import os
import textwrap
import zipfile

import cadquery as cq
from cadquery import Vector, Wire, Face, Solid
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely.affinity import scale as sscale, translate as stranslate

HERE        = os.path.dirname(os.path.abspath(__file__))
FONT_DIR    = os.path.join(HERE, "..", "fonts")
OUT_MODELS  = os.path.join(HERE, "..", "models")
OUT_RENDER  = os.path.join(HERE, "..", "renders")

# --------------------------------------------------------------------------- #
# CONFIG -- defaults; most are overridable on the command line.
# --------------------------------------------------------------------------- #
DEF_NAME   = "Elise"
DEF_FONT   = "Chewy"          # bubbly marker font, closest to the inspiration pic
DEF_WIDTH  = 230.0            # width of the WORD in mm (plate ends up ~+30 mm)

# The three colors are stacked as three clean Z bands -- plate, then halo, then
# letters -- so the whole sign only needs TWO filament changes on the AMS
# instead of one per layer. Purge waste drops from hundreds of grams to ~20 g.
PLATE_H       = 4.0    # back plate thickness            (z 0        -> 4)
OUTLINE_RAISE = 2.0    # halo slab on top of the plate   (z 4        -> 6)
TEXT_RAISE    = 3.0    # letters on top of the halo      (z 6        -> 9)
OUT_MARGIN    = 5.0    # width of the colored halo around the letters
PLATE_MARGIN  = 5.0    # how far the back plate extends past that halo

SHADOW = (3.0, -3.0)   # (dx, dy) offset of the back plate -> drop-shadow look

# Keyhole hangers milled into the BACK of the plate (open to the build plate,
# so they print with no supports). Big hole takes the screw head, narrow slot
# below it takes the shank once the sign drops down onto the screw.
HANGER = dict(
    head_d   = 9.0,    # screw-head clearance hole
    slot_w   = 5.0,    # shank slot width
    slot_len = 12.0,   # how far the sign drops onto the screw
    depth    = 2.6,    # pocket depth (leaves PLATE_H - depth as back wall)
    inset_x  = 0.30,   # hanger x position as a fraction of plate half-width
)

# Bambu bed sizes, used only for the "will this fit?" warning.
BEDS = {"H2D": (350, 320), "X1C / P1S": (256, 256), "A1": (256, 256),
        "A1 mini": (180, 180)}

FONTS = {
    "Chewy":         "Chewy-Regular.ttf",          # rounded hand-drawn bubble
    "TitanOne":      "TitanOne-Regular.ttf",       # fat, super chunky bubble
    "BubblegumSans": "BubblegumSans-Regular.ttf",  # tilted, playful
    "LuckiestGuy":   "LuckiestGuy-Regular.ttf",    # comic-book all caps
    "Boogaloo":      "Boogaloo-Regular.ttf",       # tall and skinny fun
    "Sniglet":       "Sniglet-Regular.ttf",        # soft rounded
    "Pacifico":      "Pacifico-Regular.ttf",       # flowing script
}

# (plate = deep shadow, outline = halo, text = letters)
PALETTES = {
    "purple":  dict(plate="#4a1d6e", outline="#9b51e0", text="#faf3e8"),
    "pink":    dict(plate="#8e2a5b", outline="#f06fa8", text="#fff4f0"),
    "teal":    dict(plate="#0f4c5c", outline="#2ec4b6", text="#fdfcf2"),
    "mint":    dict(plate="#2b6a4f", outline="#7bd8a5", text="#fffaf0"),
    "sunset":  dict(plate="#7a2d12", outline="#ff9f45", text="#fff6e5"),
    "rainbow": dict(plate="#3b2a5a", outline="#ffd166", text="#ffffff"),
}


# --------------------------------------------------------------------------- #
# Font -> 2D shapely polygon (with holes for the counters in e, s, o ...)
# --------------------------------------------------------------------------- #
def _signed_area(coords):
    a = 0.0
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def text_to_polygon(text, font_path, size=400.0):
    """Convert text to a filled shapely polygon using non-zero winding.

    Outer contours and inner counters are wound in opposite directions. Take the
    winding of the largest contour as "solid", union those, subtract the rest.
    """
    fp = FontProperties(fname=font_path)
    tp = TextPath((0, 0), text, size=size, prop=fp)
    contours = [c for c in tp.to_polygons() if len(c) >= 4]
    if not contours:
        raise ValueError(f"font produced no outlines for {text!r}")
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


def _npieces(geom):
    return 1 if geom.geom_type == "Polygon" else len(geom.geoms)


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
        if p.is_empty or p.area < 1e-6:
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
# Geometry
# --------------------------------------------------------------------------- #
def build_polys(text_poly, plate_margin):
    """The three 2D footprints: back plate (with drop shadow), halo, text.

    The halo is a SOLID slab, not a ring -- the letters sit on top of it, so
    only its rim is ever visible, but keeping it solid means each Z band is a
    single color and the letters get a full base underneath them.
    """
    halo  = text_poly.buffer(OUT_MARGIN, join_style=1, quad_segs=24)
    base  = halo.buffer(plate_margin, join_style=1, quad_segs=24)
    # Union the base with a copy offset by SHADOW -> a chunky drop shadow that
    # peeks out from one side, exactly like the inspiration photo.
    plate = unary_union([base, stranslate(base, SHADOW[0], SHADOW[1])])
    plate = plate.buffer(0.4, join_style=1).buffer(-0.4, join_style=1)  # smooth
    return dict(plate=plate, outline=halo, text=text_poly)


def connect_plate(text_poly, start_margin):
    """Grow the plate margin until the whole sign is ONE connected piece.

    A sign that comes off the bed as five loose letters is not a sign, so this
    walks the margin up (to a sane cap) until the letters bridge together.
    """
    margin = start_margin
    for _ in range(40):
        polys = build_polys(text_poly, margin)
        if _npieces(polys["plate"]) == 1:
            return polys, margin
        margin += 0.5
    return polys, margin


def keyhole_poly(cx, cy):
    """Back-face keyhole: screw-head circle on top, drop-down slot beneath."""
    head = Point(cx, cy).buffer(HANGER["head_d"] / 2.0, quad_segs=24)
    slot = box(cx - HANGER["slot_w"] / 2.0, cy - HANGER["slot_len"],
               cx + HANGER["slot_w"] / 2.0, cy)
    tip  = Point(cx, cy - HANGER["slot_len"]).buffer(HANGER["slot_w"] / 2.0,
                                                     quad_segs=16)
    return unary_union([head, slot, tip])


def place_hangers(plate_poly):
    """Find two fully-supported spots for the keyhole pockets, at the SAME y.

    Scans downward from the top of the plate for the highest y at which BOTH
    keyhole footprints (plus a wall clearance) still sit inside the plate. Equal
    heights matter -- two hangers at different y hang the sign crooked.
    """
    minx, miny, maxx, maxy = plate_poly.bounds
    half = (maxx - minx) / 2.0
    cx0  = (minx + maxx) / 2.0
    clearance = 2.0
    xs = [cx0 - half * HANGER["inset_x"], cx0 + half * HANGER["inset_x"]]

    y = maxy - HANGER["head_d"] / 2.0 - clearance
    while y > miny:
        if all(plate_poly.contains(keyhole_poly(cx, y).buffer(clearance))
               for cx in xs):
            return [(cx, y) for cx in xs]
        y -= 0.5

    # Nowhere works at a shared height (very irregular outline) -- fall back to
    # a single centered hanger rather than hanging the sign crooked.
    y = maxy - HANGER["head_d"] / 2.0 - clearance
    while y > miny:
        if plate_poly.contains(keyhole_poly(cx0, y).buffer(clearance)):
            return [(cx0, y)]
        y -= 0.5
    return []


def build_bodies(polys, hangers):
    plate   = extrude(polys["plate"],   0.0,                     PLATE_H)
    outline = extrude(polys["outline"], PLATE_H,                 OUTLINE_RAISE)
    text    = extrude(polys["text"],    PLATE_H + OUTLINE_RAISE, TEXT_RAISE)

    for (cx, cy) in hangers:
        pocket = extrude(keyhole_poly(cx, cy), -0.1, HANGER["depth"] + 0.1)
        if pocket is not None:
            plate = plate.cut(pocket)

    return {"plate": plate, "outline": outline, "text": text}


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def export(name, bodies):
    d = os.path.join(OUT_MODELS, name)
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


def make_zip(name, info):
    """Bundle the STLs + a printing cheat-sheet into one importable zip.

    The three color parts have to be imported together to line up, so shipping
    them as a single zip is the difference between "works" and "which files?".
    """
    d = os.path.join(OUT_MODELS, name)
    readme = textwrap.dedent(f"""\
        {info['title']}
        {'=' * len(info['title'])}

        A layered multi-color wall name plate for a Bambu Lab printer.

        Size   : {info['w']:.0f} x {info['h']:.0f} x {info['z']:.1f} mm
                 (the word itself is {info['word']:.0f} mm wide)
        Font   : {info['font']}
        Hangers: {info['hangers']} keyhole slot(s) recessed into the back
        Fits   : {info['fits']}

        MULTI-COLOR (recommended)
        -------------------------
        1. Load 3 filaments. Suggested: deep purple / bright purple / cream.
        2. Bambu Studio -> File -> Import -> Import 3MF/STL, and select ALL
           THREE of these at once:
               {name}_plate.stl
               {name}_outline.stl
               {name}_text.stl
        3. It asks "Load these files as a single object?" -> click YES.
           They share an origin, so they snap together exactly.
        4. In the Objects list, expand the object and set each part's filament:
               _plate   -> deep purple   (back plate + drop shadow)
               _outline -> bright purple (the halo around the letters)
               _text    -> cream / white (the letters)
        5. Slice and print.

        SINGLE COLOR
        ------------
        Import {name}_combined.stl on its own. Nothing else needed.

        PRINT SETTINGS
        --------------
        Material    : PLA
        Layer height: 0.2 mm
        Walls       : 3
        Infill      : 10-15% gyroid
        Supports    : OFF  (every layer sits on the one below it)
        Orientation : flat, as loaded -- letters up, back on the build plate

        Only TWO filament changes for the whole print: the colors are stacked as
        three clean height bands (plate 0-4 mm, halo 4-6 mm, letters 6-9 mm), so
        purge waste stays around 20 g.

        HANGING IT
        ----------
        Two keyhole pockets are recessed into the back, {info['span']:.0f} mm apart and level
        with each other. Put two screws or drywall anchors in the wall {info['span']:.0f} mm
        apart, leave the heads about 3 mm proud, hook the sign on through the
        round holes and slide it down -- the shank locks into the narrow slot.
        There is a {PLATE_H - HANGER['depth']:.1f} mm wall behind each pocket, so nothing reaches
        the front face.
        """)

    zpath = os.path.join(d, f"{name}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for part in ("plate", "outline", "text", "combined"):
            f = os.path.join(d, f"{name}_{part}.stl")
            z.write(f, os.path.basename(f))
        z.writestr("PRINT-ME.txt", readme)
    mb = os.path.getsize(zpath) / 1e6
    print(f"  zipped   -> models/{name}/{name}.zip ({mb:.1f} MB)")


# --------------------------------------------------------------------------- #
# Preview: fake-3D by stacking each layer's outline as offset "side wall" copies
# --------------------------------------------------------------------------- #
def render_preview(name, polys, hangers, colors):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    import numpy as np

    fig, ax = plt.subplots(figsize=(11, 6))

    def shade(hexcolor, f):
        r, g, b = (int(hexcolor[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
        return (r * f, g * f, b * f)

    def patch(geom, color, z):
        ps = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in ps:
            if p.is_empty:
                continue
            v, c = [], []
            for ring in [p.exterior, *p.interiors]:
                a = np.asarray(ring.coords)
                v.extend(a)
                c.extend([Path.MOVETO] + [Path.LINETO] * (len(a) - 2)
                         + [Path.CLOSEPOLY])
            ax.add_patch(PathPatch(Path(v, c), facecolor=color,
                                   edgecolor="none", zorder=z))

    def slab(geom, color, z_base, height, z0):
        """Draw an extruded slab: dark side walls, then the lit top face."""
        steps = max(3, int(height * 3))
        for i in range(steps, 0, -1):
            t = (z_base + height * i / steps) * 0.42
            patch(stranslate(geom, t * 0.55, t * 0.42), shade(color, 0.58),
                  z0 + i * 0.001)
        t = (z_base + height) * 0.42
        patch(stranslate(geom, t * 0.55, t * 0.42), color, z0 + 1)

    slab(polys["plate"],   colors["plate"],   0.0,                     PLATE_H,       10)
    slab(polys["outline"], colors["outline"], PLATE_H,                 OUTLINE_RAISE, 30)
    slab(polys["text"],    colors["text"],    PLATE_H + OUTLINE_RAISE, TEXT_RAISE,    50)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    ax.margins(0.06)
    os.makedirs(OUT_RENDER, exist_ok=True)
    out = os.path.join(OUT_RENDER, f"{name}.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="#efe9e2")
    plt.close(fig)
    print(f"  preview  -> renders/{name}.png")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Generate a layered wall name plate.")
    ap.add_argument("--name",  default=DEF_NAME)
    ap.add_argument("--font",  default=DEF_FONT, choices=sorted(FONTS))
    ap.add_argument("--width", type=float, default=DEF_WIDTH,
                    help="width of the word in mm (default %(default)s)")
    ap.add_argument("--colors", default="purple", choices=sorted(PALETTES),
                    help="preview palette only; you pick real filament in Studio")
    ap.add_argument("--no-hangers", action="store_true",
                    help="skip the keyhole pockets (tape / Command strips instead)")
    ap.add_argument("--out", default=None, help="output folder name")
    args = ap.parse_args()

    font_path = os.path.join(FONT_DIR, FONTS[args.font])
    out_name  = args.out or f"nameplate_{args.name.lower()}"

    raw  = text_to_polygon(args.name, font_path)
    text = normalize(raw, args.width)

    polys, margin = connect_plate(text, PLATE_MARGIN)
    if _npieces(polys["plate"]) != 1:
        print("  !! letters will NOT join into one piece -- try a wider font "
              "or a bigger --width")
    elif margin > PLATE_MARGIN:
        print(f"  note: grew plate margin {PLATE_MARGIN} -> {margin:.1f} mm so "
              f"the letters join into one piece")

    hangers = [] if args.no_hangers else place_hangers(polys["plate"])
    bodies  = build_bodies(polys, hangers)

    minx, miny, maxx, maxy = polys["plate"].bounds
    w, h = maxx - minx, maxy - miny
    total_z = PLATE_H + OUTLINE_RAISE + TEXT_RAISE
    print(f"[{out_name}]  font={args.font}  word={args.width:.0f} mm")
    print(f"  plate {w:.0f} x {h:.0f} x {total_z:.1f} mm, "
          f"{len(hangers)} keyhole hanger(s)")
    fits = [p for p, (bx, by) in BEDS.items()
            if (w <= bx - 5 and h <= by - 5) or (h <= bx - 5 and w <= by - 5)]
    print(f"  fits on: {', '.join(fits) if fits else 'NO Bambu bed -- reduce --width'}")

    export(out_name, bodies)
    span = abs(hangers[0][0] - hangers[-1][0]) if len(hangers) > 1 else 0.0
    make_zip(out_name, dict(
        title=f"{args.name} -- wall name plate", font=args.font,
        word=args.width, w=w, h=h, z=total_z, hangers=len(hangers),
        span=span, fits=", ".join(fits) if fits else "no Bambu bed as-is"))
    render_preview(out_name, polys, hangers, PALETTES[args.colors])


if __name__ == "__main__":
    main()
