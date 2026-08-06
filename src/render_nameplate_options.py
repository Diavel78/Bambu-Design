#!/usr/bin/env python3
"""
Render the "pick one" sheets for the wall name plate: the same name drawn in
every available font, and in every color palette.

    python3 src/render_nameplate_options.py --name Elise

Writes ../renders/nameplate_font_options.png and nameplate_color_options.png.
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from shapely.affinity import translate as stranslate

import generate_nameplate as G


def _patch(ax, geom, color, z):
    ps = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for p in ps:
        if p.is_empty:
            continue
        v, c = [], []
        for ring in [p.exterior, *p.interiors]:
            a = np.asarray(ring.coords)
            v.extend(a)
            c.extend([Path.MOVETO] + [Path.LINETO] * (len(a) - 2) + [Path.CLOSEPOLY])
        ax.add_patch(PathPatch(Path(v, c), facecolor=color, edgecolor="none", zorder=z))


def draw(ax, polys, colors):
    def shade(h, f):
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
        return (r * f, g * f, b * f)

    def slab(geom, color, z_base, height, z0):
        steps = max(3, int(height * 3))
        for i in range(steps, 0, -1):
            t = (z_base + height * i / steps) * 0.42
            _patch(ax, stranslate(geom, t * 0.55, t * 0.42), shade(color, 0.58), z0 + i * 0.001)
        t = (z_base + height) * 0.42
        _patch(ax, stranslate(geom, t * 0.55, t * 0.42), color, z0 + 1)

    slab(polys["plate"],   colors["plate"],   0.0,                       G.PLATE_H,       10)
    slab(polys["outline"], colors["outline"], G.PLATE_H,                 G.OUTLINE_RAISE, 30)
    slab(polys["text"],    colors["text"],    G.PLATE_H + G.OUTLINE_RAISE, G.TEXT_RAISE,  50)
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off"); ax.margins(0.04)


def sheet(items, build, title_of, path, cols=2):
    rows = (len(items) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(7.0 * cols, 2.9 * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax in axes[len(items):]:
        ax.axis("off")
    for ax, item in zip(axes, items):
        polys, colors = build(item)
        draw(ax, polys, colors)
        ax.set_title(title_of(item), fontsize=13, loc="left", pad=6)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="#efe9e2")
    plt.close(fig)
    print(f"  -> {os.path.relpath(path, os.path.join(G.HERE, '..'))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=G.DEF_NAME)
    args = ap.parse_args()

    os.makedirs(G.OUT_RENDER, exist_ok=True)
    cache = {}

    def polys_for(font):
        if font not in cache:
            fp = os.path.join(G.FONT_DIR, G.FONTS[font])
            t = G.normalize(G.text_to_polygon(args.name, fp), G.DEF_WIDTH)
            cache[font] = G.connect_plate(t, G.PLATE_MARGIN)[0]
        return cache[font]

    fonts = sorted(G.FONTS)
    sheet(fonts,
          lambda f: (polys_for(f), G.PALETTES["purple"]),
          lambda f: f"{f}{'   <- current' if f == G.DEF_FONT else ''}",
          os.path.join(G.OUT_RENDER, "nameplate_font_options.png"))

    pals = sorted(G.PALETTES)
    sheet(pals,
          lambda p: (polys_for(G.DEF_FONT), G.PALETTES[p]),
          lambda p: f"{p}{'   <- current' if p == 'purple' else ''}",
          os.path.join(G.OUT_RENDER, "nameplate_color_options.png"))


if __name__ == "__main__":
    main()
