# AGENTS.md: frederick

Parametric, 3D-printable accessories for the **Lelit Fred (PL043MMI)** coffee
grinder: an angled base (4 variants) and a single-dose hopper in three kits
(`3-part`: insert + open TPU bellows + rigid cap; `capped-bellows`: insert +
capped TPU bellows; `two-piece`: TPU body + the same cap). Python builds the
STLs; a three.js page previews them, with a "final form" view of base,
grinder and hopper together.

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
geometry/hopper.py         insert (+ plain or reinforced screw hub), capped + open TPU bellows, two-piece body, shared cap, kit poses; revolved profiles
geometry/grinder.py        grinder ghost (preview only, approximate) + poses: throat, on the base
tools/build_site.py        _site/: template + manifest + embedded gzip/base64 STLs and ghost, copies stl/, zip bundles; REPO_URL
preview/template.html      the preview page: CSS, import map, three.js viewer module
tests/test_base.py         base geometry, measured with vertical rays
tests/test_hopper.py       every hopper part, kit poses, fit + capacity of every kit, the cap on both collars
tests/test_grinder.py      ghost body, ghost on every base, kits clear of the ghost in the final form, rename check
tests/test_common.py       mesh helpers
tests/test_config.py       config loading, validation, --set
tests/test_generate.py     manifest logic: entries, kits, final-form placements (no meshes built)
tests/test_site.py         site build: embedded meshes round-trip, links, bundles (members, determinism), print panel, GitHub links, placeholders
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
make site                  # _site/index.html + _site/stl/ + _site/bundles/*.zip (open the HTML by double-click)
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
  `fetch()`, so `_site/index.html` works from `file://` (about 2 MB). three.js
  loads by dynamic `import()` from jsDelivr (sends CORS headers), so an offline
  load is caught and explained. Download links stay plain relative `stl/<file>.stl`
  and `bundles/<name>.zip` hrefs with `download` (they work from `file://` too).
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
capped bellows cap down, open bellows ring down, cap top face down, z=0 on the
bed. **No-overhang rule:** every downward-facing surface is at most
`MAX_OVERHANG` = 45° from vertical, so no part needs supports; the profiles are
built from 45° (or steeper) lines and the builders reject parameters that
would break that. Shared pieces have one helper each: `_folds()` (the zig-zag,
flank check), `_ring()` (plug-in ring radii, socket checks), `_top_collar()`
(the collar the cap plugs into).

- **Insert** (`build_insert(cfg, screw_hub=, reinforced=False)`), bottom up: the spout (OD
  `THROAT_ID - SPOUT_CLEARANCE`, `THROAT_DEPTH` long) into the throat; a 45°
  collar out to the seat on the ring face around the bore; the circular-arc
  bulb (starts `INSERT_WALL` above the spout top so the corner keeps a full
  wall, vertical at the top, bottom tangent <= `MAX_OVERHANG` from vertical); the
  socket for the bellows ring, whose floor ledge (funnel top ID < socket ID)
  stops the bellows. Variants (`INSERT_VARIANTS`, each entry's flags are
  `build_insert()` keywords): `friction` (spout fit only), `screw` (adds a
  `HUB_*` hub on `SPOKE_W` spokes inside the spout, with a hole for the stock
  central screw; keep its STL byte-identical, `test_screw_unchanged` pins it)
  and `screw-reinforced` (`_strong_hub()`: `STRONG_HUB_OD` x `STRONG_HUB_H`
  hub, a flat `WASHER_D + WASHER_CLEARANCE` washer seat at `STRONG_HUB_H` and a
  45° cone from it down to the hub OD; `STRONG_SPOKE_W` spokes with full
  `STRONG_HUB_H` sides and a 45° peaked roof on top (ridge `STRONG_SPOKE_W / 2`
  higher, about 5.4x the plain spoke's second moment), starting just outside the
  seat with their corners inside the hub; it rejects spokes wider than half the
  bore circumference in total or that miss the hub outside the seat, a hub over
  spout ID - 4, a seat that misses the hole or the hub, a hub lower than its
  cone or a ridge above `THROAT_DEPTH`).
  Both hubs sit below `THROAT_DEPTH`, so they never cut kit capacity.
- **Print info** (`generate.PRINT_INFO`, not config: they are not parameters):
  kind -> material, print hint and `material_note` (1–3 sentences) for every
  manifest item; inserts map to a kind by their flags (`generate.insert_kind`).
- **Capped bellows** (`build_bellows`, `frederick-hopper-bellows-capped`): cap
  down, then zig-zag folds with 45° flanks (`BELLOWS_FOLD_PITCH` >= 2 x
  `BELLOWS_FOLD_DEPTH`), then the plug-in ring (OD `SOCKET_ID -
  BELLOWS_FIT_CLEARANCE`, `BELLOWS_RING_H`) that pushes into the insert socket.
- **Open bellows** (`build_bellows_open`, `frederick-hopper-bellows-open`), ring
  down: the same ring on the bed, a flank out to the first peak, the same
  folds, then the top collar. Open at both ends; the inside flares out of the
  ring bore along the first flank.
- **Two-piece body** (`build_two_piece_body`, TPU 95A; reference: the commercial
  2-part Fred hopper), bottom up: the insert's spout and 45° collar, walls
  `TWO_PIECE_WALL`; the bore runs a wall past the spout top, then a straight
  cone to `FUNNEL_TOP_ID` over `TWO_PIECE_FUNNEL_H` (half-angle <= 45°); the
  bellows folds, placed so the first flank's inner face starts at the cone top;
  then the top collar. Open on top.
- **Top collar** (`_top_collar`, shared by the body and the open bellows): OD
  `BELLOWS_OD`, a 45° chamfer in to wall `BELLOWS_RING_WALL`, straight bore
  `CAP_COLLAR_H`. One collar, so one cap fits both.
- **Cap** (`build_cap`, `frederick-hopper-cap`, PLA/PETG): a `CAP_T` disc, OD
  `BELLOWS_OD + 2 * CAP_LIP`, with a plug ring (`CAP_PLUG_H` <= `CAP_COLLAR_H`,
  wall `CAP_PLUG_WALL`, OD collar ID - `CAP_FIT_CLEARANCE`). Nothing else: a
  recessed face would bridge on the bed side.
- **Kits** (`HOPPER_KITS` in `config.py`, the one place they are defined): kit
  key -> part names bottom up, as STL stems after `frederick-hopper-`;
  `insert` is a slot for any `INSERT_VARIANTS` entry. Defaults: `3-part`
  (insert, bellows-open, cap), `capped-bellows` (insert, bellows-capped),
  `two-piece` (2p-body, cap).
- **Kit poses** (`kit_poses(cfg)` -> `{kit: {part: 4x4}}`): print orientation ->
  hopper frame (spout bottom at the origin, z up). Each kit is a stack: the
  first part (insert or 2p-body) keeps identity; each other part sits on the
  seat of the one below (insert: the socket ledge; body and open bellows:
  the collar top) by its mount (open bellows as printed, capped bellows and
  cap flipped). A kit that starts elsewhere or stacks a part on one without a
  seat raises `ValueError`. The tests check, for every kit and insert variant,
  that no two parts overlap and each touches the one below (0.5 mm lower, they
  overlap), and that every kit holds >= `DOSE_VOLUME_ML`.

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
w = `FOOT_H - POCKET_DEPTH`). `generate.py` writes the ghost to
`build/frederick-grinder-ghost.stl` (never `stl/`).

