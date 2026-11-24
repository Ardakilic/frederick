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

### Single-dose hopper insert: `stl/frederick-hopper-insert-<variant>.stl`

Drops into the throat in place of the stock hopper. Shaped after [Papel Espresso's Fred single-dose hopper](https://www.papelespresso.com/product/lelit-fred-single-dose-hopper/): open spout, collar, a convex bulb that turns vertical at the top, and the bellows flush on top. Overall size: Ø70 × 70.

| | |
|---|---|
| Spout | OD 33.6 (`THROAT_ID` − 0.2), ID 30.4, 20 long |
| Seating shoulder | 45°, out to the `SHOULDER_OD` 40 collar (1.4 tall before the bulb rises out of it); sits on the ring face around the bore |
| Bulb | starts 2 above the spout top (the bore runs on, so the corner keeps the full wall); circular arc (R 58.5) from the spout ID to Ø62, 40 tall, 2 wall; 43.1° from vertical at the bottom (45° max: prints spout-down, beans still slide), vertical at the top |
| Socket for the bellows | Ø66 × 8, wall 2 |

| Variant | What's different | Volume |
|---|---|---|
| `friction` | held by the spout fit only | 23.5 cm³ |
| `screw` | adds a Ø10 × 6 hub on 3 spokes, Ø4.4 hole for the stock central screw | 24.4 cm³ |

### Bellows: `stl/frederick-hopper-bellows.stl`

TPU cap that plugs into the insert socket; press it to blow out retained grounds. Ø70 × 56.1, 26.2 cm³.

| | |
|---|---|
| Folds | 4, 11 pitch, 5.5 deep (45° flanks), 1.2 wall; narrowest bore Ø56.6 |
| Ring | OD 65.7 (0.3 clearance in the socket) × 8 tall, 2 wall |
| Cap | 2 thick |
| Capacity | about 250 ml with the insert (bulb 89 + bellows 160); `DOSE_VOLUME_ML` = 60 is the minimum the tests enforce |

### Two-piece hopper: `stl/frederick-hopper-2p-body.stl` + `stl/frederick-hopper-2p-cap.stl`

The alternative to insert + bellows, shaped after the commercial 2-part Fred single-dose hopper: one TPU body (spout, straight conical funnel, bellows, open top) and a rigid cap that plugs onto it. Lift the cap off to load beans; press it to blow out retained grounds.

| | |
|---|---|
| Body | Ø70 × 111.3, 35.8 cm³, TPU 95A |
| Spout | OD 33.6, ID 29.6 (2 wall), 20 long; the insert's 45° shoulder out to the `SHOULDER_OD` 40 collar |
| Cone | straight, from the spout ID to Ø62 over 35, 2 wall, 24.8° from vertical; starts 2 above the spout top (the bore runs on, so the corner keeps the full wall) |
| Folds | 4, the bellows' 11 pitch × 5.5 deep (45° flanks), 1.2 wall, peaks Ø70 |
| Top collar | Ø70 outside, bore Ø66 × 6 straight (2 wall) |
| Cap | Ø73 × 3 disc (1.5 lip) with a plug ring OD 65.9 (0.1 clearance in the collar) × 5 tall, 2 wall; 73 × 73 × 8, 14.6 cm³ |
| Capacity | about 226 ml (cone 61 + bellows and collar 165) |

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

| Part | Material | Settings |
|---|---|---|
| Base | PLA or PETG | deck up, no supports, 4 walls, 20–30 % infill |
| Insert | PLA or PETG | spout down, no supports |
| Bellows | TPU 95A | cap on the bed, no supports; 3+ walls or 100 % infill |
| Two-piece body | TPU 95A | spout down, no supports |
| Two-piece cap | PLA or PETG | top face down, no supports |

## Preview site (GitHub Pages)

Live at <https://ardakilic.github.io/frederick/>. `make site` builds the same page locally into `_site/`.

The page is fully static and self-contained. Every STL is embedded in `_site/index.html` (gzip + base64 of the exact file bytes, about 1.7 MB in total), and the browser decodes it itself. That means you can **double-click `_site/index.html`** and it works from disk, with no server. `make serve` is still there if you prefer `http://localhost`. Only three.js comes from the network (pinned jsDelivr import map); offline, the page says so, and the downloads still work. The download links are plain `stl/<file>.stl` files next to the page.

**Show on grinder.** The toggle under the part buttons (off by default) puts the selected part in context: a base with the grinder standing in its pockets, or a hopper part seated in the throat with its kit partner (insert + bellows, body + cap) shown faintly. The grinder is a translucent, boxy ghost built from the `GHOST_*` estimates in `config.py` (scaled from product renders, not measured). It's approximate, for context only, and not a download.

`.github/workflows/pages.yml` runs `make image`, then `make generate test site`, on every push to `main`, and deploys `_site/` to GitHub Pages as static files. If a test fails, nothing is deployed. **One-time setup:** *Settings > Pages > Build and deployment > Source: GitHub Actions*.

The generated STLs in `stl/` are committed. The toolchain is pinned (`Dockerfile`, `requirements*.txt`), so rebuilding the image does not re-triangulate them. Bump a pin only together with regenerated STLs.

## Credits

The 10° angle and the foot spacing were cross-checked against [Printables model 1818194](https://www.printables.com/model/1818194) (CC BY-NC-SA). Only measurements were taken from it; no geometry was reused.

## License

GPL-3.0, see [LICENSE](LICENSE).
