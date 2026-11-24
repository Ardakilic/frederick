"""Every frederick parameter, in one place.

Edit the values here, or override any of them for one build without touching
this file:

    make generate GEN_ARGS="--angle 12"                    # shortcut for BASE_ANGLE
    make generate GEN_ARGS="--set FOOT_D=22.0 --set THROAT_ID=34.2"

`--set NAME=VALUE` takes any UPPER_CASE name below; VALUE is a Python literal
(numbers, True/False, dicts), anything else is kept as a string. The values
are checked by geometry.common.validate() before anything is built.

Units: millimetres and degrees. Grinder figures are estimates from photos,
renders and third-party models: measure your own grinder and fix them here.
"""

# --- Grinder (measure yours!) -------------------------------------------------
GRINDER_PLATE_W = 93.0     # mm, grinder base plate width L-R; estimated 92-95 from Lelit renders
GRINDER_PLATE_D = 180.0    # mm, base plate depth front-back; Lelit spec depth 180
FOOT_D = 22.4              # mm, rubber foot diameter; Lelit spare MC428 = 3M Bumpon SJ5009, Ø22.3-22.4
FOOT_H = 10.1              # mm, rubber foot height; 3M Bumpon SJ5009
FOOT_SPACING_X = 66.0      # mm, foot centre-to-centre L-R; measured from Printables model 1818194
FOOT_SPACING_Y = 156.8     # mm, foot centre-to-centre front-back along the plate; same source, medium confidence

# --- Angled base ------------------------------------------------------------
BASE_ANGLE = 10.0          # deg, deck tilt, front low; both commercial stands use 10
BASE_FRONT_H = 6.0         # mm, deck height at the front edge
BASE_EDGE_MARGIN = 6.0     # mm, deck extends this far beyond the plate on every side; frame wall 5 mm at the deck, ~3 mm at the front rim top (10 deg)
BASE_CORNER_R = 4.0        # mm, outer vertical corner radius
FOOT_CLEARANCE = 0.8       # mm, foot pocket Ø = FOOT_D + this
POCKET_DEPTH = 3.0         # mm, foot pocket depth, perpendicular to the deck
POCKET_CHAMFER = 0.8       # mm, lead-in chamfer at the pocket mouth
FRAME_GAP = 1.0            # mm per side, plate <-> frame inner wall; frame wall = BASE_EDGE_MARGIN - FRAME_GAP
FRAME_OVERLAP = 4.0        # mm, rim rises this far above the plate underside; rim above deck = FOOT_H - POCKET_DEPTH + this
WINDOW_SIDE_RAIL = 14.0    # mm, width of the side rails beside the through-window
WINDOW_END_RAIL = 4.0      # mm, material between a window end and the foot pocket edge
WINDOW_CORNER_R = 5.0      # mm, through-window corner radius
PAD_D = 13.0               # mm, bottom recess Ø for anti-slip bumpers (fits Ø12.7)
PAD_DEPTH = 1.0            # mm, bottom recess depth; 0 disables the recesses
PAD_INSET = 14.0           # mm, pad centre from the outer footprint edges
# The power cord gland (Lelit CD361) sits low on the back panel, just above the plate.
CABLE_NOTCH_W = 30.0       # mm, frame variants: back rim cut down to the deck over this width; 0 disables
CABLE_NOTCH_X = 0.0        # mm, notch centre offset, + = right when facing the grinder's front; unverified - measure
BASE_MIN_WALL = 2.0        # mm, thinnest pocket floor (and floor-to-pad material) the base accepts
BASE_VARIANTS = {          # one STL per entry: stl/frederick-base-<name>.stl
    "solid": {"frame": False, "window": False},
    "window": {"frame": False, "window": True},
    "frame-solid": {"frame": True, "window": False},
    "frame-window": {"frame": True, "window": True},
}

# --- Hopper interface (measure yours!) -----------------------------------------
THROAT_ID = 33.8           # mm, bore the stock hopper spout drops into; Etsy seller figure, stock spout OD 34 - measure
THROAT_DEPTH = 20.0        # mm, spout length into the bore; estimated from the parts diagram
SPOUT_CLEARANCE = 0.2      # mm, diametral; spout OD = THROAT_ID - this

