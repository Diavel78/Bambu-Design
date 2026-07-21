# Drink-stick drawer organizer

Open-top boxes that turn a **20 × 14.5 × ~2.4 in** drawer into an organized
file of drink-mix **stick packets** (ICEE, Liquid Death, LMNT, etc. —
~4.25 × 1.25 in). The sticks stand up and file front-to-back like index cards,
and a curved **scoop** in the front wall lets you see the flavors and slide one
out.

No baseplate, no Gridfinity — **just boxes**. Sized to fill the drawer, so they
can't slide around.

![box](../../renders/drink_stick_box.png)
![layout](../../renders/drawer_layout.png)

## What to print

| File | What | Print how many |
|------|------|----------------|
| `drink_stick_box.stl` | One box (125 × 182 × 38 mm), scooped front | **8×** (they're all identical) |
| `drawer_layout_preview.stl` | All 8 arranged in the drawer | **don't print** — just to eyeball the fit |

**Layout:** 8 identical boxes, **4 across × 2 deep**, fills the 20 × 14.5 in
floor with a few mm of drop-in slack. Each box holds **~17 sticks** of one
flavor → **~136 sticks** total. Put the **scooped side facing you**.

## Print settings (Bambu H2D, one color)

| Setting | Value |
|---|---|
| Material | PLA (or PETG) |
| Layer height | 0.2–0.28 mm (these are just bins — go fast) |
| Walls | 3 |
| Infill | 10–15% |
| Supports | **None** (scoop is a gentle arc, prints fine) |
| Orientation | As-is, open side up |
| Per plate | ~4 boxes fit an H2D plate → 2 plates for all 8 |

Each box is ~86 cm³ / roughly 100–110 g of filament and a couple hours.

## Want it different? It's parametric

Edit the CONFIG block in `src/generate_drawer_organizer.py` and re-run
`python3 src/generate_drawer_organizer.py`. Common tweaks:

- **More, smaller compartments:** set `ROWS = 3` → 12 boxes (~11 sticks each).
- **Fewer, bigger:** set `COLS = 3` → 6 boxes.
- **Taller/shorter boxes:** `BOX_H`.
- **Deeper/shallower scoop:** `SCOOP_DIP` (and `SCOOP_R` for its width).
- **Different drawer or packet:** `DRAWER_L/W/D`, `STICK_LEN/TALL/THICK`.

The box footprint is derived so `COLS × ROWS` boxes always tile the drawer.
