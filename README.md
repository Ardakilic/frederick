# frederick

Parametric, 3D-printable accessories for the **Lelit Fred (PL043MMI)** coffee grinder. Python generates the STLs, and GitHub Pages hosts a 3D preview with download links: <https://ardakilic.github.io/frederick/>.

## Parts

All sizes are in mm at the default `config.py`. STLs are in `stl/` and already in print orientation. `make generate` prints each part's size and volume, and writes them to `build/manifest.json`.

### Angled base: `stl/frederick-base-<variant>.stl`

Tilts the grinder 10° forward (front low). The grinder's four rubber feet sit in blind pockets.

| | |
|---|---|
| Deck | 105 × 192 (plate 93 × 180, plus a 6 mm margin on each side), tilted 10° |
| Footprint | 105 × 189.1 |
| Deck height | 6 at the front, 39.3 at the back |
| Foot pockets | Ø23.2 × 3 deep, square to the deck, 0.8 chamfer (mouth Ø24.8), centres 66 × 156.8 |
| Underside | four Ø13 × 1 recesses for Ø12.7 anti-slip bumpers |
| Frame (rim) | 11.1 above the deck, 4 over the plate's underside; wall 5 at the deck, 3 at the front rim top; 30 wide cable notch in the back rim |
| Window | 77 × 122 through-window between the pocket rows |

| Variant | Frame | Window | Size | Volume |
|---|---|---|---|---|
| `solid` | no | no | 105 × 189.1 × 39.3 | 444 cm³ |
| `window` | no | yes | 105 × 189.1 × 39.3 | 232 cm³ |
| `frame-solid` | yes | no | 105 × 189.1 × 50.6 | 474 cm³ |
| `frame-window` | yes | yes | 105 × 189.1 × 50.6 | 261 cm³ |

### Single-dose hopper kits

The hopper parts print separately and go together in three kits. The insert and the cap are shared, so each is one STL; the insert slot takes any of the three insert variants (friction by default).

| Kit | Parts, bottom up | Materials | Assembled height above the throat floor | Capacity |
|---|---|---|---|---|
| `3-part` | insert + open bellows + cap | PETG + TPU + PETG/PLA | 127.15 | about 277 ml (bulb 89 + bellows 188) |
| `capped-bellows` | insert + capped bellows | PETG + TPU | 118.15 | about 250 ml (bulb 89 + bellows 160) |
| `two-piece` | two-piece body + cap | TPU + PETG/PLA | 114.3 | about 226 ml (cone 61 + bellows and collar 165) |

`DOSE_VOLUME_ML` = 60 is the minimum capacity the tests enforce for every kit, with every insert variant (the screw hubs sit inside the spout, below the counted bean path). The kits are listed in `HOPPER_KITS` in `config.py`.

### Insert: `stl/frederick-hopper-insert-<variant>.stl`

