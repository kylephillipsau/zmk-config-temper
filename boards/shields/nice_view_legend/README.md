# nice!view layer legend

A copy of ZMK's `nice_view` shield with different screens, trimmed from the one on Kyles Sofle. Each
layer's keys are drawn where they sit on the board, so each screen describes the hand it's on.

The left (central) screen, `widgets/status.c`, shows both batteries, the layer, the Bluetooth slots,
held modifiers and Caps Lock. Below them is a card: the combos on Base, or the left hand's keys on
the held layer.

The right (peripheral) screen, `widgets/peripheral_status.c`, has the battery and link in its top 20
rows. Below them are the right hand's keys on the held layer, or on Base the name, a drawing of the
board, and which thumbs open each layer.

## How it works

`widgets/legend_layer.c` raises a one-byte `zmk_legend_layer_changed` event on the left half
whenever the highest active layer changes, and relays it to the right half with the ZMK fork's
`ZMK_RELAY_EVENT_CENTRAL_TO_PERIPHERAL`. Both halves need `CONFIG_ZMK_SPLIT_RELAY_EVENT=y`, set in
`nice_view_legend.conf`. The right half swaps its image to match, and goes back to Base if the link
to the left half drops.

`widgets/peripheral_charging.c` goes the other way, with `ZMK_RELAY_EVENT_PERIPHERAL_TO_CENTRAL`.
The right half tells the left whether it's on USB power when it's plugged in or out, and again 5
seconds after the link comes up. Both screens show a bolt instead of a level for a half on USB, as
the nice!nano reads a charging battery as full.

Holding a layer on the left thumbs isn't activity on the right half, so its display timer stops 30
seconds after the last right-hand key. `set_legend()` calls `lv_refr_now()` so the legend still
appears straight away.

## Changing the screens

`widgets/legend_art.c` and `widgets/status_glyphs.h` are generated. Edit `art/screens.py`, then:

```sh
uv run art/screens.py
```

If the keymap changes, update the legends in `art/screens.py` to match.

## Settings

`CONFIG_NICE_VIEW_WIDGET_INVERTED=y` inverts the colours, as with the stock shield.
