#!/usr/bin/env python3
"""
Package everything printable in this repo into one zip.

The zip is the deliverable -- run this after generating models and hand the
single file over, rather than sending files one at a time.

    python3 src/make_zip.py                 # -> dist/Bambu-Design-print-files.zip
    python3 src/make_zip.py --only boxes    # just the drawer bins

The zip is regenerated from scratch every run and is NOT committed (see
.gitignore) -- it is a build output, not a source file.
"""

import argparse
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT_DIR = os.path.join(ROOT, "dist")

# What goes in the zip: (folder in the zip, folder in the repo, group name).
SECTIONS = [
    ("drawer_boxes", "models/drawer_boxes", "boxes"),
    ("cheer_charms/keychain", "models/keychain", "charms"),
    ("cheer_charms/bagcharm", "models/bagcharm", "charms"),
    ("cheer_charms/croc", "models/croc", "charms"),
    ("cheer_bows/bow_eden", "models/bow_eden", "bows"),
    ("cricut_svg", "svg", "charms"),
    ("previews", "renders", "all"),
]


def human(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


def collect(only):
    """Every file to pack, as (path_in_zip, path_on_disk)."""
    out = []
    for zip_dir, repo_dir, group in SECTIONS:
        if only and group not in (only, "all"):
            continue
        src = os.path.join(ROOT, repo_dir)
        if not os.path.isdir(src):
            continue
        for dirpath, _dirs, files in os.walk(src):
            for f in sorted(files):
                if f.startswith("."):
                    continue
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, src)
                out.append((os.path.join(zip_dir, rel), full))
    return out


def index_text(entries):
    """A short READ ME dropped in at the top of the zip."""
    by_dir = {}
    for zip_path, full in entries:
        by_dir.setdefault(os.path.dirname(zip_path), []).append((zip_path, full))

    lines = [
        "# Bambu-Design — print files",
        "",
        "Everything in this zip is ready to print. Start here:",
        "",
        "## Drawer organizer bins (20\" x 16.4\" x 2\" deep)",
        "",
        "**`drawer_boxes/bambu/` — open these in Bambu Studio and hit Slice.**",
        "The bins are already arranged on the plate; nothing to position.",
        "Two bins per plate, four plates, eight bins total.",
        "",
        "`drawer_boxes/PRINT_LIST.md` has the full table, sizes and filament",
        "estimates. Individual `.stl` and `.step` files are there too if you'd",
        "rather arrange plates yourself.",
        "",
        "## Cheer charms and bows",
        "",
        "`cheer_charms/` and `cheer_bows/` hold the multi-color \"sonics\" charms.",
        "Each folder has `_plate` (black), `_outline` (white) and `_text` (red)",
        "to load as one object for AMS printing, plus a `_combined.stl` for",
        "single-color. `cricut_svg/` is for cutting, not printing.",
        "",
        "## Everything in here",
        "",
        "| Folder | Files | Size |",
        "|---|---|---|",
    ]
    for d in sorted(by_dir):
        size = sum(os.path.getsize(f) for _z, f in by_dir[d])
        lines.append(f"| `{d}/` | {len(by_dir[d])} | {human(size)} |")
    lines += ["", "Regenerate any of it with `python3 src/generate_drawer_boxes.py`.", ""]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", choices=["boxes", "charms", "bows"],
                   help="pack just one group instead of everything")
    p.add_argument("--name", help="output file name (default depends on --only)")
    args = p.parse_args(argv)

    entries = collect(args.only)
    if not entries:
        raise SystemExit("nothing to pack -- generate the models first")

    os.makedirs(OUT_DIR, exist_ok=True)
    name = args.name or (f"Bambu-Design-{args.only}.zip" if args.only
                         else "Bambu-Design-print-files.zip")
    path = os.path.join(OUT_DIR, name)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr("READ_ME_FIRST.md", index_text(entries))
        for zip_path, full in entries:
            z.write(full, zip_path)

    raw = sum(os.path.getsize(f) for _z, f in entries)
    print(f"  {len(entries)} files, {human(raw)} -> {human(os.path.getsize(path))}")
    print(f"  {os.path.relpath(path, ROOT)}")
    return path


if __name__ == "__main__":
    main()