# --- Single-dose insert (PLA/PETG) ----------------------------------------------
# Shape reference: Papel Espresso's Fred single-dose hopper,
# https://www.papelespresso.com/product/lelit-fred-single-dose-hopper/ - friction fit,
# open spout, ~60 g, PLA-CF body, silicone bellows. Bottom up: spout, collar, a convex
# bulb (circular arc, vertical at the top), bellows flush on top.
SPOUT_WALL = 1.6           # mm, spout wall thickness
SHOULDER_OD = 40.0         # mm, collar Ø (~1.2x spout OD, as on the reference) the 45° seating step runs out to; rests on the ring face around the bore; the bulb rises out of it - measure that face
INSERT_WALL = 2.0          # mm, bulb wall thickness
FUNNEL_TOP_ID = 62.0       # mm, bulb inner diameter at the top, where it turns vertical
FUNNEL_H = 40.0            # mm, height of the bulb, which starts INSERT_WALL above THROAT_DEPTH; its bottom tangent 2*atan((FUNNEL_TOP_ID - spout ID) / 2 / FUNNEL_H) must be <= 45° from vertical (43.1)
SOCKET_ID = 66.0           # mm, socket the bellows ring plugs into
SOCKET_DEPTH = 8.0         # mm, socket depth
SOCKET_WALL = 2.0          # mm, socket wall thickness
# screw hub: the stock hopper is held by one central screw (Lelit CD553INOX, size unverified)
HUB_OD = 10.0              # mm, hub outer diameter
HUB_H = 6.0                # mm, hub height
SCREW_HOLE_D = 4.4         # mm, screw clearance hole; M4 clearance, unverified
SPOKES = 3                 # count, spokes holding the hub
SPOKE_W = 3.0              # mm, spoke width
INSERT_VARIANTS = {        # one STL per entry: stl/frederick-hopper-insert-<name>.stl
    "friction": {"screw_hub": False},
    "screw": {"screw_hub": True},
}

# --- Bellows (TPU 95A): capped (cap on the bed) or open (ring on the bed) -----------
BELLOWS_WALL = 1.2         # mm, wall thickness
BELLOWS_OD = 70.0          # mm, outer diameter at the fold peaks
BELLOWS_FOLD_DEPTH = 5.5   # mm, radial fold depth; 5.5 keeps the bean path >= FUNNEL_TOP_ID - 6 (Ø56.6)
BELLOWS_FOLD_PITCH = 11.0  # mm, fold pitch; >= 2 x depth -> flanks <= 45 deg, support-free
BELLOWS_FOLDS = 4          # count, number of folds
BELLOWS_RING_H = 8.0       # mm, plug-in ring height; <= SOCKET_DEPTH
BELLOWS_RING_WALL = 2.0    # mm, plug-in ring wall thickness; ring ID = ring OD - 2 x this
BELLOWS_FIT_CLEARANCE = 0.3  # mm, diametral; ring OD = SOCKET_ID - this
BELLOWS_CAP_T = 2.0        # mm, capped bellows: cap thickness
DOSE_VOLUME_ML = 60.0      # ml, minimum bean capacity of every hopper kit (~20 g beans)

# --- Two-piece hopper body (TPU 95A) ----------------------------------------------
# Shape reference: the commercial 2-part Fred single-dose hopper - one rubber bellows body
# (spout, straight conical funnel, ~4 folds, open top) plus a rigid cap that plugs onto the
# top of the bellows. The body reuses the spout fit, SHOULDER_OD collar, FUNNEL_TOP_ID and
# the BELLOWS_* folds above; its top collar is the shared one below.
TWO_PIECE_WALL = 2.0       # mm, spout and cone wall; a TPU spout needs more wall than SPOUT_WALL
TWO_PIECE_FUNNEL_H = 35.0  # mm, straight cone height, spout ID -> FUNNEL_TOP_ID, starting TWO_PIECE_WALL above THROAT_DEPTH; half-angle atan((FUNNEL_TOP_ID - spout ID) / 2 / this) must be <= 45° (24.8)

