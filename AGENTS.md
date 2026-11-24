# AGENTS.md: frederick

Parametric, 3D-printable accessories for the **Lelit Fred (PL043MMI)** coffee
grinder: an angled base (4 variants), a single-dose hopper insert (2 variants)
and a TPU bellows, or a two-piece hopper (TPU body + rigid cap). Python builds
the STLs; a three.js page previews them.

Remote: `github.com/Ardakilic/frederick`. Site: <https://ardakilic.github.io/frederick/>
(GitHub Pages, deployed by `.github/workflows/pages.yml` on every push to `main`).
License: GPL-3.0.

**Golden rule: everything is generated from Python.** Never hand-edit an STL,
`build/` or `_site/`. Change `config.py` or `geometry/`, then regenerate
(`make`). Commit the regenerated `stl/` in the same commit as the code or pin
change that caused it.

## Repo layout

```
config.py                  every design parameter, one commented UPPER_CASE constant each
generate.py                builds every part -> stl/*.stl + build/manifest.json; CLI overrides
geometry/common.py         config load/validate/--set, shapely -> manifold3d -> trimesh helpers
geometry/base.py           angled base: deck frame, pockets, frame/rim, window, pads, cable notch
geometry/hopper.py         single-dose insert (+ screw hub), TPU bellows, two-piece body + cap, assembly poses; revolved profiles
geometry/grinder.py        grinder ghost (preview only, approximate) + poses: throat, on the base, upright
tools/build_site.py        _site/: template + manifest + embedded gzip/base64 STLs and ghost, copies stl/
preview/template.html      the preview page: CSS, import map, three.js viewer module
tests/test_base.py         base geometry, measured with vertical rays
tests/test_hopper.py       insert (both variants), bellows, two-piece body + cap, assembly poses
tests/test_grinder.py      ghost body, ghost fit on every base and of the hopper in the throat, placements
tests/test_common.py       mesh helpers
tests/test_config.py       config loading, validation, --set
tests/test_generate.py     manifest logic (no geometry needed)
tests/test_site.py         site build: embedded meshes round-trip, links, placeholders
stl/                       generated STLs, COMMITTED deliverables (print orientation)
build/, _site/             generated, gitignored (manifest + grinder ghost STL; the Pages site)
Dockerfile                 python:3.14-slim + the pinned wheels; HOME=/tmp
Makefile                   every command, run in Docker as the host uid:gid
requirements*.txt          == pins (mesh stack; pytest and its deps)
pytest.ini                 pythonpath = ., testpaths = tests
.github/workflows/pages.yml  make image; make generate test site; deploy _site/
examples/                  third-party reference (Printables 1818194, CC BY-NC-SA) + photos; read-only
README.md                  user docs: parts tables, measure-before-printing list, build, preview
```

## Commands

Everything runs in Docker through the Makefile. You need only Docker and make.

```bash
make                       # = make generate test site
make generate              # stl/*.stl + build/manifest.json (prints size, volume, triangles)
make generate GEN_ARGS="--angle 12 --set NAME=VALUE"   # one-off overrides, repeat --set
make test                  # pytest -q
make site                  # _site/index.html + _site/stl/ (open the HTML by double-click)
make serve PORT=9000       # optional: serve _site at http://localhost:9000
make shell                 # bash in the build image
make image                 # (re)build the frederick-build image (cached; byte-neutral)
make clean                 # delete build/, _site/, caches
```

