# Thigh holster

![The faceted holster pulled apart in a line: the keyboard, its screws, the holster's top and back, the clip and its steel spine](../docs/holster/exploded.jpg)

A holster for wearing the Temper on your thighs, with a swappable clip that goes into a pocket. The
keyboard's printed case isn't changed, and it lifts straight out for desk use.

The test fit has been printed, and the keyboard fits it. The full holster hasn't been printed yet.

## How it's worn

Each half goes on its own side's thigh, turned 180 degrees from how it sits on a desk: thumbs up,
USB towards the knee, keys facing out. Your hanging hand meets the keys the way it does at a desk.

The clip is a J, like a knife clip. It hooks over the pocket edge and runs straight down inside the
pocket, so the seam carries the weight and the keyboard sits flush below the edge. The top of the J
is cut at the pocket edge's angle, so it sits along the edge instead of on one corner.

## Side bumps

Knocks from the side are the most likely to dislodge it, and these all resist them:

- The tongue runs 80 mm down inside the pocket, on the keyboard's centre line.
- Ribs along the tongue press the fabric into grooves in the holster. They slide in easily and resist
  sideways slip.
- The clip's plate sits in a recess, so its walls take a sideways load instead of the screws.
- Bumpers on both sides stand just above the keycaps, so a knock lands on the holster. The right one
  stops short of the thumb-end corner, so the keyboard can still rock in at an angle. The left one
  starts above the power switch, so nothing stands beside the thumb keys. Both ramp up at 45 degrees
  instead of ending square.

The holster has no clearance for the optional nice!view screens, so take them off before you wear it.

## Parts

`holster.py` writes all of these to `out/`, as STEP, STL and 3MF, for each side.

| Part | Print in | How |
|---|---|---|
| `outline-sheet` | Anything | Flat, no supports. An open frame, 1 mm thick, with the case's exact outline. It does both halves: flip it over for the left |
| `test-fit` | Anything | Flat, with supports. A thin slice with every fit in it |
| `holster` | PETG | Keyboard side up, with tree supports under all of the curved back. That face sits against your leg, so support marks won't show |
| `holster-faceted-top` | PETG | Keyboard side up, flat on its floor, with supports. The faceted holster's top, which holds the keyboard |
| `holster-faceted-back` | PETG | Upside down, flat on the face that meets the top, so the side against your leg prints as a smooth top surface. No supports |
| `clip` | Nylon, or PETG | On its long edge, so the layers run along the tongue, with 100% infill. Avoid PLA and carbon-filled filament, which are brittle |
| `clip-steel` | Same as `clip` | The same clip with a channel for a steel spine |

Set supports to build plate only, which keeps them out of the keyboard's pocket. A few can still
reach into the slit under the latch, and the latch arm starts in mid-air and can stick to the floor,
so run a thin blade through the slit before using a part.

Each clip also needs two M3 x 4 heat-set inserts, 4.2 to 4.6 mm across, and two M3 x 6 countersunk
screws (a countersunk screw's length includes its head). The inserts go into the clip, and the
screws go in from the keyboard side, where the keyboard covers them. The clip's plate is flat on top
and bears straight on the 3 mm floor under the keyboard, so both heads sit flush and both screws get
about 2.9 mm of thread in the insert.

### Plain or faceted

The two holsters fit the keyboard and the clip the same way, and differ only below the keyboard.

The plain holster has a solid back that follows your leg, with its edges rounded where they meet it.

On the faceted holster, every face under the keyboard leans in at 45 degrees, the steepest a printer
manages without supports. Two windows beside the clip go right through, the far ends of the rails
ramp down at 45 degrees, and SHORT TEMPER is cut into the front face, reading the right way round on
both halves. The tether runs through a tunnel across a corner instead of a lug, so nothing sticks
out. It prints as two parts, so neither needs supports under it.

`holster.py` prints a rough guess at the plastic each takes: about 67 g of PETG for the plain one
before supports, and about 40 g for the faceted top and 34 g for its back, which need none. Most of
the plain one's back is already infill, so reshaping it saves less than it looks, and splitting the
faceted one adds solid skins where the two parts meet.

### The faceted holster's two parts

It splits along the underside of the floor the keyboard sits on. The top holds everything the test
fit proved: the walls, lips, latch, rails, peg and floor. The back holds everything that depends on
your leg: its curve, the angles, and the depth. If it doesn't sit right on your leg, change
`THIGH_R`, `TILT`, `YAW` or `PITCH` and reprint just the back.

The clip's screws hold the clip to the top through an opening in the back, so the clip's load never
goes through the joint. The back joins the top with:

- two M3 x 8 countersunk screws, which go in from the keyboard side and cut their own thread in the
  back, with no inserts;
- three pieces of 1.75 mm filament, each about 6 mm long, which line the parts up in their holes.

To assemble it, push the filament pins into the back, press the top on, and drive the two M3 x 8
screws in snug, not tight, as they thread into plastic. Then fit the clip with its own screws. Once
you're happy with how it sits, you can glue the two parts instead: sand both faces and use two-part
epoxy or a plastic-bonding superglue, as ordinary superglue holds PETG only moderately.

The faceted one touches your leg across about the same width in the middle, and less towards the
knee. That's untested.

### Steel spine

`clip-steel` seals in a strip of spring steel 12 to 13 mm wide, up to 0.7 mm thick and 49 mm long. A
0.6 or 0.7 mm feeler gauge blade is the cleanest source, if its sides are parallel and it's no wider
than 13 mm. A piece of bi-metal hacksaw blade also works, as its back is flexible, if you cut it from
the middle to miss the end holes. Cut either with a rotary tool and a cut-off wheel, wear eye
protection, and take the burrs off the ends.

Printed on its long edge, the channel is open from the top until about 20.7 mm up. Add a pause
there, drop the strip in, and resume. Check the layer in your slicer's preview.

The strip is there to hold the clip together if the plastic ever cracks. It's only about a sixth as
stiff as the PETG around it, so the plastic still sets how hard the clip grips.

### Tether

Tie 4 mm paracord to a belt loop, so the keyboard can't hit the ground if the clip lets go. On the
plain holster it goes through the lug at the thumb end. On the faceted one it goes through a tunnel
across the thumb-end corner on the pinky side, in one face and out the other. Melt and taper the
cord's end to thread it through.

## Trial prints

Bambu Studio may say a 3MF from here has an invalid config and load only the geometry. These files
carry no print settings, so that's harmless, but you'll need to set them yourself. The STL loads the
same shape.

Cheap filament and low infill are fine for checking fit and comfort, in this order:

1. `outline-sheet`, in any filament with ironing off. Lay it on the table and set the right half on
   it, keycaps up. Run a fingernail around the join: the edges should be flush all the way round,
   within about 0.5 mm. The ring inside the frame is the slot: its outer edge is the slot's outline
   and its inner edge is the peg. For the clearest view, switch the half off, rest it upside down on
   its keycaps and lay the frame on its underside. The ring's outer edge should follow the slot,
   except where it joins the rim, and the notches should line up with the middle of the USB port and
   the power switch. Then flip the sheet over and repeat with the left half. Note where anything's
   out, and by how much.
2. `test-fit`, with 2 walls and 15% infill. Check the keyboard drops in, the peg meets the slot, the
   lips hook on, and the latch clicks. If it's tight under the lips or the latch, shave any droop off
   their undersides before changing `CLEARANCE`.
3. `holster` and `clip`, with 3 walls and 15% infill. Wear it, and check where it sits, how the rails
   feel, and how it reaches your hands.
4. The final print, with the filament and settings from the parts table.

Don't judge the clip's strength from a trial print: PLA is stiff and snaps easily. If `CLEARANCE`
was right in one filament, check it again in another, as they shrink differently.

## Fitting the keyboard

1. Slide the clip over the pocket edge, so the tongue goes down inside the pocket.
2. Hook the USB end under the lips at the bottom of the holster.
3. Rock the keyboard in, so the peg goes into the slot.
4. Press the thumb end until the latch clicks.

The walls and rails are chamfered, so it finds its way in by feel. To take it out, slide your thumb
along the wall to the grooved paddle on the latch, push it along the edge, away from the slit, and
lift the thumb end. The paddle stands out from the wall, so the push levers the latch open, and it
has no hook or gap to catch on clothes.

## Changing the fit

The settings are at the top of `holster.py`. Rerun it with `uv run case/holster.py`.

| Setting | What it does |
|---|---|
| `CASE_H` | Height of the printed case, measured at 8 mm |
| `CLEARANCE` | Gap around the case. Raise it if the test fit is tight |
| `THIGH_R` | Radius of the curve behind the holster |
| `TILT` | How far the fingers point away from straight down |
| `YAW` | How far the keys turn towards your palm. The front edge stands further off the leg |
| `PITCH` | How far the thumb end stands further off the leg than the USB end |
| `POCKET_ANGLE` | The slope of the pocket edge, where the clip goes over it |
| `TONGUE_DEPTH` | How far the clip reaches below the pocket edge. Keep it shorter than the pocket |
| `BACK_MAX` | The deepest the holster gets behind the keyboard |
| `CLIP_PRELOAD` | How hard the clip grips. The script prints the force, and the strain it puts on the plastic |

`case-outline.json` is the case outline, about 116.5 x 95.7 mm, traced from photos of the real case's
underside. Each half's bottom plate follows the PCB, so fitting its edges to the exact outline in
`keymap_img/temper-board.yaml` brings the photo to true scale without a ruler, to within 0.06 mm. The
two halves mirror each other to about 0.1 mm, and the file is their average. The wall is about 2.5 to
2.7 mm on most edges, and up to about 3.1 mm along the thumb edge, which is one smooth curve where the
board has straight sections. `board_corner` places the board in that outline, so the USB port, switch
and keys all follow it. `SLOT` is about 17.2 x 8.9 mm, measured from the board the same way.
