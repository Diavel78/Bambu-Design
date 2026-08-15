# Drawer bins — print list

Drawer: **20.0" x 16.4" x 2.0" deep** (508 x 417 x 51 mm).
Bin height **48.0 mm**, walls 2.0 mm, floor 1.6 mm, 0.8 mm gap between bins.

## Compartments (as drawn)

| Compartment | Size | Printed as |
|---|---|---|
| A1 | 6.0" x 8.2" | 1 bin |
| A2 | 6.0" x 8.2" | 1 bin |
| B1 | 6.0" x 8.2" | 1 bin |
| B2 | 6.0" x 8.2" | 1 bin |
| C1 | 8.0" x 4.1" | 1 bin |
| C2 | 8.0" x 4.1" | 1 bin |
| C3 | 8.0" x 4.1" | 1 bin |
| C4 | 8.0" x 4.1" | 1 bin |

## What to print

Bins of the same size are the same model — print the one STL as many times as the quantity says.

| Print this | Size (in) | Size (mm) | Qty | Fills | Filament |
|---|---|---|---|---|---|
| `bin_A1.stl` | 6.00 x 8.20 | 151.6 x 207.5 | **4x** | A1, A2, B1, B2 | ~573 g |
| `bin_C1.stl` | 8.00 x 4.10 | 202.4 x 103.3 | **4x** | C1, C2, C3, C4 | ~441 g |

**Total: 8 bins from 2 unique models, ~1014 g (~1.0 kg) of filament.**

## Straight into Bambu Studio

`bambu/` holds one **.3mf per build plate**, already arranged for the **H2D** (350 x 320 mm). Open one, pick your filament, slice, print. No arranging needed.

| Plate file | Holds | Fills |
|---|---|---|
| `bambu/plate_1_bin_A1_x2.3mf` | 2 x `bin_A1.stl` | A1, A2 |
| `bambu/plate_2_bin_A1_x2.3mf` | 2 x `bin_A1.stl` | B1, B2 |
| `bambu/plate_3_bin_C1_x2.3mf` | 2 x `bin_C1.stl` (rotated to fit) | C1, C2 |
| `bambu/plate_4_bin_C1_x2.3mf` | 2 x `bin_C1.stl` (rotated to fit) | C3, C4 |

Prefer to arrange yourself? Every bin is also exported as its own `bin_<id>.stl` and `.step`.