`--set` takes any UPPER_CASE name from `config.py`, VALUE as a Python literal.
Unknown names are rejected with close-match suggestions; values are validated
(`geometry.common.validate()` plus each builder's own checks) before any mesh
is built. `--angle` is a shortcut for `BASE_ANGLE`.

## Working rules (the user's)

- **Docker only.** Never `pip install` on the host, never create a venv. One-off
  tools go in a throwaway container (e.g. `docker run --rm -v "$PWD":/w -w /w
  node:22-slim node --check file.mjs`).
- **Every design parameter lives in `config.py`** as a commented UPPER_CASE
  constant (unit, meaning, source). No magic numbers in `geometry/`; module
  constants there are only non-design limits (`EPS`, `MAX_OVERHANG`).
- **Every new or changed function gets a Google-style docstring** (Args /
  Returns / Raises) **and pytest coverage.** `make test` must stay green.
- **Use the Context7 MCP** for library docs (three.js, trimesh, manifold3d,
  shapely, browser APIs) instead of memory.
- **Delegate** research and separable jobs to subagents.
- Don't commit or push unless asked; show the result first.

## Technology decisions (and why)

- **shapely + manifold3d + trimesh.** Outlines and (r, z) profiles are shapely
  polygons (buffers give round corners for free); `geometry/common.py` turns
  them into manifold3d solids (`prism`, `revolve`, even-odd fill so ring
  orientation doesn't matter), booleans run in manifold3d (always manifold),
  and `to_trimesh` hands the result to trimesh for export and the tests.
  `generate.py` refuses a mesh that isn't watertight or doesn't sit on z=0.
- **Pinned `python:3.14-slim` and `==` pins.** The mesh stack decides
  triangulation and last-bit floats, so a floating toolchain rewrites every
  committed STL. With the pins, rebuilding the image is byte-neutral. To bump:
  change the pin, `make image all`, compare the printed sizes/volumes, commit
  the regenerated STLs with the pin change.
- **three.js on a pinned CDN import map, meshes embedded.** `tools/build_site.py`
  embeds every STL as gzip + base64 of its exact bytes, one
  `<script type="application/octet-stream" id="mesh-<file stem>">` each. The
  page decodes with `DecompressionStream("gzip")` and `STLLoader.parse()`. No
  `fetch()`, so `_site/index.html` works from `file://` (about 1.7 MB). three.js
  loads by dynamic `import()` from jsDelivr (sends CORS headers), so an offline
  load is caught and explained. Download links stay plain `stl/<file>.stl`.
- **CI regenerates, tests, then deploys.** The workflow runs `make image`, then
  `make generate test site`, and uploads `_site/` as a static Pages artifact. A
  failing test fails make, the job stops, nothing deploys (the last good site
  stays up).

## Design map

Read the code for exact formulas; this is the map.

### Angled base (`geometry/base.py`, `build_base(cfg, frame=, window=)`)

- **World:** X left-right centred on 0, Y front -> back with the footprint's
  front edge at Y=0, Z up, bed at z=0. The deck rises toward +Y at `BASE_ANGLE`
  (front low), `BASE_FRONT_H` at the front edge.
- **Deck frame:** origin (0, 0, `BASE_FRONT_H`), x = world X, u = (0, cos a,
  sin a) up the slope, w = (0, -sin a, cos a) the deck normal. `_to_world()`
  maps deck coordinates to world. Pockets and the frame recess are built in
  the deck frame (walls square to the deck); the outer walls, window and pad
  recesses are world-vertical.
- **Deck:** plate (`GRINDER_PLATE_W` x `GRINDER_PLATE_D`) plus
  `BASE_EDGE_MARGIN` on every side; the body is the rounded footprint prism
  cut by the tilted deck plane.
- **Variants** (`BASE_VARIANTS`): `solid`, `window`, `frame-solid`, `frame-window`.
- **Pockets:** four blind, revolved, Ø`FOOT_D + FOOT_CLEARANCE` x
  `POCKET_DEPTH`, with a `POCKET_CHAMFER` lead-in; centres
  `FOOT_SPACING_X` x `FOOT_SPACING_Y`, centred on the deck.
- **Frame/rim:** a recess for the plate (`FRAME_GAP` per side), cut
  `FOOT_H - POCKET_DEPTH + FRAME_OVERLAP` above the deck, so the rim rises
  `FRAME_OVERLAP` above the plate's underside. Wall = `BASE_EDGE_MARGIN - FRAME_GAP`.
- **Cable notch** (frame only): the back rim is cut to the deck over
  `CABLE_NOTCH_W`, centred at `CABLE_NOTCH_X`, for the cord gland.
- **Window:** a vertical through-hole between the pocket rows, leaving
  `WINDOW_SIDE_RAIL` at the sides and `WINDOW_END_RAIL` to the pockets
  (checked at both the pocket mouth and its floor, since one is tilted).
- **Pads:** four Ø`PAD_D` x `PAD_DEPTH` recesses underneath, `PAD_INSET`
  from the footprint edges, for anti-slip bumpers; `PAD_DEPTH = 0` disables.
- **Validations** (one `ValueError` listing all): chamfer < depth; pocket
  mouths inside the deck (inside the frame wall on frame variants); front
  pocket floor (pad counted) >= `BASE_MIN_WALL`; thinnest frame wall >=
  `BASE_MIN_WALL`; window bigger than its corner radius; pads clear of the window.

### Hopper (`geometry/hopper.py`)

Every part is a solid of revolution: an (r, z) envelope minus a void, revolved
with `SEGMENTS`. **Print orientation:** insert and two-piece body spout down,
bellows cap down, two-piece cap top face down, z=0 on the bed. **No-overhang
rule:** every downward-facing surface is at most `MAX_OVERHANG` = 45° from
vertical, so no part needs supports; the profiles are built from 45° (or
steeper) lines and the builders reject parameters that would break that.

- **Insert** (`build_insert(cfg, screw_hub=)`), bottom up: the spout (OD
  `THROAT_ID - SPOUT_CLEARANCE`, `THROAT_DEPTH` long) into the throat; a 45°
  collar out to the seat on the ring face around the bore; the circular-arc
  bulb (starts `INSERT_WALL` above the spout top so the corner keeps a full
  wall, vertical at the top, bottom tangent <= `MAX_OVERHANG` from vertical); the
  socket for the bellows ring, whose floor ledge (funnel top ID < socket ID)
  stops the bellows. Variants (`INSERT_VARIANTS`): `friction` (spout fit only)
  and `screw` (adds a hub on spokes inside the spout, with a hole for the
  stock central screw).
- **Bellows** (`build_bellows`): cap down, then zig-zag folds with 45° flanks
  (`BELLOWS_FOLD_PITCH` >= 2 x `BELLOWS_FOLD_DEPTH`), then the plug-in ring
  (OD `SOCKET_ID - BELLOWS_FIT_CLEARANCE`) that pushes into the insert socket.
  The tests enforce the combined capacity >= `DOSE_VOLUME_ML`. `_folds()`
  builds the zig-zag (and checks the flanks) for both the bellows and the body.
- **Two-piece body** (`build_two_piece_body`, TPU 95A; reference: the commercial
  2-part Fred hopper), bottom up: the insert's spout and 45° collar, walls
  `TWO_PIECE_WALL`; the bore runs a wall past the spout top, then a straight
  cone to `FUNNEL_TOP_ID` over `TWO_PIECE_FUNNEL_H` (half-angle <= 45°); the
  bellows folds, placed so the first flank's inner face starts at the cone top;
  a 45° chamfer in to the top collar (OD `BELLOWS_OD`, wall `BELLOWS_RING_WALL`,
  straight bore `TWO_PIECE_COLLAR_H`). Open on top.
- **Two-piece cap** (`build_two_piece_cap`, PLA/PETG): a `CAP_T` disc, OD
  `BELLOWS_OD + 2 * CAP_LIP`, with a plug ring (`CAP_PLUG_H` <=
  `TWO_PIECE_COLLAR_H`, wall `CAP_PLUG_WALL`, OD collar ID - `CAP_FIT_CLEARANCE`).
  Nothing else: a recessed face would bridge on the bed side.
- **Assembly** (`assembly_poses(cfg)`): STL stem -> 4x4 pose from print
  orientation into the hopper frame (spout bottom at the origin, z up). Inserts
  and body: identity; bellows flipped onto the socket ledge; cap flipped, disc
  on the collar top. The tests check each pair touches without overlapping.

### Grinder ghost (`geometry/grinder.py`, preview only)

No usable model of the Fred exists, so `build_grinder_ghost(cfg)` makes a boxy
stand-in from the `GHOST_*` constants: plate, four feet, stainless shell
(flush with the plate's rear edge), chute tower, black housing cylinder, ring
with the `THROAT_ID` x `THROAT_DEPTH` bore, two fork tines and a side knob.
**Every `GHOST_*` value is an estimate** from a Cremashop side render and the
Lelit front render, scaled against the 180 mm plate and the Ø120 hopper (see
the confidence in each config comment); the ghost is context, not a fit
reference. Pieces run into their neighbours so the union is one body.
**Grinder frame:** origin at the centre of the plate underside, z up, Y front
-> back, +X right (as `CABLE_NOTCH_X`). Poses (4x4): `throat_pose` hopper
frame -> grinder frame (spout bottom on the bore floor, collar on the ring
top); `grinder_on_base_pose` grinder frame -> base world, reusing
`base.deck_to_world` (plate centre over the deck centre, plate underside at
w = `FOOT_H - POCKET_DEPTH`); `grinder_upright_pose` feet on z = 0.
`generate.py` writes the ghost to `build/frederick-grinder-ghost.stl` (never
`stl/`) and gives each manifest entry `placement` and `ghost_placement`
(row-major 16 floats: the page uses `Matrix4.set(...m)`; `fromArray` would
transpose) plus `partners` (insert <-> bellows, body <-> cap). The page's
"Show on grinder" toggle (off by default) draws the ghost translucent
(opacity 0.25, no depth writes), the part in assembly position and its
partners faint, and refits the camera. The ghost is embedded, never linked.

## Research and sources

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Grinder size | 125 x 180 x 310 mm, 38 mm conical burrs | Lelit spec | high |
| Base plate width | 93 (92–95) | Lelit renders | low |
| Feet | Ø22.4 x 10.1, 3M Bumpon SJ5009 = Lelit spare MC428 | part spec (config.py) | high |
| Foot spacing | 66 x 156.8 | measured from Printables 1818194 (CC BY-NC-SA; measurements only, no geometry reused) | medium (Y explicitly flagged) |
| Throat bore | Ø33.8 | Etsy seller's figure | medium |
| Throat depth | 20 | parts-diagram estimate | low |
| Stock hopper | MC342-250, Ø34 spout, held by central screw CD553INOX (size unverified, M4 guessed) | Lelit parts diagram | high (parts), low (screw size) |
| Cord gland | CD361, low on the back panel just above the plate | Lelit parts diagram | medium (position unverified) |
| Seat ring face | `SHOULDER_OD` 40 | Papel collar, about 1.2 x the spout OD | low |
| Grinder ghost (shell 90 x 123 x 146, ring Ø70 top at 200, 74 from the back, fork, knob) | `GHOST_*` | Cremashop side render + Lelit front render, scaled to the 180 plate and Ø120 hopper | low to medium (ring Ø high); preview only |

- Lelit parts diagram:
  <https://www.espresso.co.nz/content/Spare_Part_Diagrams/LELIT/LELIT_PL043MMI-Spare_Parts.pdf>
- Insert shape reference (Papel Espresso):
  <https://www.papelespresso.com/product/lelit-fred-single-dose-hopper/>,
  an open friction-fit spout, bulb body, about 60 g capacity, silicone
  bellows, aluminium lid.
- The 10° angle matches both commercial stands and Printables 1818194.

## Open measurement requests

Nothing here has been measured on the user's grinder yet. Ask for these
before treating the fits as final (README "Measure your grinder before
printing" has the user-facing version):

- `GRINDER_PLATE_W`, `GRINDER_PLATE_D`: plate size; sets the deck and the frame recess.
- `FOOT_D`, `FOOT_H`: foot size; pocket Ø and how high the plate rides.
- `FOOT_SPACING_X`, `FOOT_SPACING_Y`: pocket centres. The defaults put the feet
  0.4 mm from the plate's front/back edges, so one estimate is probably off.
- `CABLE_NOTCH_X`, `CABLE_NOTCH_W`: cord gland position and width.
- `THROAT_ID`, `THROAT_DEPTH`: spout fit and length.
- `SHOULDER_OD`: outer Ø of the flat ring face the collar seats on.
- `SCREW_HOLE_D`, `HUB_OD`, `HUB_H`: the stock central screw (diameter, length).

## Gotchas

- **Pocket mouth vs frame recess: 0.2 mm** at the front and back by default
  (mouth Ø24.8 at u = 17.6, wall 5). A larger `FOOT_SPACING_Y` (over 157.2)
  raises "foot pockets reach into the frame wall" on the frame variants.
- **The frame's front wall thins with the angle:** the recess wall is square
  to the deck, so it leans forward; at the rim top it is
  `wall - rise * tan(angle)` (about 3.0 at 10°). Steeper angles or a taller
  `FRAME_OVERLAP` trip the `BASE_MIN_WALL` check.
- **three.js r167+ is split** into `three.module.js` + `three.core.js`. The
  import map maps only `three` and `three/addons/`; `three.module.js` pulls
  `three.core.js` by a relative URL from the same CDN folder. Keep both entries
  on the same pinned version.
- **Pages must be enabled once:** Settings > Pages > Build and deployment >
  Source: **GitHub Actions**. The workflow token can deploy but not create the site.
- **Containers run as the host uid:gid** (so repo files stay yours). That uid
  has no passwd entry or home, hence `HOME=/tmp` in the Dockerfile; keep it
  for any new `docker run`.
- `_site/` is rebuilt from scratch by `make site`; anything put there by hand is lost.
- `make site` only reads `build/manifest.json` and `stl/`: run `make generate`
  first (it fails without a manifest, and shows stale parts with an old one).
  The site tests use fixtures, not the real `stl/`.
