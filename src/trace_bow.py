#!/usr/bin/env python3
"""Trace the cheer-bow clipart into clean shapely polygons.

The clipart is 5 disjoint black pieces (2 loops, 2 tails, center knot),
separated by thin white lines. We trace each, classify them, and return
them scaled to a target width with the origin at the bow center.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import label
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.affinity import scale as sscale, translate as stranslate


def _largest_ring(component_mask):
    fig, ax = plt.subplots()
    cs = ax.contour(np.pad(component_mask.astype(float), 2), levels=[0.5])
    segs = cs.allsegs[0]
    plt.close(fig)
    best, ba = None, -1
    for s in segs:
        p = Polygon(s)
        if not p.is_valid:
            p = p.buffer(0)
        if p.area > ba:
            best, ba = p, p.area
    return best


def trace(image_path, target_w, simplify=2.0, smooth=1.5):
    arr = np.array(Image.open(image_path).convert("L"))
    mask = arr < 128
    lab, n = label(mask)
    comps = []
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() < 500:                      # ignore specks
            continue
        poly = _largest_ring(m)
        poly = poly.simplify(simplify).buffer(smooth).buffer(-smooth)
        poly = stranslate(sscale(poly, 1, -1, origin=(0, 0)), 0, 0)  # flip y
        comps.append(poly)

    comps.sort(key=lambda p: p.area, reverse=True)
    loops = comps[0:2]
    tails = comps[2:4]
    knot  = comps[4]
    loops.sort(key=lambda p: p.centroid.x)     # [left, right]
    tails.sort(key=lambda p: p.centroid.x)

    parts = {"loop_l": loops[0], "loop_r": loops[1],
             "tail_l": tails[0], "tail_r": tails[1], "knot": knot}

    # scale everything together to target width, center at origin
    allp = loops + tails + [knot]
    minx = min(p.bounds[0] for p in allp); maxx = max(p.bounds[2] for p in allp)
    miny = min(p.bounds[1] for p in allp); maxy = max(p.bounds[3] for p in allp)
    s = target_w / (maxx - minx)
    cx = (minx + maxx) / 2.0; cy = (miny + maxy) / 2.0
    def fix(p):
        p = stranslate(p, -cx, -cy)
        return sscale(p, s, s, origin=(0, 0))
    return {k: fix(v) for k, v in parts.items()}


if __name__ == "__main__":
    import os
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    P = "/tmp/claude-0/-home-user-Bambu-Design/3de4930d-4a07-5cb4-8e0b-355775576f3b/scratchpad/"
    parts = trace(P + "uploads/img_09.png", 92.0)
    colors = {"loop_l": "#f2f2f2", "loop_r": "#f2f2f2",
              "tail_l": "#101010", "tail_r": "#101010", "knot": "#c8102e"}
    fig, ax = plt.subplots(figsize=(6, 6))
    for k, poly in parts.items():
        gs = list(poly.geoms) if poly.geom_type == "MultiPolygon" else [poly]
        for p in gs:
            ax.add_patch(PathPatch(Path(np.asarray(p.exterior.coords)),
                                   facecolor=colors[k], edgecolor="#101010", lw=2))
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    fig.savefig(P + "trace_color.png", dpi=140, bbox_inches="tight", facecolor="#bfbfbf")
    print("saved trace_color.png")
    for k, v in parts.items():
        b = v.bounds
        print(f"  {k}: bounds=({b[0]:.0f},{b[1]:.0f})-({b[2]:.0f},{b[3]:.0f})")
