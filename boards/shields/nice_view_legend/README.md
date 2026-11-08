# nice!view layer legend

A copy of ZMK's `nice_view` shield with different screens, trimmed from the one on Kyles Sofle:

- **Right (peripheral):** the battery and link in the top 20 rows, then the held layer's keys, or on
  Base the name, a drawing of the board, and which thumbs open each layer
  (`widgets/peripheral_status.c`).
- **Left (central):** both batteries, the layer, the Bluetooth slots, held modifiers and Caps Lock,
  over a fixed card of the combos (`widgets/status.c`).

## How it works

`widgets/legend_layer.c` raises a one-byte `zmk_legend_layer_changed` event on the left half
whenever the highest active layer changes, and relays it to the right half with the ZMK fork's
`ZMK_RELAY_EVENT_CENTRAL_TO_PERIPHERAL` (`CONFIG_ZMK_SPLIT_RELAY_EVENT=y` on both halves, set in
`nice_view_legend.conf`). The right half swaps the image to match, and goes back to Base if the link
to the left half drops.

Holding a layer on the left thumbs isn't activity on the right half, so after 30 seconds without a
right-hand key its display timer has stopped. `set_legend()` calls `lv_refr_now()` so the legend
still appears straight away.

## Changing the screens

`widgets/legend_art.c` and `widgets/status_glyphs.h` are generated. Edit `art/screens.py`, then:

```sh
uv run art/screens.py
```

If the keymap changes, update the legends in `art/screens.py` to match.

## Settings

`CONFIG_NICE_VIEW_WIDGET_INVERTED=y` inverts the colours, as with the stock shield.
