# Drink-packet drawer organizer (flat-stack bins)

Open-top bins for a **20 × 14.5 × ~2.4 in** drawer. Drink-mix packets
(ICEE, Holloway, Laura Beverlin, etc.) **lie flat and stack up** inside — one
flavor per bin. A curved **scoop** in the front lets you reach in and slide the
top packet out.

No baseplate, no Gridfinity — **just bins**.

![box](../../renders/drink_stick_box.png)
![layout](../../renders/drawer_layout.png)

## Layout

**4 rows of 5 in down the 20 in length**, each row spanning the 14.5 in width.
A full-width tray (~14.5 in / 368 mm) is bigger than the H2D bed (~350 mm), so
each row is **2 bins side by side** → a **2 × 4 grid, 8 bins total**, filling the
whole drawer. Each bin holds **~45 packets laid flat** (they stack ~9 high in
the 2 in depth) → plenty of headroom for however many you keep.

Each bin is **4.9 × 7.2 × 2 in** (125 × 182 × 50 mm) — fits the bed easily.

## What to print

| File | What | Print how many |
|------|------|----------------|
| `drink_stick_box.stl` | One bin, scooped front | **8×** (all identical) |
| `drawer_layout_preview.stl` | All 8 placed in the drawer | **don't print** — just to eyeball it |

## Print settings (Bambu H2D, one color)

| Setting | Value |
|---|---|
| Material | PLA (or PETG) |
| Layer height | 0.2–0.28 mm |
| Walls | 3 |
| Infill | 10–15% |
| Supports | **None** (the scoop is a gentle arc) |
| Orientation | As-is, open side up |
| Per plate | ~2 bins per H2D plate → 4 plates for all 8 |

## Want it different? It's parametric

Edit the CONFIG block in `src/generate_drawer_organizer.py` and re-run
`python3 src/generate_drawer_organizer.py`:

- **Only fill the front** (leave the back for other stuff): `ROWS = 1`.
- **More / fewer rows down the length:** `COLS`.
- **Taller / shorter bins:** `BOX_H`.
- **Different packet or drawer:** `PKT_*`, `DRAWER_*`.
