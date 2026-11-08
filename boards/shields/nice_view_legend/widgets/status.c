/*
 *
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 *
 * Left (central) screen: a status area (both batteries, layer, Bluetooth slots, held modifiers and
 * Caps Lock) above a card: the base layer's combos, or while a layer is held, the left hand's keys.
 * The layout mirrors left_screen() in art/screens.py, and the fonts and icons are generated from
 * the same sources, so the mockups match the device.
 *
 * The status area is a 68x68 canvas covering portrait rows 0-67, drawn upright and then rotated
 * into the panel's landscape orientation. The cards below it are prebuilt images, swapped when the
 * layer changes, so nothing is drawn at runtime but the status area, and only when it changes.
 */

#include <stdio.h>
#include <string.h>
#include <zephyr/kernel.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <dt-bindings/zmk/hid_usage.h>
#include <dt-bindings/zmk/hid_usage_pages.h>
#include <dt-bindings/zmk/modifiers.h>
#include <zmk/battery.h>
#include <zmk/display.h>
#include "draw.h"
#include "peripheral_charging.h"
#include "status.h"
#include "status_glyphs.h"
#include <zmk/events/usb_conn_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/events/endpoint_changed.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/usb.h>
#include <zmk/ble.h>
#include <zmk/endpoints.h>
#include <zmk/keymap.h>
#if IS_ENABLED(CONFIG_ZMK_HID_INDICATORS)
#include <zmk/hid_indicators.h>
#include <zmk/events/hid_indicators_changed.h>
#endif
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
#include <zmk/split/central.h>
#endif

LV_FONT_DECLARE(lv_font_silkscreen_8);
LV_FONT_DECLARE(lv_font_silkscreen_bold_8);
LV_FONT_DECLARE(lv_font_jersey_1x);
LV_IMG_DECLARE(left_combos);
LV_IMG_DECLARE(left_num);
LV_IMG_DECLARE(left_sym);
LV_IMG_DECLARE(left_nav);
LV_IMG_DECLARE(left_system);

#define SCREEN_W 68

// Caps Lock in the HID keyboard LED report
#define LED_CAPS_LOCK BIT(1)

static sys_slist_t widgets = SYS_SLIST_STATIC_INIT(&widgets);

struct output_status_state {
    struct zmk_endpoint_instance selected_endpoint;
    int active_profile_index;
    bool active_profile_connected;
    bool active_profile_bonded;
    bool profiles_connected[NICEVIEW_PROFILE_COUNT];
    bool profiles_bonded[NICEVIEW_PROFILE_COUNT];
};

struct layer_status_state {
    zmk_keymap_layer_index_t index;
    const char *label;
};

struct peripheral_battery_state {
    int16_t level;
};

struct peripheral_charging_state {
    bool charging;
};

struct mods_state {
    uint8_t mods;
};

struct caps_state {
    bool on;
};

/* ---------------------------------------------------------------------------------------------
 * Drawing in portrait coordinates: struct frame and the helpers in draw.h.
 */

static void dashed_square(const struct frame *f, int x, int y, int size, lv_color_t c) {
    for (int k = 0; k < size; k += 2) {
        put_px(f, x + k, y, c);
        put_px(f, x + k, y + size - 1, c);
        put_px(f, x, y + k, c);
        put_px(f, x + size - 1, y + k, c);
    }
}

static void draw_battery_column(const struct frame *f, int x, char label, int level,
                                bool charging) {
    lv_color_t ink = LVGL_FOREGROUND;
    char text[12] = {label, '\0'};

    if (charging) {
        // A charging half reads its battery as full whatever its charge, so show no level. The
        // column's place says which half it is.
        draw_glyph(f, x, 0, &glyph_bolt, ink);
        draw_text(f, &lv_font_silkscreen_8, x, 31, 0, LV_TEXT_ALIGN_RIGHT, ink, "CHG");
        return;
    }
    draw_text(f, &lv_font_silkscreen_bold_8, x, 31, 0, LV_TEXT_ALIGN_LEFT, ink, text);

    if (level < 0) {
        strcpy(text, "--");
    } else {
        snprintf(text, sizeof(text), "%d%%", level);
    }
    draw_text(f, &lv_font_silkscreen_8, x, 31, 0, LV_TEXT_ALIGN_RIGHT, ink, text);

    for (int i = 0; i < 10; i++) {
        bool on = level >= 0 && i < (level + 5) / 10;
        fill(f, x + i * 3, on ? 8 : 11, 2, on ? 4 : 1, ink);
    }
}

