#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["cadquery", "shapely"]
# ///
"""A thigh holster for the Temper, with a swappable pocket clip.

The keyboard's own printed case stays as it is. Its USB end hooks under lips at the bottom of the
holster, it rocks in over a peg that fits the case's slot, and a latch clicks over the thumb
edge. A J-shaped clip bolts on behind, goes over the pocket edge and points straight down the leg.

Modelled as the right half, flat on a desk: X to the right, Y up the desk, Z towards the keycaps.
Worn, the whole thing turns 180 degrees, so the thumbs point up and USB points at the knee.

    uv run case/holster.py        # writes STEP, STL and 3MF to case/out, and prints the checks
"""
import json
import math
from pathlib import Path

import cadquery as cq
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = Path(__file__).parent
OUT = HERE / "out"
TRACE = json.loads((HERE / "case-outline.json").read_text())  # traced from photos of the real case: see the README

# Measured
KEYTOP_H = 17.0  # desk to the top of the keycaps
CASE_H = 8.0  # desk to the top edge of the printed case
BOARD_X, BOARD_Y = TRACE["board_corner"]  # where the board's lower left corner sits in the case
BOARD_H = 89.98  # the board's height, to turn its Y-down positions into this model's
# The hole through the case on the right half, measured from the board's corner: its corners and their radius
SLOT = [(90.87, 21.67), (90.87, 30.57), (76.82, 30.57), (73.57, 24.71), (73.57, 21.67)]
SLOT_R = 2.5
# Guessed
THIGH_R = 130.0  # flatter than a real thigh, as the leg gives a little
TILT = 20.0  # degrees the fingers point away from straight down, from the worn photo
YAW = 6.0  # degrees the keys turn towards the palm: the front edge stands further off the leg
PITCH = 0.0  # degrees the thumb end stands further off the leg than the USB end
POCKET_ANGLE = 35.0  # degrees the pocket edge drops towards the back of the leg, where the clip sits
# Fit
CLEARANCE = 0.5  # gap around the case
CORNER_RELIEF = 2.0  # rounds the pocket's inward corners, as the case's own look filleted
PEG_GAP = 1.8  # around the peg, so the slot clears it as the keyboard rocks in
WALL = 2.4
BACK_MIN = 7.5  # thinnest the holster gets behind the keyboard, where the clip sits
BACK_MAX = 22.0  # deepest it gets: a real thigh falls away from the corners sooner than this curve
LIP = 2.1  # how far the lips reach in from the pocket wall
CATCH = 1.6  # how far the latch's catch does, which sets how far its arm has to flex
LIP_T = 1.6
LIP_GAP = 0.4  # above the case, under the lips and the catch. Two layers, with room for some droop
# Openings, from the inner edge of the case
USB_X, USB_W = 10.16 + BOARD_X, 16.0
SWITCH_Y, SWITCH_LEN = 34.87 + BOARD_Y, 16.0
# Latch on the thumb edge: a stretch of wall, fixed at one end and free at the other
LATCH_X = (32.0, 60.0)
LATCH_SLIT = 1.2
# The latch's release: a paddle on its free end. Push its face along the edge, towards the latch's fixed
# end: it stands out from the wall, so the push levers the latch outward. The thumb comes in along the
# wall past the slit, and the paddle has no undercut for fabric to catch on
PADDLE_OUT = 8.0  # how far it stands out from the wall: further is an easier push, and more to knock
PADDLE_TOP = 5.0  # its flat top, along the edge, before it ramps back into the wall
PADDLE_FROM = 0.8  # where its underside starts, at the wall. It leans out from there at 45 degrees
PADDLE_ROUND = 1.5  # radius of its upright edges
GRIP = (2.0, 4.0, 6.0)  # grooves up its face, this far out from the wall, across the way the thumb pulls
GRIP_W, GRIP_DEPTH = 1.0, 0.8
# Clip: a J that goes over the pocket edge and runs straight down the leg, inside the pocket
CLIP_W = 28.0
TONGUE_DEPTH = 80.0  # how far the tip reaches below the pocket edge
CLIP_ABOVE = 2.0  # how far the pocket edge sits above the top of the holster
CLIP_MOUTH = 2.4  # gap at the top of the J, for thick seams
TONGUE_T = (3.4, 5.2)  # thickness at the tip and at the top, so the stress is spread along it
CLIP_PRELOAD = 3.0  # mm the tip is bent into the holster when printed
BRIDGE_T = 4.5  # thickness over the top of the J
PLATE_T = 5.0  # the plate sits flush in a recess, whose walls take sideways bumps
PLATE_TOP = -3.0  # the plate's top is flat at this height, so it bears straight on the floor under the keyboard
RIB_OFFSET, RIB_H, RIB_W = 8.0, 0.9, 2.2  # ribs along the tongue resist sideways slip, not insertion
BARB_FROM_TIP = 14.0  # one rib across the tongue resists being pulled out
BOLT_BELOW_TOP, BOLT_SPREAD = 27.0, 9.5  # from the top of the holster
BOLT_D, CSK_D, CSK_H = 3.4, 6.4, 1.8  # M3 countersunk
SCREW_LEN = 6.0  # a countersunk screw is measured with its head included
INSERT_D, INSERT_LEN, INSERT_DEPTH = 4.0, 4.0, 4.4  # M3 x 4 heat-set insert in the clip, with room for melted plastic
# Bumpers on both sides, standing just above the keycaps
RAIL_ABOVE_KEYS = 0.5
# The right bumper starts where that side goes straight, clear of the thumb-end corner, and ramps up
# at 45 degrees. A full-height corner there made the keyboard go in level rather than at an angle
RIGHT_RAIL_FROM = 25.0
# A strip of spring steel sealed inside the tongue, in the clip-steel version
SPINE_W, SPINE_T = 13.4, 0.9
SPINE_FROM_TOP, SPINE_FROM_TIP = 24.0, 16.0
# The flat frame that checks the outline
SHEET_T = 1.0
SHEET_RIM = 4.0  # width of the rim and the struts
SHEET_STRUTS = [((-1, 55), (117, 55)), ((84, 30), (84, 96)), ((30, 4), (30, 55))]  # these keep it from twisting
NOTCH = 1.2
# Lug for a tether to a belt loop
LUG = (97.0, 12.0)
LUG_HOLE = 5.0
# The faceted version: under the keyboard's tray every face leans in at 45 degrees, the steepest the
# printer manages without supports, with two windows beside the clip and the name on the front face
FACET_TRAY = -PLATE_TOP  # the floor under the keyboard: the faces start below it, and the holster splits there
FACET_SIMPLIFY = 3.0  # how loosely the faces follow the outline: larger means fewer, bigger faces
KEEL_HALF = CLIP_W / 2 + 0.3 + 4.0  # the clip's recess and a wall each side, which the windows stay clear of
# Each window: from and to, down the leg; how far out from the keel, minus for the front; and its width
WINDOWS = ((-38.0, 16.0, -8.0, 15.0), (4.0, 30.0, 10.0, 20.0))
WINDOW_WALL = 2.4  # thinnest the plastic gets between a window and a face
NAME, NAME_SIZE, NAME_DEPTH = "SHORT TEMPER", 9.0, 0.6
# The faceted version's tether: a tunnel through the thumb end's pinky-side corner, in one face and out the
# other, for 4 mm paracord. A teardrop pointing at the leg, so it prints without support with the back upside down
TETHER_HOLE = 4.8
TETHER_ROOF = 1.0  # plastic between the tunnel and the split, under the floor
TETHER_BAR = 4.0  # thinnest plastic between the tunnel and the corner, which the cord pulls on
FONT = HERE.parent / "art/fonts/Jersey10-Regular.ttf"
# The faceted holster prints as two parts, split along the underside of the floor: the top, which holds the
# keyboard and takes the clip's screws, and the back, which sits on the leg. Two screws from the keyboard side
# hold them together, cutting their own thread in the back, and three short pieces of 1.75 mm filament line them up
JOINS = ((7.0, 71.0), (109.0, 49.0))
JOIN_LEN = 8.0  # M3 countersunk, its head included
JOIN_PILOT = 2.6  # the hole the screw cuts its thread in
PINS = ((64.0, 90.0), (4.0, 24.0), (34.0, 86.0))
PIN_D = 1.9  # for 1.75 mm filament
PIN_TOP, PIN_BACK = 2.2, 4.0  # how deep the pin holes go into each part
# A rough guess at what the slicer prints: about 1.1 mm of walls and skins all over, and 15% infill inside
SKIN, INFILL, PETG = 0.11, 0.15, 1.27