Drops into the throat in place of the stock hopper. Shaped after [Papel Espresso's Fred single-dose hopper](https://www.papelespresso.com/product/lelit-fred-single-dose-hopper/): open spout, collar, a convex bulb that turns vertical at the top, and a bellows flush on top. Overall size: Ø70 × 70. Used by the `3-part` and `capped-bellows` kits.

| | |
|---|---|
| Spout | OD 33.6 (`THROAT_ID` − 0.2), ID 30.4, 20 long |
| Seating shoulder | 45°, out to the `SHOULDER_OD` 40 collar (1.4 tall before the bulb rises out of it); sits on the ring face around the bore |
| Bulb | starts 2 above the spout top (the bore runs on, so the corner keeps the full wall); circular arc (R 58.5) from the spout ID to Ø62, 40 tall, 2 wall; 43.1° from vertical at the bottom (45° max: prints spout-down, beans still slide), vertical at the top |
| Socket for the bellows | Ø66 × 8, wall 2; its floor is the ledge either bellows' ring rests on |

| Variant | What's different | Volume |
|---|---|---|
| `friction` | held by the spout fit only | 23.5 cm³ |
| `screw` | adds a Ø10 × 6 hub on 3 spokes (3 wide, flat tops), Ø4.4 hole for the stock central screw | 24.4 cm³ |
| `screw-reinforced` | the screw clamps the hub while the collar rests on the ring, so the spokes bend: a Ø12 × 8 hub with a flat Ø9.5 seat at 8 for an M4 DIN 125 washer and a 45° cone from the seat down to the hub OD, so beans slide off; 3 spokes 4.5 wide with full 8 tall sides and a 45° peaked roof on top (ridge at 10.25, clear of the seat), about 5.4 × as stiff as the `screw` spokes | 25.4 cm³ |

### Capped bellows: `stl/frederick-hopper-bellows-capped.stl`

TPU bellows with its own cap, for the `capped-bellows` kit. It plugs into the insert socket; press it to blow out retained grounds. Ø70 × 56.1, 26.2 cm³.

| | |
|---|---|
| Folds | 4, 11 pitch, 5.5 deep (45° flanks), 1.2 wall; narrowest bore Ø56.6 |
| Ring | OD 65.7 (0.3 clearance in the socket) × 8 tall, 2 wall |
| Cap | 2 thick |

### Open bellows: `stl/frederick-hopper-bellows-open.stl`

TPU bellows open at both ends, for the `3-part` kit: the capped bellows' ring at the bottom, the same folds, and the two-piece body's top collar, so the one cap fits both. Lift the cap off to load beans; press it to blow out retained grounds. Ø70 × 62.1, 21.6 cm³, prints ring down.

| | |
|---|---|
| Ring | OD 65.7 (0.3 clearance in the socket) × 8 tall, 2 wall; plugs into the insert socket and rests on its ledge |
| Folds | a 45° flank out from the ring top to the first peak (10.2 up), then 4 folds, 11 pitch × 5.5 deep, 1.2 wall, peaks Ø70; narrowest bore Ø56.6 |
| Top collar | Ø70 outside, a 45° chamfer in, then bore Ø66 × 6 straight (2 wall) |

### Two-piece body: `stl/frederick-hopper-2p-body.stl`

The body of the `two-piece` kit, shaped after the commercial 2-part Fred single-dose hopper: one TPU part (spout, straight conical funnel, bellows, open top) that drops straight into the throat. Ø70 × 111.3, 35.8 cm³.

| | |
|---|---|
| Spout | OD 33.6, ID 29.6 (2 wall), 20 long; the insert's 45° shoulder out to the `SHOULDER_OD` 40 collar |
| Cone | straight, from the spout ID to Ø62 over 35, 2 wall, 24.8° from vertical; starts 2 above the spout top (the bore runs on, so the corner keeps the full wall) |
| Folds | 4, the bellows' 11 pitch × 5.5 deep (45° flanks), 1.2 wall, peaks Ø70 |
| Top collar | the open bellows' collar: Ø70 outside, bore Ø66 × 6 straight (2 wall) |

### Cap: `stl/frederick-hopper-cap.stl`

The rigid cap of the `3-part` and `two-piece` kits. It plugs into the top collar, which the open bellows and the two-piece body share. 73 × 73 × 8, 14.6 cm³.

| | |
|---|---|
| Disc | Ø73 × 3 (1.5 lip over the collar) |
| Plug ring | OD 65.9 (0.1 clearance in the collar) × 5 tall, 2 wall |

The variants are listed in `BASE_VARIANTS` and `INSERT_VARIANTS` in `config.py`.

## Measure your grinder before printing

Most grinder figures are **research estimates**, not measurements. Check these on your own grinder and fix them in `config.py` (or pass `--set`):

| Config | Default | Source | Why it matters |
|---|---|---|---|
| `GRINDER_PLATE_W`, `GRINDER_PLATE_D` | 93, 180 | W from renders, D from the Lelit spec | Set the deck size and the frame recess. If they're too small, the plate won't drop into a frame variant. |
| `FOOT_D`, `FOOT_H` | 22.4, 10.1 | 3M Bumpon SJ5009 (= Lelit spare MC428) | Pocket Ø is `FOOT_D` + 0.8. `FOOT_H` sets how high the plate rides, and so the rim height. |
| `FOOT_SPACING_X`, `FOOT_SPACING_Y` | 66, 156.8 | Printables 1818194 (Y: medium confidence) | Pocket centres. At the default margins, frame variants take at most 70.2 × 157.2: Y has only 0.4 mm of headroom. These defaults also put the feet 0.4 mm from the plate's front and back edges, so one of the estimates is probably off. |
| `CABLE_NOTCH_X`, `CABLE_NOTCH_W` | 0, 30 | unverified | Where the back rim is cut down for the power-cord gland (frame variants only). |
| `THROAT_ID`, `THROAT_DEPTH` | 33.8, 20 | seller's figure, parts-diagram estimate | Spout OD and length. If it's too tight, the insert won't seat; too loose, and it wobbles. |
| `SHOULDER_OD` | 40 | reference collar, about 1.2 × the spout OD | The 45° shoulder rests on the flat ring face around the bore. Measure that face's outer Ø. |
| `SCREW_HOLE_D`, `HUB_OD`, `HUB_H` | 4.4, 10, 6 | M4 guess (screw CD553INOX, size unverified) | `screw` insert only: hole and hub for the stock central hopper screw. Measure the screw's diameter and length. |
| `STRONG_HUB_H`, `WASHER_D` | 8, 9 | M4 DIN 125 washer | `screw-reinforced` only: the screw must reach through an 8 tall hub plus the washer. Check its length and thread first. |

## Build (Docker only)

You need Docker and make. Nothing is installed on the host.

| Command | What it does |
|---|---|
| `make` | `generate`, `test`, `site` |
| `make generate` | writes `stl/*.stl` and `build/manifest.json` |
| `make generate GEN_ARGS="--angle 12 --set FOOT_D=20.0"` | the same, with one-off overrides (`--angle` is a shortcut for `BASE_ANGLE`) |
| `make test` | runs pytest |
| `make site` | builds `_site/` (`index.html` + the STLs) |
| `make serve` | serves `_site/` at <http://localhost:8000>; change the port with `make serve PORT=9000` |
| `make image`, `make shell`, `make clean` | rebuild the `frederick-build` image, open a shell in it, delete `build/`, `_site/` and caches |

`--set NAME=VALUE` takes any `UPPER_CASE` name in `config.py`, with VALUE as a Python literal; repeat it to set more. A misspelled name is rejected, and the error suggests the closest names. Values are validated before anything is built.

## Print settings

For anything that touches beans, use filament certified food-safe and a stainless or hardened nozzle (brass nozzles can contain lead). Wash the parts by hand and keep them out of the dishwasher. The preview page shows the same material note with each part.

| Part | Material | Settings |
|---|---|---|
| Base | PLA or PETG; PETG or ASA near a hot espresso machine | deck up, no supports, 4 walls, 20–30 % gyroid infill; Ø12.7 silicone bumpers in the pad recesses |
| Insert `friction` | PETG (food-safe is best), or PLA+; PLA-CF needs a hardened nozzle | spout down, no supports |
| Insert `screw` | PETG or ASA (PLA creeps under the screw clamp, and the screw works loose) | spout down, no supports; 5+ walls or 100 % infill around the hub; use a washer, tighten only until snug |
| Insert `screw-reinforced` | as `screw`; the stronger choice if you clamp with the stock screw | as `screw`; check the screw's length and thread first |
| Capped bellows | TPU 95A (85A pumps more easily, prints harder) | cap on the bed, no supports; 20–30 mm/s, 2–3 walls, minimal retraction |
| Open bellows | TPU 95A (85A pumps more easily, prints harder) | ring on the bed, no supports; 20–30 mm/s, 2–3 walls, minimal retraction |
| Two-piece body | TPU 95A; 98A for a stiffer spout if the fit feels loose | spout down, no supports; the bellows' slow settings |
| Cap | PETG or PLA | top face down, no supports, 100 % infill (it's thin) |

## Preview site (GitHub Pages)

Live at <https://ardakilic.github.io/frederick/>. `make site` builds the same page locally into `_site/`.

The page is fully static and self-contained. Every STL is embedded in `_site/index.html` (gzip + base64 of the exact file bytes, about 2 MB in total), and the browser decodes it itself. That means you can **double-click `_site/index.html`** and it works from disk, with no server. `make serve` is still there if you prefer `http://localhost`. Only three.js comes from the network (pinned jsDelivr import map); offline, the page says so, and the downloads still work. The download links are plain relative `stl/<file>.stl` and `bundles/<name>.zip` files next to the page.

**Downloads.** The "Print these" panel follows your last click: the base variant, or the hopper kit with its insert. It lists each file with its material and print hint, a direct STL link and a "view on GitHub" link (GitHub renders STLs in 3D), plus a **Download bundle (.zip)** button. On a phone a sticky bar at the bottom keeps that bundle one tap away. `make site` writes one zip per base variant (`frederick-base-<variant>.zip`), one per hopper kit and insert variant (`frederick-hopper-3-part-friction.zip`, ...; `frederick-hopper-two-piece.zip` has no insert) and `frederick-all.zip`; each holds the STLs plus a `README.txt` with every part's material, print orientation and settings. The zips are deterministic (fixed timestamps, sorted entries), so a rebuild gives the same bytes. "All downloads" lists every bundle and each STL once.

The part buttons are grouped as the angled base variants, then one row per hopper kit; the buttons of the current base and kit are outlined, the last one clicked is filled. The camera presets (3/4, front, side, top), auto-rotate, the title block and the axis triad sit on the stage. A shared part (the insert, the cap) has a button in every kit that uses it; the download list still has each file once.

**Show on grinder.** The toggle under the part buttons (off by default) shows the final form: the last base variant you clicked (`frame-solid` at first), the grinder standing in its pockets, and every part of the last hopper kit you clicked seated in the throat (`3-part` with the friction insert at first). Clicking any base or hopper part swaps that slot, so you can flip through combinations; a caption names the current one (for example "Final form: frame-solid base · 3-part hopper (friction insert)"). Printed parts are opaque in their material colour (rigid tan, TPU slate), the part you clicked last is lit slightly, and the camera refits. The grinder is a translucent, boxy ghost built from the `GHOST_*` estimates in `config.py` (scaled from product renders, not measured). It's approximate, for context only, and not a download.

`.github/workflows/pages.yml` runs `make image`, then `make generate test site`, on every push to `main`, and deploys `_site/` to GitHub Pages as static files. If a test fails, nothing is deployed. **One-time setup:** *Settings > Pages > Build and deployment > Source: GitHub Actions*.

The generated STLs in `stl/` are committed. The toolchain is pinned (`Dockerfile`, `requirements*.txt`), so rebuilding the image does not re-triangulate them. Bump a pin only together with regenerated STLs.

## Credits

The 10° angle and the foot spacing were cross-checked against [Printables model 1818194](https://www.printables.com/model/1818194) (CC BY-NC-SA). Only measurements were taken from it; no geometry was reused.

## License

GPL-3.0, see [LICENSE](LICENSE).
