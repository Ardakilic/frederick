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

# --- Bellows (TPU 95A) ----------------------------------------------------------
BELLOWS_WALL = 1.2         # mm, wall thickness
BELLOWS_OD = 70.0          # mm, outer diameter at the fold peaks
BELLOWS_FOLD_DEPTH = 5.5   # mm, radial fold depth; 5.5 keeps the bean path >= FUNNEL_TOP_ID - 6 (Ø56.6)
BELLOWS_FOLD_PITCH = 11.0  # mm, fold pitch; >= 2 x depth -> flanks <= 45 deg, support-free
BELLOWS_FOLDS = 4          # count, number of folds
BELLOWS_RING_H = 8.0       # mm, plug-in ring height; <= SOCKET_DEPTH
BELLOWS_RING_WALL = 2.0    # mm, plug-in ring wall thickness; ring ID = ring OD - 2 x this
BELLOWS_FIT_CLEARANCE = 0.3  # mm, diametral; ring OD = SOCKET_ID - this
BELLOWS_CAP_T = 2.0        # mm, cap thickness
DOSE_VOLUME_ML = 60.0      # ml, minimum bean capacity of insert + bellows (~20 g beans)

# --- Mesh ---------------------------------------------------------------------
SEGMENTS = 128             # count, circle resolution