def prism(poly, z0, z1):
    points = list(poly.exterior.coords)[:-1]
    return cq.Workplane("XY").workplane(offset=z0).polyline(points).close().extrude(z1 - z0)


def block(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def load_case():
    """The right half's case, and its height."""
    case = Polygon(TRACE["outline"])
    return case, case.bounds[3]


class Holster:
    def __init__(self):
        self.case, self.height = load_case()
        slot = Polygon(SLOT).buffer(-SLOT_R, quad_segs=6).buffer(SLOT_R, quad_segs=6)
        self.slot = affinity.translate(slot, BOARD_X, BOARD_Y)
        pocket = self.case.buffer(CLEARANCE, join_style=2)
        # Curves in fine steps, so rounded walls print and render as curves rather than flat strips
        self.inner = pocket.buffer(CORNER_RELIEF, quad_segs=12).buffer(-CORNER_RELIEF, quad_segs=12).simplify(0.01)
        self.outer = self.case.buffer(CLEARANCE + WALL, join_style=1, quad_segs=16).simplify(0.01)
        x0, _, x1, _ = self.outer.bounds
        tilt, pitch = math.radians(TILT), math.radians(PITCH)
        self.across = cq.Vector(math.cos(tilt), -math.sin(tilt), 0)  # towards the back of the leg
        self.axis = cq.Vector(math.sin(tilt) * math.cos(pitch), math.cos(tilt) * math.cos(pitch), math.sin(pitch))  # down it
        self.radial = self.across.cross(self.axis)
        # Turning the keys towards the palm is the same as moving the leg's crown towards the back
        shift = THIGH_R * math.sin(math.radians(YAW))
        self.clip_w = -shift
        self.leg_x = (x0 + x1) / 2 + shift * self.across.x
        self.leg_y = self.height / 2 + shift * self.across.y
        self.leg_z = -BACK_MIN - THIGH_R / self.radial.z
        self.origin = cq.Vector(self.leg_x, self.leg_y, self.leg_z)
        points = list(self.outer.exterior.coords)
        self.back = min(-min(self.surface_z(x, y, THIGH_R) for x, y in points) + 2, BACK_MAX)

        # Where the clip's centre line leaves the top of the holster
        start, end = self.at(0, self.clip_w), self.at(-300, self.clip_w)
        reach = LineString([start, end]).intersection(self.outer.exterior)
        edge = min(getattr(reach, "geoms", [reach]), key=lambda p: p.y)
        self.top = -math.hypot(edge.x - start[0], edge.y - start[1])
        self.edge_s = self.top - CLIP_ABOVE  # the pocket edge, at the clip's centre line
        self.slant = math.tan(math.radians(POCKET_ANGLE))
        self.clip_top = self.edge_s - CLIP_W / 2 * self.slant  # the J's highest point, at the front
        self.clip_tip = self.edge_s + TONGUE_DEPTH
        self.length = self.clip_tip - self.clip_top
        self.bolt_s = self.top + BOLT_BELOW_TOP
        self.plate_len = self.bolt_s + 8 - self.clip_top

    def at(self, s, w=0.0):
        """A point on the holster: s down the leg from its middle, and w across it."""
        return (
            self.leg_x + s * self.axis.x + w * self.across.x,
            self.leg_y + s * self.axis.y + w * self.across.y,
        )

    def surface_z(self, x, y, radius):
        """Height of a cylinder around the leg, at x, y."""
        dx, dy = x - self.leg_x, y - self.leg_y
        w = dx * self.across.x + dy * self.across.y
        along = math.sqrt(radius**2 - w**2)
        return self.leg_z + (along - dx * self.radial.x - dy * self.radial.y) / self.radial.z

    def leg(self, radius):
        """A cylinder along the thigh."""
        start = self.origin - self.axis * 300
        return cq.Workplane(obj=cq.Solid.makeCylinder(radius, 600, start, self.axis))

    def edge_y(self, x):
        """The bottom of the pocket at x, for placing the latch."""
        return self.inner.intersection(box(x - 0.1, -50, x + 0.1, 200)).bounds[1]

    def body(self, faceted=False):
        body = prism(self.outer, -self.back, CASE_H - 1)
        if not faceted:  # a lug for the tether, where the faceted version has a tunnel instead
            x, y = LUG
            body = body.union(prism(box(x - 7, y - 5, x + 7, y + 11).buffer(2.5), -self.back, -1.5))
        body = body.cut(prism(self.inner, 0, CASE_H + 5))
        body = body.cut(self.leg(THIGH_R))

        # Soften the edges against the leg, in steps small enough to feel round. The faceted version
        # doesn't need it, as its faces meet the leg at 135 degrees
        for reach in () if faceted else (0.9, 1.8, 2.7):
            inside = self.outer.buffer(-reach)
            inside = max(getattr(inside, "geoms", [inside]), key=lambda g: g.area)
            edge = prism(self.outer, -80, 0).cut(prism(inside, -81, 1))
            body = body.cut(edge.intersect(self.leg(THIGH_R + 3.6 - reach)))
            body = body.cut(edge.intersect(block(-50, 200, -50, 200, -self.back - 1, -self.back + 3.6 - reach)))

        # Lips over the +Y edges, which the USB end hooks under
        zone = box(-20, self.height * 0.6, 200, 200)
        shifted = affinity.translate(self.inner, 0, -LIP)
        wall = self.outer.difference(self.inner).intersection(zone)
        lip = self.outer.difference(shifted).intersection(zone)
        for poly, z0, z1 in ((wall, CASE_H - 1, CASE_H + LIP_GAP), (lip, CASE_H + LIP_GAP, CASE_H + LIP_GAP + LIP_T)):
            for part in getattr(poly, "geoms", [poly]):
                if part.area > 1:
                    body = body.union(prism(part, z0, z1))

        # Peg for the slot, stepped in at the top so the slot finds it
        peg_top = CASE_H * 0.8
        body = body.union(self.peg(-1, peg_top - 1.2))
        for i in range(1, 5):
            body = body.union(self.peg(peg_top - 1.5 + 0.3 * i, peg_top - 1.2 + 0.3 * i, 0.3 * i))

        # Bumpers down both sides, to take a knock before the keycaps do
        ring = self.outer.difference(self.inner)
        x0, _, x1, _ = self.outer.bounds
        # The left one starts above the power switch, leaving the inner thumb key clear for the thumb
        left_from = SWITCH_Y + SWITCH_LEN / 2
        for zone in (box(x0 - 1, left_from, x0 + 4.5, self.height + 5), box(x1 - 4.5, RIGHT_RAIL_FROM, x1 + 1, self.height + 5)):
            rail = ring.intersection(zone)
            for part in getattr(rail, "geoms", [rail]):
                if part.area > 8:
                    body = body.union(prism(part, CASE_H - 1.5, KEYTOP_H + RAIL_ABOVE_KEYS))
        # Both ramp up from the wall's top, rather than ending square
        body = body.cut(self.ramp(x1 - 6, RIGHT_RAIL_FROM, CASE_H - 1, 1))
        body = body.cut(self.ramp(x0 - 2, left_from, CASE_H - 1, 1))

        # Lead-ins, so the keyboard finds its way in by feel
        zone = box(-20, self.height * 0.6, 200, 200)
        for grow, z0, z1 in ((0.5, CASE_H - 2, CASE_H - 1.3), (1.0, CASE_H - 1.3, CASE_H - 1)):
            body = body.cut(prism(self.inner.buffer(grow).difference(zone), z0, z1 + 0.01))
        for grow, z0, z1 in ((0.6, KEYTOP_H - 2.2, KEYTOP_H - 1.1), (1.2, KEYTOP_H - 1.1, KEYTOP_H + 2)):
            body = body.cut(prism(self.inner.buffer(grow), z0, z1))

        # USB and the power switch
        body = body.cut(block(USB_X - USB_W / 2, USB_X + USB_W / 2, self.height - 12, self.height + 10, 0, 40))
        body = body.cut(block(-10, 6, SWITCH_Y - SWITCH_LEN / 2, SWITCH_Y + SWITCH_LEN / 2, 0.5, 40))

        body = self.add_latch(body)
        # Drop any specks the cuts left behind
        body = cq.Workplane(obj=max(solid(body).Solids(), key=lambda s: s.Volume()))

        # A recess for the clip's plate, up to the underside of the floor, which the plate bears on. Its walls
        # take sideways bumps, not the screws
        plate_end = self.clip_top + self.plate_len + 0.3
        body = body.cut(prism(self.plate_strip(self.clip_top - 30, plate_end, CLIP_W + 0.6), -80, PLATE_TOP))

        # Grooves the ribs press the fabric into, so the fabric can't slide sideways
        for w in (-RIB_OFFSET, RIB_OFFSET):
            groove = [(THIGH_R - 2, plate_end - 0.3), (THIGH_R - 2, self.clip_tip), (THIGH_R + 1.5, self.clip_tip), (THIGH_R + 1.5, plate_end - 0.3)]
            body = body.cut(self.band(groove, RIB_W + 1.6, w))
        barb = self.clip_tip - BARB_FROM_TIP
        body = body.cut(self.band([(THIGH_R - 2, barb - 3), (THIGH_R - 2, barb + 3), (THIGH_R + 1.5, barb + 3), (THIGH_R + 1.5, barb - 3)], CLIP_W + 1))

        if not faceted:  # the tether hole
            lx, ly = LUG
            body = body.cut(cq.Workplane("XY").workplane(offset=-40).center(lx, ly).circle(LUG_HOLE / 2).extrude(45))

        # Countersunk bolts for the clip, under the keyboard
        for (x, y), sunk in zip(self.bolts(), self.head_depths()):
            assert self.inner.buffer(-CSK_D / 2).contains(Point(x, y)), f"bolt at {x:.1f}, {y:.1f} is off the floor"
            body = body.cut(cq.Workplane("XY").workplane(offset=-30).center(x, y).circle(BOLT_D / 2).extrude(31))
            cone = cq.Solid.makeCone(BOLT_D / 2, CSK_D / 2, CSK_H, cq.Vector(x, y, -sunk - CSK_H), cq.Vector(0, 0, 1))
            floor = -PLATE_TOP - sunk
            assert floor > CSK_H + 0.4, f"only {floor:.1f} mm of floor over the plate"
            body = body.cut(cq.Workplane(obj=cone))
            if sunk > 0:
                body = body.cut(cq.Workplane("XY").workplane(offset=-sunk).center(x, y).circle(CSK_D / 2).extrude(sunk + 1))
        return self.facet(body) if faceted else body

    def add_latch(self, body):
        """A stretch of wall on the thumb edge, sprung from one end. Hook a nail behind its free end and pull to release."""
        x0, x1 = LATCH_X
        zone = box(x0, -50, x1, self.height * 0.4)
        arm = self.outer.difference(self.inner).intersection(zone)
        arm = max(getattr(arm, "geoms", [arm]), key=lambda g: g.area)
        # Clear the wall, and leave a slit under it and at its free end
        clear = arm.buffer(0.01)
        body = body.cut(prism(clear, 0, 40))
        body = body.cut(block(x0 - LATCH_SLIT, x0, -50, self.height * 0.4, 0, 40).intersect(prism(self.outer, 0, 40)))
        top = CASE_H + 3
        body = body.union(prism(arm, 0.8, top))
        # Join the fixed end back into the wall
        anchor = self.outer.difference(self.inner).intersection(box(x1 - 3, -50, x1 + 3, self.height * 0.4))
        anchor = max(getattr(anchor, "geoms", [anchor]), key=lambda g: g.area)
        body = body.union(prism(anchor, -0.5, CASE_H - 1))
        # The catch, stepped back layer by layer so the case rides over it
        steps = 5
        for i in range(steps):
            reach = CATCH * (1 - i / steps)
            catch = self.outer.difference(affinity.translate(self.inner, 0, reach)).intersection(zone)
            catch = max(getattr(catch, "geoms", [catch]), key=lambda g: g.area)
            body = body.union(prism(catch, CASE_H + LIP_GAP + i * 0.5, CASE_H + LIP_GAP + (i + 1) * 0.5))
        # The release: a paddle on the free end, where the arm moves most
        band = self.outer.buffer(PADDLE_OUT).difference(self.inner.buffer(0.3))
        body = body.union(self.wedge(band.intersection(box(x0, -50, x1, self.height * 0.4)), x0, PADDLE_TOP, 1, top))
        # Grooves up the paddle's face, across the outward pull, for the thumb to grip
        face = self.outer.intersection(box(x0 - 0.05, -50, x0 + 0.05, self.height * 0.4)).bounds[1]
        for out in GRIP:
            y = face - out
            body = body.cut(block(x0 - 0.01, x0 + GRIP_DEPTH, y - GRIP_W / 2, y + GRIP_W / 2, PADDLE_FROM, top + 1))
        return body

    def wedge(self, plan, x, flat, direction, height):
        """A block standing out from the wall, with a square face at x, a flat top running `flat` mm along the
        edge (towards +x for direction 1), then a 45 degree ramp back into the wall. Its underside leans out at 45 degrees."""
        (ax, ay), (bx, by) = [(u, self.outer.intersection(box(u - 0.05, -50, u + 0.05, self.height * 0.4)).bounds[1]) for u in (x, x + direction * 5)]
        length = math.hypot(bx - ax, by - ay)
        tx, ty = (bx - ax) / length, (by - ay) / length  # along the edge, away from the face
        mx, my = ty * direction, -tx * direction  # out of the wall
        far = flat + PADDLE_OUT  # u + v stays under this: the ramp
        corner = lambda u, v: (ax + tx * u + mx * v, ay + ty * u + my * v)
        keep = Polygon([corner(-3, -8), corner(-3, PADDLE_OUT + 3), corner(far - PADDLE_OUT - 3, PADDLE_OUT + 3), corner(far + 8, -8)])
        shape = plan.intersection(keep).buffer(-PADDLE_ROUND, join_style=1).buffer(PADDLE_ROUND, quad_segs=6)
        shape = max(getattr(shape, "geoms", [shape]), key=lambda g: g.area)
        solid_ = prism(shape, PADDLE_FROM, height)
        return solid_.cut(self.under_slope(cq.Vector(ax, ay, 0), cq.Vector(mx, my, 0), PADDLE_FROM))

    def under_slope(self, origin, direction, z):
        """Everything under a plane at height z through origin, rising at 45 degrees in a horizontal direction."""
        plane = cq.Plane(origin=origin.toTuple(), xDir=direction.toTuple(), normal=direction.cross(cq.Vector(0, 0, 1)).toTuple())  # x along it, y up
        return cq.Workplane(plane).polyline([(0, z), (60, z + 60), (60, -60), (-60, -60), (-60, z)]).close().extrude(60, both=True)

    def peg(self, z0, z1, inset=0.0):
        """The slot's own shape, drawn in all the way round."""
        return prism(self.slot.buffer(-PEG_GAP - inset, quad_segs=6), z0, z1)

    def bolts(self):
        return self.at(self.bolt_s, self.clip_w - BOLT_SPREAD), self.at(self.bolt_s, self.clip_w + BOLT_SPREAD)

    def head_depths(self):
        """How far each screw head sits below the floor. The plate is flat on top, so both are flush."""
        return [0.0 for _ in self.bolts()]

    def bolt_check(self):
        """The screw's thread in the insert, and how far it stops short of the end of the hole."""
        floor = -PLATE_TOP
        thread = SCREW_LEN - floor - 0.15
        spare = floor + INSERT_DEPTH - SCREW_LEN
        assert INSERT_LEN < INSERT_DEPTH - 0.15, "the insert is longer than its hole"
        assert thread > 2.5 and spare > 0.3, f"{thread:.1f} mm of thread, {spare:.1f} mm spare"
        return thread, spare

    def plate_strip(self, s0, s1, width):
        """A strip down the leg along the clip's centre line, in plan."""
        w0, w1 = self.clip_w - width / 2, self.clip_w + width / 2
        return Polygon([self.at(s0, w0), self.at(s1, w0), self.at(s1, w1), self.at(s0, w1)])

    def band(self, chain, width, offset=0.0):
        """Sweep a (radius, s) outline around the leg, so it follows the curve across its width."""
        radius = THIGH_R
        angle = width / radius
        start = (self.clip_w + offset) / radius - angle / 2
        x_dir = self.radial * math.cos(start) + self.across * math.sin(start)
        plane = cq.Plane(
            origin=self.origin.toTuple(),
            xDir=x_dir.toTuple(),
            normal=x_dir.cross(self.axis).toTuple(),
        )
        return cq.Workplane(plane).polyline(chain).close().revolve(math.degrees(angle), (0, 0, 0), (0, 1, 0))

    def along(self, s):
        """How far along the tongue s is, from 0 at the top to 1 at the tip."""
        return min(max((s - self.clip_top) / self.length, 0.0), 1.0)

    def thickness(self, s):
        tip, top = TONGUE_T
        q = self.along(s)
        return top + (tip - top) * q + 2.0 * math.exp(-(s - self.clip_top) / 5)  # thicker where it leaves the J

    def centre_line(self, s):
        """The tongue's holster side, without the barb. It leans in, then flares back at the tip."""
        q = self.along(s)
        face = THIGH_R - CLIP_MOUTH + (CLIP_MOUTH + CLIP_PRELOAD) * q**2
        flare_from = self.clip_tip - 12
        if s > flare_from:
            face -= 2.6 * ((s - flare_from) / 12) ** 2
        return face

    def clip(self, steel=False):
        top, tip = self.clip_top, self.clip_tip
        steps = [top + i * (tip - top) / 164 for i in range(165)]
        barb = tip - BARB_FROM_TIP
        rib = lambda s: RIB_H * math.exp(-(((s - barb) / 1.6) ** 2))
        plate_r = THIGH_R + PLATE_T - 0.15
        mouth = CLIP_MOUTH / 2
        chain = [(self.centre_line(s) + rib(s), s) for s in reversed(steps)]
        # Around the inside of the J, where the seam sits
        chain += [(THIGH_R - mouth - mouth * math.cos(a), top - mouth * math.sin(a))
                  for a in (math.pi * i / 12 for i in range(1, 13))]
        # Down the plate and back up its far side
        chain += [(THIGH_R, top + self.plate_len), (plate_r, top + self.plate_len)]
        # Over the top of the J
        back = self.centre_line(top) - self.thickness(top)
        crown = (plate_r - back) / 2
        crown_r, crown_s = (plate_r + back) / 2, top - mouth - BRIDGE_T + crown
        chain += [(crown_r + crown * math.cos(a), crown_s - crown * math.sin(a))
                  for a in (math.pi * i / 16 for i in range(17))]
        # Down the leg side of the tongue
        chain += [(self.centre_line(s) - self.thickness(s), s) for s in steps if s > crown_s + 0.5]
        clip = self.band(chain, CLIP_W)

        # Rounded in plan, as a square corner is where a crack or a snag starts
        corners = box(top - 20, -CLIP_W / 2 + 7, tip - 7, CLIP_W / 2 - 7).buffer(7, quad_segs=10)
        plan = Polygon([self.at(s, w + self.clip_w) for s, w in corners.exterior.coords])
        clip = clip.intersect(prism(plan.buffer(0), -80, 40))

        # Fill the top of the J down to a slant, so it sits along the pocket edge instead of on a corner
        half = CLIP_W / 2
        deep = top + CLIP_W * self.slant
        slant = Polygon([self.at(top - 3, self.clip_w - half), self.at(top - 3, self.clip_w + half), self.at(deep, self.clip_w + half), self.at(top, self.clip_w - half)])
        web = [(THIGH_R + 0.2, top - 3), (THIGH_R + 0.2, deep + 2), (THIGH_R - CLIP_MOUTH - 0.8, deep + 2), (THIGH_R - CLIP_MOUTH - 0.8, top - 3)]
        clip = clip.union(self.band(web, CLIP_W).intersect(prism(slant.buffer(0), -80, 40)))

        # Ribs along the tongue
        first = top + self.plate_len + 2
        ribs = [s for s in steps if first <= s <= barb - 3]
        for w in (-RIB_OFFSET, RIB_OFFSET):
            strip = [(self.centre_line(s) + RIB_H, s) for s in ribs] + [(self.centre_line(s) - 0.8, s) for s in reversed(ribs)]
            clip = clip.union(self.band(strip, RIB_W, w))

        # The plate is flat on top, where it's under the holster, so it bears straight on the floor
        clip = clip.cut(block(-300, 300, -300, 300, PLATE_TOP, 100))
        under = self.plate_strip(self.top - 2, top + self.plate_len, CLIP_W + 2).intersection(plan.buffer(0))
        clip = clip.union(prism(under, -80, PLATE_TOP).cut(self.leg(THIGH_R)))

        if steel:
            clip = clip.cut(self.spine(SPINE_T, SPINE_W))

        for x, y in self.bolts():
            hole = cq.Workplane("XY").workplane(offset=PLATE_TOP - INSERT_DEPTH).center(x, y).circle(INSERT_D / 2).extrude(INSERT_DEPTH + 3)
            clip = clip.cut(hole)
        return clip

    def spine_radius(self, s):
        return self.centre_line(min(s, self.clip_tip - 12)) - self.thickness(s) / 2

    def spine(self, thick=0.65, width=12.7):
        """The steel strip, or the channel for it. It's sealed in, so the print pauses to add it."""
        a, b = self.clip_top + SPINE_FROM_TOP, self.clip_tip - SPINE_FROM_TIP
        steps = [a + i * (b - a) / 80 for i in range(81)]
        return self.band([(self.spine_radius(s) + thick / 2, s) for s in steps]
                         + [(self.spine_radius(s) - thick / 2, s) for s in reversed(steps)], width)

    def spine_walls(self):
        """The thinnest plastic either side of the steel strip."""
        thinnest = 99.0
        for i in range(81):
            s = self.clip_top + SPINE_FROM_TOP + i * (self.length - SPINE_FROM_TOP - SPINE_FROM_TIP) / 80
            face, back = self.centre_line(s), self.centre_line(s) - self.thickness(s)
            r = self.spine_radius(s)
            thinnest = min(thinnest, face - r - SPINE_T / 2, r - SPINE_T / 2 - back)
        return thinnest

    def screws(self):
        out = None
        for (x, y), sunk in zip(self.bolts(), self.head_depths()):
            head = cq.Workplane(obj=cq.Solid.makeCone(1.45, CSK_D / 2 - 0.2, CSK_H, cq.Vector(x, y, -sunk - CSK_H), cq.Vector(0, 0, 1)))
            screw = head.union(cq.Workplane("XY").workplane(offset=-sunk - SCREW_LEN).center(x, y).circle(1.45).extrude(SCREW_LEN - CSK_H + 0.1))
            out = screw if out is None else out.add(screw)
        return out

    def spring_check(self, modulus=2000.0):
        """Treats the tongue as a tapered cantilever, closed over thin fabric. Returns N and strain."""
        deflection = CLIP_PRELOAD + 1.0
        length = self.length
        steps = 400
        flex = 0.0
        for i in range(steps):
            d = (i + 0.5) / steps * length  # distance from the tip
            t = self.thickness(self.clip_tip - d)
            flex += d**2 / (modulus * CLIP_W * t**3 / 12) * (length / steps)
        force = deflection / flex
        strain = 0.0
        for i in range(1, 51):
            d = length * i / 50
            t = self.thickness(self.clip_tip - d)
            strain = max(strain, force * d * (t / 2) / (modulus * CLIP_W * t**3 / 12))
        return force, strain

    def test_fit(self, body):
        """A thin slice with every fit in it: walls, lips, peg and latch. Print this first."""
        keep = prism(self.outer.buffer(PADDLE_OUT + 2), -2.0, 40)  # wide enough for the whole latch paddle
        window = prism(self.inner.buffer(-9), -3, -0.0)
        x0, y0, x1, y1 = self.slot.bounds
        fit = body.intersect(keep).cut(window.cut(block(x0 - 1, x1 + 1, y0 - 1, y1 + 1, -3, 0)))
        return cq.Workplane(obj=max(solid(fit).Solids(), key=lambda s: s.Volume()))

    def outline_sheet(self):
        """The case's exact outline as an open frame, to check against the real keyboard before anything else.

        A ring has the slot's outline outside and the peg's inside, and V notches mark the middle of the
        USB port and the power switch. Flip it over and it's the left half.
        """
        struts = [LineString(strut).buffer(SHEET_RIM / 2, cap_style=2) for strut in SHEET_STRUTS]
        inside = self.case.buffer(-SHEET_RIM).difference(unary_union([*struts, self.slot]))
        sheet = prism(self.case, 0, SHEET_T).cut(self.peg(-1, SHEET_T + 1))
        for part in getattr(inside, "geoms", [inside]):
            opening = part.buffer(-2).buffer(2, quad_segs=4)  # round corners, which lift less as they cool
            for piece in getattr(opening, "geoms", [opening]):
                if piece.area > 20:
                    sheet = sheet.cut(prism(piece.simplify(0.05), -1, SHEET_T + 1))
        top = self.case.intersection(box(USB_X - 0.1, 0, USB_X + 0.1, 200)).bounds[3]
        usb = Polygon([(USB_X - NOTCH, top + 0.1), (USB_X + NOTCH, top + 0.1), (USB_X, top - 1.5 * NOTCH)])
        switch = Polygon([(-0.1, SWITCH_Y - NOTCH), (-0.1, SWITCH_Y + NOTCH), (1.5 * NOTCH, SWITCH_Y)])
        return sheet.cut(prism(usb, -1, SHEET_T + 1)).cut(prism(switch, -1, SHEET_T + 1))

    def keyboard(self):
        """A stand-in for the keyboard, for checking fits."""
        return prism(self.case, 0, CASE_H).cut(prism(self.slot, -1, 40))

    def ramp(self, x, y, z, direction):
        """Cuts a rail's end back at 45 degrees, rising from height z at y, in the direction given along Y."""
        rise = KEYTOP_H + RAIL_ABOVE_KEYS - z + 1
        side = cq.Plane(origin=(x, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))  # sketch in Y and Z
        d = direction
        return cq.Workplane(side).polyline([(y, z), (y + d * rise, z + rise), (y - d, z + rise), (y - d, z)]).close().extrude(8)

    # The faceted version

    def face_lines(self, polygon, outline):
        """Each edge of a polygon as (nx, ny, c), with n pointing out, pushed out until the outline is inside."""
        points = list(orient(polygon, 1.0).exterior.coords)[:-1]
        lines = []
        for (px, py), (qx, qy) in zip(points, points[1:] + points[:1]):
            length = math.hypot(qx - px, qy - py)
            nx, ny = (qy - py) / length, -(qx - px) / length
            c = max(max(nx * x + ny * y for x, y in outline.exterior.coords), nx * px + ny * py)
            lines.append((nx, ny, c))
        return lines

    def faces(self, polygon, outline, z_top, slope=1.0):
        """The solid under z_top whose faces run through the polygon's edges and lean in by slope going down."""
        out = None
        for nx, ny, c in self.face_lines(polygon, outline):
            plane = cq.Plane(origin=(nx * c, ny * c, 0), xDir=(nx, ny, 0), normal=(ny, -nx, 0))  # u out, v up
            half = cq.Workplane(plane).polyline([(-600, -100), ((-100 - z_top) * slope, -100), ((40 - z_top) * slope, 40), (-600, 40)]).close().extrude(600, both=True)
            out = half if out is None else out.intersect(half)
        return out

    def hull_plan(self):
        return orient(self.outer.convex_hull, 1.0).simplify(FACET_SIMPLIFY)

    def tether(self):
        """The tunnel for the tether, across the corner at the thumb end on the pinky side."""
        centre, along, r = self.tether_axis()
        out = cq.Vector(along.y, -along.x, 0)
        # A circle with a 45 degree point towards the leg, which is up when the back prints, drawn across the
        # tunnel and run through the corner
        plane = cq.Plane(origin=centre.toTuple(), xDir=out.toTuple(), normal=(-along).toTuple())  # x out, y up
        hole = cq.Workplane(plane).circle(r).extrude(30, both=True)
        tip = r / math.sqrt(2)
        return hole.union(cq.Workplane(plane).polyline([(-tip, -tip), (0, -r * math.sqrt(2)), (tip, -tip), (0, 0)]).close().extrude(30, both=True))

    def tether_footprint(self):
        """Where the tether tunnel runs, in plan."""
        centre, along, r = self.tether_axis()
        ends = [(centre.x + along.x * d, centre.y + along.y * d) for d in (-30, 30)]
        return LineString(ends).buffer(r * math.sqrt(2)).intersection(self.outer)

    def tether_axis(self):
        """The tether tunnel's middle, its direction, and its radius."""
        plan = self.hull_plan()
        points = list(orient(plan, 1.0).exterior.coords)[:-1]
        lines = self.face_lines(plan, self.outer)
        v = max(range(len(points)), key=lambda i: points[i][0] - points[i][1])
        (n1x, n1y, c1), (n2x, n2y, c2) = lines[v - 1], lines[v]

        def corner(z):
            """Where the two faces meet, at height z."""
            a, b = c1 + z + FACET_TRAY, c2 + z + FACET_TRAY
            det = n1x * n2y - n1y * n2x
            return cq.Vector((a * n2y - b * n1y) / det, (n1x * b - n2x * a) / det, z)

        r = TETHER_HOLE / 2
        z = PLATE_TOP - TETHER_ROOF - r  # its roof under the split
        out = cq.Vector(n1x + n2x, n1y + n2y, 0).normalized()  # straight out of the corner
        along = cq.Vector(-out.y, out.x, 0)  # the tunnel's direction, across the corner
        # The corner leans in going down, so set the tunnel back far enough to keep TETHER_BAR all round
        step = corner(z - 1) - corner(z)
        lean = math.hypot(step.x, step.y)  # sideways, for each mm down
        centre = corner(z) - out * ((TETHER_BAR + r) * math.sqrt(1 + lean**2))
        # Check the plastic between the tunnel and the leg, along the part of it inside the body
        for i in range(-300, 301):
            p = centre + along * (i * 0.1)
            if all(nx * p.x + ny * p.y <= c + z + FACET_TRAY for nx, ny, c in lines) and self.outer.contains(Point(p.x, p.y)):
                floor = z - r * math.sqrt(2) - self.surface_z(p.x, p.y, THIGH_R)
                assert floor > 2.0, f"only {floor:.1f} mm of plastic between the tether tunnel and the leg"
        return centre, along, r

    def windows(self):
        """Long hexagons either side of the clip, clear of everything the keyboard and the clip need."""
        x0, x1 = LATCH_X
        lx, ly = LUG
        keel = Polygon([self.at(-300, self.clip_w - KEEL_HALF), self.at(300, self.clip_w - KEEL_HALF),
                        self.at(300, self.clip_w + KEEL_HALF), self.at(-300, self.clip_w + KEEL_HALF)])
        keep = unary_union([
            keel,
            box(x0 - 6, -50, x1 + 6, self.edge_y(x0 + 8) + 9),  # the latch
            self.inner.difference(self.inner.buffer(-11)).intersection(box(-20, self.height * 0.6 - 4, 200, 200)),  # the lips
            self.slot.buffer(4.5),
            box(lx - 10, ly - 8, lx + 10, ly + 14),
        ])
        allowed = self.inner.buffer(-6.5).difference(keep.buffer(2.5)).buffer(0)
        lines = self.face_lines(self.hull_plan(), self.outer)
        out = []
        for s0, s1, offset, width in WINDOWS:
            w = self.clip_w + math.copysign(KEEL_HALF + 2.5 + abs(offset), offset)
            point = width / 2
            corners = [(s0, w), (s0 + point, w - width / 2), (s1 - point, w - width / 2), (s1, w), (s1 - point, w + width / 2), (s0 + point, w + width / 2)]
            window = Polygon([self.at(s, ww) for s, ww in corners])
            assert window.difference(allowed).area < 0.5, f"window at {s0}..{s1} reaches something the keyboard or clip needs"
            window = window.buffer(-1.5, join_style=2).buffer(1.5, quad_segs=4)
            # Keep plastic between the window and the faces, all the way down to the leg
            for k in range(160):
                x, y = window.exterior.interpolate(k / 160, normalized=True).coords[0]
                z = self.surface_z(x, y, THIGH_R)
                for nx, ny, c in lines:
                    wall = (c + z + FACET_TRAY - (nx * x + ny * y)) / math.sqrt(2)
                    assert wall >= WINDOW_WALL, f"window at {s0}..{s1} is {wall:.1f} mm from a face"
            out.append(window)
        return out

    def facet(self, body):
        """The faceted version's changes, all but the name, which body(faceted=True) makes."""
        hull = self.faces(self.hull_plan(), self.outer, -FACET_TRAY)
        body = body.cut(prism(self.outer.buffer(10), -80, -FACET_TRAY).cut(hull)).cut(self.tether())
        for window in self.windows():
            body = body.cut(prism(window, -80, 0.5))
            for reach in (0.9, 1.8, 2.7):  # rounded against the leg
                ring = window.buffer(reach, join_style=2).difference(window)
                body = body.cut(prism(ring, -80, 0).intersect(self.leg(THIGH_R + 3.6 - reach)))
        # The far ends of the rails ramp down onto the lips at 45 degrees
        ring = self.outer.difference(self.inner)
        x0, _, x1, _ = self.outer.bounds
        lip_top = CASE_H + LIP_GAP + LIP_T
        for zone, x in ((box(x0 - 1, 0, x0 + 4.5, self.height + 5), x0 - 2), (box(x1 - 4.5, 0, x1 + 1, self.height + 5), x1 - 6)):
            end = ring.intersection(zone).bounds[3]
            assert end > self.height * 0.6, "the rail ends outside the lips, so it would ramp from the wrong height"
            body = body.cut(self.ramp(x, end, lip_top, -1))
        return cq.Workplane(obj=max(solid(body).Solids(), key=lambda s: s.Volume()))

    def split(self, body):
        """The faceted holster's two parts, the top and the back, with their screw and pin holes."""
        top = body.intersect(block(-50, 200, -50, 200, PLATE_TOP, 60))
        back = body.intersect(block(-50, 200, -50, 200, -80, PLATE_TOP))
        lines = self.face_lines(self.hull_plan(), self.outer)
        windows = unary_union(self.windows())
        strip = self.plate_strip(self.clip_top - 30, self.clip_top + self.plate_len + 0.3, CLIP_W + 0.6)
        tunnel = self.tether_footprint()

        def solid_under(x, y, depth, margin, what):
            """Check the back is solid for depth mm under the split, with margin mm all round."""
            z = PLATE_TOP - depth
            for dx, dy in ((margin, 0), (-margin, 0), (0, margin), (0, -margin), (0, 0)):
                inside = all(nx * (x + dx) + ny * (y + dy) <= c + z - PLATE_TOP for nx, ny, c in lines)
                assert inside and self.surface_z(x + dx, y + dy, THIGH_R) < z - 1.0, f"{what} at {x}, {y} runs out of plastic"
            for keep, gap in ((windows, 1.5), (strip, 1.5), (self.slot, 2.0), (tunnel, 1.0)):
                assert not keep.buffer(gap + margin).contains(Point(x, y)), f"{what} at {x}, {y} is too close to something"

        for x, y in JOINS:
            assert self.inner.buffer(-(CSK_D / 2 + 1.0)).contains(Point(x, y)), f"screw at {x}, {y} is off the floor"
            solid_under(x, y, JOIN_LEN - FACET_TRAY + 1.2, JOIN_PILOT / 2 + 1.5, "screw")
            top = top.cut(cq.Workplane("XY").workplane(offset=PLATE_TOP - 1).center(x, y).circle(BOLT_D / 2).extrude(5))
            top = top.cut(cq.Workplane(obj=cq.Solid.makeCone(BOLT_D / 2, CSK_D / 2, CSK_H, cq.Vector(x, y, -CSK_H), cq.Vector(0, 0, 1))))
            top = top.cut(cq.Workplane("XY").workplane(offset=0).center(x, y).circle(CSK_D / 2).extrude(1))
            back = back.cut(cq.Workplane("XY").workplane(offset=PLATE_TOP - (JOIN_LEN - FACET_TRAY + 0.8)).center(x, y).circle(JOIN_PILOT / 2).extrude(JOIN_LEN))
        for x, y in PINS:
            assert self.outer.buffer(-3).contains(Point(x, y)), f"pin at {x}, {y} is too near the edge"
            solid_under(x, y, PIN_BACK + 0.6, PIN_D / 2 + 1.5, "pin")
            top = top.cut(cq.Workplane("XY").workplane(offset=PLATE_TOP - 1).center(x, y).circle(PIN_D / 2).extrude(PIN_TOP + 1))
            back = back.cut(cq.Workplane("XY").workplane(offset=PLATE_TOP - PIN_BACK).center(x, y).circle(PIN_D / 2).extrude(PIN_BACK + 1))
        return top, back

    def joins(self):
        """The screws that hold the faceted holster's two parts together, for the viewer."""
        out = None
        for x, y in JOINS:
            head = cq.Workplane(obj=cq.Solid.makeCone(1.45, CSK_D / 2 - 0.2, CSK_H, cq.Vector(x, y, -CSK_H), cq.Vector(0, 0, 1)))
            screw = head.union(cq.Workplane("XY").workplane(offset=-JOIN_LEN).center(x, y).circle(1.45).extrude(JOIN_LEN - CSK_H + 0.1))
            out = screw if out is None else out.add(screw)
        return out

    def name_plate(self, mirrored=False):
        """The name, to cut into the front face. The left half is a mirror image, so its name is cut after mirroring."""
        plan = self.hull_plan()
        points = list(orient(plan, 1.0).exterior.coords)[:-1]
        front = min(range(len(points)), key=lambda i: points[i][0] + points[(i + 1) % len(points)][0])  # the inner edge
        nx, ny, c = self.face_lines(plan, self.outer)[front]
        (px, py), (qx, qy) = points[front], points[(front + 1) % len(points)]
        mx, my = (px + qx) / 2, (py + qy) / 2
        down = 9.0  # how far below the tray the middle of the name sits
        out = c - (nx * mx + ny * my) - down
        origin = cq.Vector(mx + nx * out, my + ny * out, -FACET_TRAY - down)
        normal = cq.Vector(nx, ny, -1).normalized()
        reading = cq.Vector(0, 1 if mirrored else -1, 0)  # left to right, seen from outside
        if mirrored:
            origin, normal = cq.Vector(-origin.x, origin.y, origin.z), cq.Vector(-normal.x, normal.y, normal.z)
        reading = (reading - normal * reading.dot(normal)).normalized()
        plane = cq.Plane(origin=origin.toTuple(), xDir=reading.toTuple(), normal=normal.toTuple())
        return cq.Workplane(plane).text(NAME, NAME_SIZE, -NAME_DEPTH, fontPath=str(FONT), halign="center", valign="center", combine=False)


def solid(work):
    return work.val() if len(work.vals()) == 1 else cq.Compound.makeCompound(work.vals())


def report(name, work):
    shape = solid(work)
    bb = shape.BoundingBox()
    grams = shape.Volume() / 1000 * 1.27
    print(f"{name}: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, {shape.Volume() / 1000:.1f} cm3 "
          f"(about {grams:.0f} g solid), valid={shape.isValid()}, solids={len(shape.Solids())}")


def printed_grams(work):
    """A rough guess at the plastic a slicer would use, without supports."""
    shape = solid(work)
    volume, area = shape.Volume() / 1000, shape.Area() / 100
    return (area * SKIN + (volume - area * SKIN) * INFILL) * PETG


def overlap(a, b):
    try:
        return solid(a.intersect(b)).Volume()
    except Exception:
        return 0.0


def on_bed(work, upside_down=False):
    """Turns a part over if asked, and stands it on z = 0."""
    if upside_down:
        work = work.rotate((0, 0, 0), (1, 0, 0), 180)
    return work.translate((0, 0, -solid(work).BoundingBox().zmin))


def export(work, name):
    OUT.mkdir(exist_ok=True)
    for ext in ("step", "stl", "3mf"):
        cq.exporters.export(work, str(OUT / f"{name}.{ext}"), tolerance=0.05, angularTolerance=0.2)


def describe(name, work):
    for s in solid(work).Solids():
        c, bb = s.Center(), s.BoundingBox()
        print(f"  {name} piece: {s.Volume():.1f} mm3 at ({c.x:.0f}, {c.y:.0f}, {c.z:.0f}), "
              f"x {bb.xmin:.0f}..{bb.xmax:.0f} y {bb.ymin:.0f}..{bb.ymax:.0f} z {bb.zmin:.0f}..{bb.zmax:.0f}")


def main():
    h = Holster()
    print(f"back of the holster: {BACK_MIN:.1f} mm at its thinnest, {h.back:.1f} mm at its deepest")
    print(f"clip: {h.length:.0f} mm from the top of the J to the tip, {TONGUE_DEPTH:.0f} mm below the pocket edge")
    body, clip, keyboard = h.body(), h.clip(), h.keyboard()
    top, back = h.split(h.body(faceted=True))
    named = back.cut(h.name_plate())
    steel = h.clip(steel=True)
    fit = h.test_fit(body)
    report("holster", body)
    report("faceted top", top)
    report("faceted back", named)
    print(f"printed, roughly: plain {printed_grams(body):.0f} g of PETG before supports; faceted "
          f"{printed_grams(top):.0f} g top and {printed_grams(named):.0f} g back, with no supports")
    report("clip", clip)
    report("clip-steel", steel)
    print(f"thinnest wall beside the steel strip: {h.spine_walls():.2f} mm")
    thread, spare = h.bolt_check()
    print(f"screws: {thread:.1f} mm of thread in the insert, stopping {spare:.1f} mm short of the end of the hole")
    print("screw heads below the floor: " + ", ".join(f"{sunk:.1f} mm" for sunk in h.head_depths()))
    for material, modulus in (("PETG", 2000.0), ("nylon", 1400.0)):
        force, strain = h.spring_check(modulus)
        print(f"clip in {material}: about {force:.1f} N of clamp, peak strain {strain * 100:.2f}%")
    report("test fit", fit)
    sheet = h.outline_sheet()
    report("outline sheet", sheet)
    if len(solid(body).Solids()) > 1:
        describe("holster", body)
    for name, part in (("holster", body), ("faceted top", top)):
        print(f"keyboard into {name}: {overlap(keyboard, part):.2f} mm3 of overlap (should be about 0)")
        if overlap(keyboard, part) > 1:
            describe("overlap", keyboard.intersect(part))
    print(f"clip into the plain holster: {overlap(clip, body):.2f} mm3 of overlap (the preload, at the tip)")
    print(f"clip into the faceted top: {overlap(clip, top):.2f} mm3 (should be about 0: the plate only touches it)")
    print(f"clip into the faceted back: {overlap(clip, back):.2f} mm3 (the preload, at the tip)")
    mirror = lambda w: w.mirror("YZ")
    for name, part in (("holster", body), ("clip", clip), ("clip-steel", steel), ("test-fit", fit)):
        export(part, f"{name}-right")
        export(mirror(part), f"{name}-left")
    # The faceted parts come out the way they print: the top keyboard side up, the back upside down. The
    # name is cut after mirroring, so it reads the right way round on both halves
    export(on_bed(top), "holster-faceted-top-right")
    export(on_bed(mirror(top)), "holster-faceted-top-left")
    export(on_bed(named, upside_down=True), "holster-faceted-back-right")
    export(on_bed(mirror(back).cut(h.name_plate(mirrored=True)), upside_down=True), "holster-faceted-back-left")
    for old in OUT.glob("holster-faceted-right.*"):
        old.unlink()  # the one-piece faceted holster, from before the split
    for old in OUT.glob("holster-faceted-left.*"):
        old.unlink()
    export(sheet, "outline-sheet")  # one file does both halves: flip it over for the left
    print("wrote", len(list(OUT.iterdir())), "files to", OUT)


if __name__ == "__main__":
    main()
