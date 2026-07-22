# Drink-packet drawer organizer (flat-stack bins)

Open-top bins for a **20 × 14.5 × ~2.4 in** drawer. Drink-mix packets
(ICEE, Holloway, Laura Beverlin, etc.) **lie flat and stack up** inside — one
flavor per bin. A curved **scoop** in the front lets you reach in and slide the
top packet out.

No baseplate, no Gridfinity — **just bins**.

![box](../../renders/drink_stick_box.png)
![layout](../../renders/drawer_layout.png)

## Layout

**4 bins across the front** of the drawer, each reaching ~6 in back. The rest of
the drawer stays free for your other stuff. Each bin holds **~36 packets laid
flat** (they stack ~9 high in the 2 in depth) → **~144 total**.

## What to print

| File | What | Print how many |
|------|------|----------------|
| `drink_stick_box.stl` | One bin (125 × 148 × 50 mm), scooped front | **4×** (all identical) |
| `drawer_layout_preview.stl` | The 4 bins placed in the drawer | **don't print** — just to eyeball it |

## Print settings (Bambu H2D, one color)

| Setting | Value |
|---|---|
| Material | PLA (or PETG) |
| Layer height | 0.2–0.28 mm |
| Walls | 3 |
| Infill | 10–15% |
| Supports | **None** (the scoop is a gentle arc) |
| Orientation | As-is, open side up |
| Per plate | ~2 bins per H2D plate → 2 plates for all 4 |

## Want it different? It's parametric

Edit the CONFIG block in `src/generate_drawer_organizer.py` and re-run
`python3 src/generate_drawer_organizer.py`:

- **Fill the whole drawer** (front *and* back): set `ROWS = 2` → 8 bins.
- **More / fewer bins across:** `COLS`.
- **Deeper or shallower reach:** `BOX_DEPTH`.
- **Taller / shorter bins:** `BOX_H`.
- **Different packet or drawer:** `PKT_*`, `DRAWER_*`.