### Final-form view (`generate.final_form`, `preview/template.html`)

The manifest carries `ghost` (`file`, `placement` = `grinder_on_base_pose`),
`bases` (variant -> file), `kits` (per `HOPPER_KITS` entry: `key`, `inserts`
variant -> file or `{}`, `files` the other parts bottom up, `placements` file
-> `grinder_on_base_pose @ throat_pose @ kit pose`, every insert variant
included) and `default` (`frame-solid` if it exists, the first kit, the first
insert). Matrices are row-major 16 floats rounded to 6 decimals: the page uses
`Matrix4.set(...m)`; `fromArray` would transpose. No placement depends on the
base variant. `groups` (the downloads) lists each STL once.

The page picker has the base variants, then one row per kit (a shared STL
gets a button in every kit using it). It keeps three slots: base, kit (with
its insert variant) and the part last clicked; a click fills its slot. With
"Show on grinder" off it shows the clicked part as printed; on, the final
form: the base (identity), every part of the kit at its placement, the ghost
translucent (opacity 0.25, no depth writes), a caption ("Final form:
frame-solid base · 3-part hopper (friction insert)"), the clicked part lit
slightly (emissive), the camera refitted. Printed parts are opaque, rigid tan
and TPU slate. The ghost is embedded, never linked. On load the default base
button is pressed, so the slots and the pressed button agree.

The page design follows the sibling projects (ithalat's drafting bench, filtarr's
"Print these" panel): masthead with the GitHub link, stage (z-up camera, OrbitControls,
RoomEnvironment + hemisphere/key/fill on the physical scale, shadow catcher + 10 mm grid,
view presets, auto-rotate, title block, axis triad) and a side panel (picker, "Print
these", all downloads, parameters with the `config.py` link). Colours are CSS tokens
(`--scene-*` feed the scene) with light and dark sets. The picker and the print panel
run before three.js loads, so they work offline or without WebGL.

**Bundles** (`build_site.bundles`): one zip per base variant, per kit x insert
(`frederick-hopper-<kit>[-<insert>].zip`) and `frederick-all.zip`, each with a
`README.txt` (parts, material, optional `material_note`, print hint, links). Entries are
sorted, stamped `ZIP_DATE`, mode 0644, deflate 9: rebuilds are byte-identical. The
"Print these" sets are rendered server-side (one per bundle but "all", `data-base` or
`data-kit` + `data-insert`); the script shows the one of the slot last clicked and copies
its zip href into the phone's sticky bar.

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
  `screw-reinforced` adds `STRONG_HUB_H` 8 plus a `WASHER_D` washer under the
  head, so the screw's length and thread need checking too.

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