static void draw_slots(const struct frame *f, const struct status_state *state) {
    lv_color_t ink = LVGL_FOREGROUND, paper = LVGL_BACKGROUND;

    if (state->selected_endpoint.transport == ZMK_TRANSPORT_USB) {
        fill(f, 0, 34, SCREEN_W, 12, ink);
        draw_text(f, &lv_font_silkscreen_bold_8, 0, SCREEN_W, 38, LV_TEXT_ALIGN_CENTER, paper,
                  "USB");
        return;
    }

    for (int i = 0; i < NICEVIEW_PROFILE_COUNT; i++) {
        int x = 1 + i * 13, y = 34;
        bool active = i == state->active_profile_index;
        bool solid = active && state->profiles_connected[i];
        char digit[2] = {'0' + i, '\0'}; // slots are numbered 0-4, as in the keymap

        if (solid) {
            fill(f, x, y, 12, 12, ink);
        } else if (active) {
            // selected but not connected yet: double outline
            outline(f, x, y, 12, 12, ink);
            outline(f, x + 1, y + 1, 10, 10, ink);
        } else if (state->profiles_connected[i]) {
            outline(f, x, y, 12, 12, ink);
        } else if (state->profiles_bonded[i]) {
            dashed_square(f, x, y, 12, ink);
        }
        draw_text(f, &lv_font_silkscreen_bold_8, x, 12, y + 3, LV_TEXT_ALIGN_CENTER,
                  solid ? paper : ink, digit);
    }
}

static void draw_badges(const struct frame *f, const struct status_state *state) {
    static const struct {
        const struct glyph *glyph;
        uint8_t mods;
    } badges[] = {
        {&glyph_cmd, MOD_LGUI | MOD_RGUI},  {&glyph_opt, MOD_LALT | MOD_RALT},
        {&glyph_ctrl, MOD_LCTL | MOD_RCTL}, {&glyph_shift, MOD_LSFT | MOD_RSFT},
        {&glyph_caps, 0},
    };
    lv_color_t ink = LVGL_FOREGROUND, paper = LVGL_BACKGROUND;

    for (int i = 0; i < ARRAY_SIZE(badges); i++) {
        const struct glyph *g = badges[i].glyph;
        int x = i * 14;
        bool on = badges[i].mods ? (state->mods & badges[i].mods) != 0 : state->caps_lock;

        if (on) {
            fill(f, x, 50, 12, 13, ink);
        } else {
            outline(f, x, 50, 12, 13, ink);
        }
        draw_glyph(f, x + (12 - g->w) / 2, 50 + (13 - g->h) / 2, g, on ? paper : ink);
    }
}

static void draw_status(lv_obj_t *widget, struct zmk_widget_status *w) {
    const struct status_state *state = &w->state;
    struct frame f = {.canvas = lv_obj_get_child(widget, 0), .buf = w->cbuf, .y0 = 0};
    lv_color_t ink = LVGL_FOREGROUND, paper = LVGL_BACKGROUND;
    char layer[12];

    fill(&f, 0, 0, CANVAS_SIZE, CANVAS_SIZE, paper);

    draw_battery_column(&f, 0, 'L', state->battery, state->charging);
    draw_battery_column(&f, 36, 'R', state->peripheral_battery, state->peripheral_charging);

    if (state->layer_label != NULL && state->layer_label[0] != '\0') {
        snprintf(layer, sizeof(layer), "%s", state->layer_label);
    } else {
        snprintf(layer, sizeof(layer), "LAYER %d", state->layer_index);
    }
    for (char *c = layer; *c; c++) {
        if (*c >= 'a' && *c <= 'z') {
            *c -= 'a' - 'A'; // the keymap names the base layer "Base"
        }
    }
    fill(&f, 0, 15, SCREEN_W, 16, ink);
    draw_text(&f, &lv_font_jersey_1x, 0, SCREEN_W, 18, LV_TEXT_ALIGN_CENTER, paper, layer);

    draw_slots(&f, state);
    draw_badges(&f, state);
    fill(&f, 0, 65, SCREEN_W, 1, ink);

    rotate_canvas(f.canvas, f.buf);
}

/* ---------------------------------------------------------------------------------------------
 * State listeners
 */

static void battery_status_update_cb(struct battery_status_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        bool was_charging = widget->state.charging;
#if IS_ENABLED(CONFIG_USB_DEVICE_STACK)
        widget->state.charging = state.usb_present;
#endif
        widget->state.battery = state.level;
        draw_status(widget->obj, widget);
        if (widget->state.charging != was_charging) {
            lv_refr_now(NULL); // as in peripheral_charging_update_cb
        }
    }
}