# --- Cap (shared by the two-piece and 3-part kits; PLA/PETG) -----------------------
# One rigid cap fits both TPU parts that end in the top collar: the two-piece body and the
# open bellows. The collar is BELLOWS_OD outside, BELLOWS_RING_WALL thick, reached by a 45°
# chamfer in from the last fold peak.
CAP_COLLAR_H = 6.0         # mm, straight bore height of the top collar the cap plugs into
CAP_T = 3.0                # mm, cap disc thickness
CAP_LIP = 1.5              # mm, cap disc overhang per side; cap OD = BELLOWS_OD + 2 x this
CAP_PLUG_H = 5.0           # mm, plug ring height; <= CAP_COLLAR_H
CAP_PLUG_WALL = 2.0        # mm, plug ring wall thickness
CAP_FIT_CLEARANCE = 0.1    # mm, diametral; plug OD = collar ID - this

# --- Hopper kits ------------------------------------------------------------------
# Each kit is the parts printed separately and put together, bottom up: the first goes in
# the throat, each other part sits on the one below it. Names are STL stems after
# "frederick-hopper-"; "insert" is a slot for any INSERT_VARIANTS entry.
HOPPER_KITS = {
    "3-part": ["insert", "bellows-open", "cap"],        # insert PLA + open bellows TPU + cap PLA
    "capped-bellows": ["insert", "bellows-capped"],     # insert PLA + bellows with its own TPU cap
    "two-piece": ["2p-body", "cap"],                    # TPU body (spout, cone, folds) + cap PLA
}

# --- Grinder ghost (preview only, approximate) ----------------------------------
# A boxy stand-in for the grinder, drawn translucent by the preview's "Show on grinder"
# toggle; context only, never exported to stl/ or offered as a download. Not measured:
# estimated from a Cremashop side render and the Lelit front render, scaled against the
# 180 mm plate and the Ø120 stock hopper. Grinder frame: origin at the centre of the plate
# underside, z up from it, Y front -> back, + X = right (as CABLE_NOTCH_X).
GHOST_PLATE_T = 2.0          # mm, plate thickness; render estimate, medium
GHOST_SHELL_W = 90.0         # mm, stainless shell width L-R; render estimate, medium
GHOST_SHELL_D = 123.0        # mm, shell depth, flush with the plate's rear edge (plate ~55 proud in front); render estimate, medium
GHOST_SHELL_TOP = 146.0      # mm, shell top above the plate underside; render estimate, medium
GHOST_CHUTE_W = 37.0         # mm, chute tower width L-R; render estimate, medium-low
GHOST_CHUTE_PROUD = 32.0     # mm, chute tower depth in front of the shell; render estimate, medium-low
GHOST_CHUTE_BOTTOM = 117.0   # mm, chute tower underside; it runs up to the shell top; render estimate, medium-low
GHOST_HOUSING_D = 64.0       # mm, black burr housing Ø, from the shell top up to the ring; render estimate, medium
GHOST_RING_D = 70.0          # mm, ring Ø the hopper collar sits on (throat bore THROAT_ID x THROAT_DEPTH); render, high
GHOST_RING_H = 9.0           # mm, ring height; render estimate, low-medium
GHOST_RING_TOP = 200.0       # mm, ring top face above the plate underside; render estimate, low-medium
GHOST_RING_FROM_BACK = 74.0  # mm, ring (and throat) centre in front of the plate's rear edge, centred L-R; render estimate, medium
GHOST_FORK_Z = 68.0          # mm, portafilter fork tine height (centre); render estimate, low
GHOST_FORK_REACH = 42.0      # mm, fork reach in front of the shell; render estimate, low
GHOST_FORK_GAP = 60.0        # mm, fork tine centre-to-centre L-R; guess, low
GHOST_FORK_T = 4.0           # mm, square fork tine section; guess, low
GHOST_KNOB_D = 25.0          # mm, side knob Ø, axis along X at ring-top height; render estimate, low
GHOST_KNOB_L = 15.0          # mm, knob length, from the centre plane out to the right (so it joins the ring); low
GHOST_KNOB_BEHIND = 40.0     # mm, knob axis behind the ring centre; render estimate, low

# --- Mesh ---------------------------------------------------------------------
SEGMENTS = 128             # count, circle resolution
