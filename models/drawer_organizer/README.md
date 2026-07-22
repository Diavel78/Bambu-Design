# Drawer boxes — 5 × 7 × 2 in

Plain open boxes for a **20 × 14.5 in** drawer. Each box is **5 × 7 × 2 inches**.
**4 boxes** line up along the 20 in length (4 × 5 in = 20 in), each reaching
7 in front-to-back.

![box](../../renders/drink_box.png)
![layout](../../renders/drawer_layout.png)

## What to print

| File | What | Print how many |
|------|------|----------------|
| `drink_box.stl` | One box, 5 × 7 × 2 in | **4×** |
| `drawer_layout_preview.stl` | 4 boxes in the drawer | don't print — just to look at |

## Print settings (Bambu H2D)

- PLA, 0.2–0.28 mm layers, 3 walls, 10–15% infill
- **No supports**, print open-side-up
- One box per plate (it's 7 in across)

## Change the size

Edit the top of `src/generate_drawer_organizer.py` (`BOX_L_IN`, `BOX_W_IN`,
`BOX_H_IN`, `N_BOXES`) and re-run `python3 src/generate_drawer_organizer.py`.
All values are in inches.
