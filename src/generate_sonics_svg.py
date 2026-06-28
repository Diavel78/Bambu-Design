#!/usr/bin/env python3
"""
Export the "sonics" logo as SVG files for a Cricut (or any vinyl cutter).

Produces:
  svg/sonics_layered_color.svg  - 3 stacked color layers (black/white/red).
                                  Cut each color from matching vinyl & layer.
  svg/sonics_text_only.svg      - just the letters, single color (HTV/decal).
  svg/sonics_outline_cut.svg    - the full plate silhouette as one cut line
                                  (sticker / single-color backer).

Reuses the exact same geometry as the 3D charm so they match perfectly.
"""

import os
import generate_sonics_charm as g  # reuse text_to_polygon, normalize, params

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "svg")

# Real-world size. Cricut reads mm; she can resize freely in Design Space.
TEXT_WIDTH_MM = 100.0   # ~4 inch wide word; scale up/down later as needed


def ring_to_path(ring, xmin, ymax):
    # SVG y-axis points down, so flip: sy = ymax - y
    pts = list(ring.coords)
    d = f"M {pts[0][0]-xmin:.3f} {ymax-pts[0][1]:.3f} "
    d += " ".join(f"L {x-xmin:.3f} {ymax-y:.3f}" for x, y in pts[1:])
    return d + " Z"


def poly_to_path(geom, xmin, ymax):
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    parts = []
    for p in polys:
        if p.is_empty:
            continue
        parts.append(ring_to_path(p.exterior, xmin, ymax))
        parts.extend(ring_to_path(r, xmin, ymax) for r in p.interiors)
    return " ".join(parts)


def svg_header(w, h):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{w:.3f}mm" height="{h:.3f}mm" '
            f'viewBox="0 0 {w:.3f} {h:.3f}">\n')


def write_svg(path, layers, bounds):
    """layers: list of (label, geom, fill). bounds from the largest geom."""
    xmin, ymin, xmax, ymax = bounds
    w, h = xmax - xmin, ymax - ymin
    with open(path, "w") as f:
        f.write(svg_header(w, h))
        for label, geom, fill in layers:
            d = poly_to_path(geom, xmin, ymax)
            f.write(f'  <g id="{label}">\n'
                    f'    <path d="{d}" fill="{fill}" '
                    f'fill-rule="evenodd" stroke="none"/>\n'
                    f'  </g>\n')
        f.write("</svg>\n")
    print(f"  wrote svg/{os.path.basename(path)}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    raw = g.text_to_polygon(g.TEXT, g.FONT_PATH)
    text = g.normalize(raw, TEXT_WIDTH_MM)
    outline = text.buffer(g.OUT_MARGIN / g.TEXT_WIDTH * TEXT_WIDTH_MM,
                          join_style=1)
    plate = text.buffer(g.PLATE_MARGIN / g.TEXT_WIDTH * TEXT_WIDTH_MM,
                        join_style=1)
    bounds = plate.bounds  # plate is the biggest -> use as canvas

    # Layered: bottom black plate, white base (text+outline), red letters on top.
    write_svg(os.path.join(OUT_DIR, "sonics_layered_color.svg"),
              [("black_plate", plate,   "#101010"),
               ("white_outline", outline, "#ffffff"),
               ("red_text", text,      "#c8102e")],
              bounds)

    # Text only, single color.
    write_svg(os.path.join(OUT_DIR, "sonics_text_only.svg"),
              [("red_text", text, "#c8102e")], text.bounds)

    # Full silhouette, single cut line (sticker / backer).
    write_svg(os.path.join(OUT_DIR, "sonics_outline_cut.svg"),
              [("silhouette", plate, "#101010")], plate.bounds)


if __name__ == "__main__":
    main()