static struct battery_status_state battery_status_get_state(const zmk_event_t *eh) {
    const struct zmk_battery_state_changed *ev = eh ? as_zmk_battery_state_changed(eh) : NULL;
    return (struct battery_status_state){
        .level = (ev != NULL) ? ev->state_of_charge : zmk_battery_state_of_charge(),
#if IS_ENABLED(CONFIG_USB_DEVICE_STACK)
        .usb_present = zmk_usb_is_powered(),
#endif /* IS_ENABLED(CONFIG_USB_DEVICE_STACK) */
    };
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_battery_status, struct battery_status_state,
                            battery_status_update_cb, battery_status_get_state)

ZMK_SUBSCRIPTION(widget_battery_status, zmk_battery_state_changed);
#if IS_ENABLED(CONFIG_USB_DEVICE_STACK)
ZMK_SUBSCRIPTION(widget_battery_status, zmk_usb_conn_state_changed);
#endif /* IS_ENABLED(CONFIG_USB_DEVICE_STACK) */

static void peripheral_battery_update_cb(struct peripheral_battery_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        widget->state.peripheral_battery = state.level;
        draw_status(widget->obj, widget);
    }
}

static struct peripheral_battery_state peripheral_battery_get_state(const zmk_event_t *eh) {
    static int16_t level = -1;
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
    const struct zmk_peripheral_battery_state_changed *ev =
        eh ? as_zmk_peripheral_battery_state_changed(eh) : NULL;
    uint8_t fetched;

    if (ev != NULL) {
        if (ev->source == 0) {
            level = ev->state_of_charge;
        }
    } else if (zmk_split_central_get_peripheral_battery_level(0, &fetched) == 0) {
        level = fetched;
    }
#endif
    return (struct peripheral_battery_state){.level = level};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_peripheral_battery, struct peripheral_battery_state,
                            peripheral_battery_update_cb, peripheral_battery_get_state)
#if IS_ENABLED(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING)
ZMK_SUBSCRIPTION(widget_peripheral_battery, zmk_peripheral_battery_state_changed);
#endif

// The right half sends this when it's plugged in or out, and again each time it reconnects
// (widgets/peripheral_charging.c).
static void peripheral_charging_update_cb(struct peripheral_charging_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        if (widget->state.peripheral_charging != state.charging) {
            widget->state.peripheral_charging = state.charging;
            draw_status(widget->obj, widget);
            // Plugging the right half in isn't a key press here, so the display timer may be
            // stopped (CONFIG_ZMK_DISPLAY_BLANK_ON_IDLE). Draw it now.
            lv_refr_now(NULL);
        }
    }
}

static struct peripheral_charging_state peripheral_charging_get_state(const zmk_event_t *eh) {
    static bool charging = false;
    const struct zmk_peripheral_charging_changed *ev =
        eh ? as_zmk_peripheral_charging_changed(eh) : NULL;
    if (ev != NULL) {
        charging = ev->charging;
    }
    return (struct peripheral_charging_state){.charging = charging};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_peripheral_charging, struct peripheral_charging_state,
                            peripheral_charging_update_cb, peripheral_charging_get_state)
ZMK_SUBSCRIPTION(widget_peripheral_charging, zmk_peripheral_charging_changed);

static void output_status_update_cb(struct output_status_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        widget->state.selected_endpoint = state.selected_endpoint;
        widget->state.active_profile_index = state.active_profile_index;
        widget->state.active_profile_connected = state.active_profile_connected;
        widget->state.active_profile_bonded = state.active_profile_bonded;
        for (int i = 0; i < NICEVIEW_PROFILE_COUNT; ++i) {
            widget->state.profiles_connected[i] = state.profiles_connected[i];
            widget->state.profiles_bonded[i] = state.profiles_bonded[i];
        }
        draw_status(widget->obj, widget);
    }
}

static struct output_status_state output_status_get_state(const zmk_event_t *_eh) {
    struct output_status_state state = {
        .selected_endpoint = zmk_endpoints_selected(),
        .active_profile_index = zmk_ble_active_profile_index(),
        .active_profile_connected = zmk_ble_active_profile_is_connected(),
        .active_profile_bonded = !zmk_ble_active_profile_is_open(),
    };
    for (int i = 0; i < MIN(NICEVIEW_PROFILE_COUNT, ZMK_BLE_PROFILE_COUNT); ++i) {
        state.profiles_connected[i] = zmk_ble_profile_is_connected(i);
        state.profiles_bonded[i] = !zmk_ble_profile_is_open(i);
    }
    return state;
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_output_status, struct output_status_state,
                            output_status_update_cb, output_status_get_state)
ZMK_SUBSCRIPTION(widget_output_status, zmk_endpoint_changed);

#if IS_ENABLED(CONFIG_USB_DEVICE_STACK)
ZMK_SUBSCRIPTION(widget_output_status, zmk_usb_conn_state_changed);
#endif
#if defined(CONFIG_ZMK_BLE)
ZMK_SUBSCRIPTION(widget_output_status, zmk_ble_active_profile_changed);
#endif

