# Drawer boxes — 5 × 7 × 2 in

Plain open boxes for a **20 × 14.5 in** drawer. Each box is **5 × 7 × 2 inches**.
They sit **2 across the 14.5 in width** (5 in each = 10 in), **7 in front-to-back**.
A second row makes **4 boxes**, leaving the back of the drawer for other stuff.

![box](../../renders/drink_box.png)
![layout](../../renders/drawer_layout.png)

## What to print

| File | What | How many |
|------|------|----------|
| `drink_box.stl` | One box, 5 × 7 × 2 in | up to 4 |
| `drawer_layout_preview.stl` | boxes in the drawer | don't print — just to look |

## Print settings (Bambu H2D)

- PLA, 0.2–0.28 mm layers, 3 walls, 10–15% infill
- No supports, open-side-up, one box per plate

## Change it

Edit the inch values at the top of `src/generate_drawer_organizer.py`
(`BOX_ACROSS_IN`, `BOX_DEEP_IN`, `BOX_H_IN`, `N_ACROSS`, `N_DEEP`) and re-run it.