// Below the status area: the combos on Base, and the left hand's keys while a layer is held. The
// layer numbers follow config/temper.keymap, as legend_for_layer() in peripheral_status.c does.
static const lv_img_dsc_t *card_for_layer(uint8_t layer) {
    switch (layer) {
    case 1:
        return &left_num;
    case 2:
        return &left_sym;
    case 3:
        return &left_nav;
    case 4:
        return &left_system;
    default:
        return &left_combos;
    }
}

static void layer_status_update_cb(struct layer_status_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        widget->state.layer_index = state.index;
        widget->state.layer_label = state.label;
        draw_status(widget->obj, widget);

        lv_obj_t *card = lv_obj_get_child(widget->obj, 1);
        const lv_img_dsc_t *src = card_for_layer(state.index);
        if (lv_img_get_src(card) != src) {
            lv_img_set_src(card, src);
        }
    }
}

static struct layer_status_state layer_status_get_state(const zmk_event_t *eh) {
    zmk_keymap_layer_index_t index = zmk_keymap_highest_layer_active();
    return (struct layer_status_state){
        .index = index, .label = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(index))};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_layer_status, struct layer_status_state, layer_status_update_cb,
                            layer_status_get_state)

ZMK_SUBSCRIPTION(widget_layer_status, zmk_layer_state_changed);

static void mods_update_cb(struct mods_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        // this fires for every key press, so only redraw when a modifier actually changed
        if (widget->state.mods != state.mods) {
            widget->state.mods = state.mods;
            draw_status(widget->obj, widget);
        }
    }
}

// Track held modifier keys from key events. ZMK doesn't raise zmk_modifiers_state_changed, and
// reading the HID report here could race the HID listener handling the same event.
static struct mods_state mods_get_state(const zmk_event_t *eh) {
    static uint8_t held;
    const struct zmk_keycode_state_changed *ev = eh ? as_zmk_keycode_state_changed(eh) : NULL;

    if (ev != NULL && ev->usage_page == HID_USAGE_KEY &&
        ev->keycode >= HID_USAGE_KEY_KEYBOARD_LEFTCONTROL &&
        ev->keycode <= HID_USAGE_KEY_KEYBOARD_RIGHT_GUI) {
        uint8_t bit = BIT(ev->keycode - HID_USAGE_KEY_KEYBOARD_LEFTCONTROL);
        held = ev->state ? (held | bit) : (held & ~bit);
    }
    return (struct mods_state){.mods = held};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_mods, struct mods_state, mods_update_cb, mods_get_state)
ZMK_SUBSCRIPTION(widget_mods, zmk_keycode_state_changed);

static void caps_update_cb(struct caps_state state) {
    struct zmk_widget_status *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        if (widget->state.caps_lock != state.on) {
            widget->state.caps_lock = state.on;
            draw_status(widget->obj, widget);
        }
    }
}

static struct caps_state caps_get_state(const zmk_event_t *eh) {
#if IS_ENABLED(CONFIG_ZMK_HID_INDICATORS)
    return (struct caps_state){.on = (zmk_hid_indicators_get_current_profile() & LED_CAPS_LOCK) != 0};
#else
    return (struct caps_state){.on = false};
#endif
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_caps, struct caps_state, caps_update_cb, caps_get_state)
#if IS_ENABLED(CONFIG_ZMK_HID_INDICATORS)
ZMK_SUBSCRIPTION(widget_caps, zmk_hid_indicators_changed);
#endif

int zmk_widget_status_init(struct zmk_widget_status *widget, lv_obj_t *parent) {
    widget->obj = lv_obj_create(parent);
    lv_obj_set_size(widget->obj, 160, 68);
    lv_obj_t *top = lv_canvas_create(widget->obj);
    lv_obj_align(top, LV_ALIGN_TOP_RIGHT, 0, 0);
    lv_canvas_set_buffer(top, widget->cbuf, CANVAS_SIZE, CANVAS_SIZE, LV_IMG_CF_TRUE_COLOR);

    // Portrait rows 68-159: the combos card, drawn once
    lv_obj_t *card = lv_img_create(widget->obj);
    lv_img_set_src(card, &left_combos);
    lv_obj_align(card, LV_ALIGN_TOP_LEFT, 0, 0);

    widget->state.peripheral_battery = -1;

    sys_slist_append(&widgets, &widget->node);
    widget_battery_status_init();
    widget_peripheral_battery_init();
    widget_peripheral_charging_init();
    widget_output_status_init();
    widget_layer_status_init();
    widget_mods_init();
    widget_caps_init();

    return 0;
}

lv_obj_t *zmk_widget_status_obj(struct zmk_widget_status *widget) { return widget->obj; }
