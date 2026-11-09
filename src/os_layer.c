/*
 * Windows or macOS by Bluetooth slot: the WIN layer in config/temper.keymap is on while a Windows
 * device's slot is selected, and off for the Macs.
 *
 * Slot 1 (index 0) is the MacBook, slot 2 (index 1) the phone, and slot 3 (index 2) the work
 * computer, which runs Windows. Slots 4 and 5 are free and use macOS keys until listed here.
 *
 * It follows the selected slot, not the connection, so over USB the keys match whichever slot is
 * selected.
 *
 * SPDX-License-Identifier: MIT
 */

#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/util.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/ble.h>
#include <zmk/event_manager.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/keymap.h>

// Bluetooth slot indexes (BT_SEL n) that get Windows keys
#define WINDOWS_SLOTS BIT(2)

static zmk_keymap_layer_id_t win_layer(void) {
    for (zmk_keymap_layer_id_t id = 0; id < ZMK_KEYMAP_LAYERS_LEN; id++) {
        const char *name = zmk_keymap_layer_name(id);
        if (name != NULL && strcmp(name, "WIN") == 0) {
            return id;
        }
    }
    return ZMK_KEYMAP_LAYER_ID_INVAL;
}

static void apply_os_layer(int profile) {
    zmk_keymap_layer_id_t layer = win_layer();
    if (layer == ZMK_KEYMAP_LAYER_ID_INVAL) {
        LOG_WRN("No WIN layer in the keymap");
        return;
    }

    bool windows = profile >= 0 && profile < 32 && (WINDOWS_SLOTS & BIT(profile));
    if (windows == zmk_keymap_layer_active(layer)) {
        return;
    }
    LOG_INF("Slot %d: %s keys", profile + 1, windows ? "Windows" : "macOS");
    if (windows) {
        zmk_keymap_layer_activate(layer);
    } else {
        zmk_keymap_layer_deactivate(layer);
    }
}

static int os_layer_listener(const zmk_event_t *eh) {
    const struct zmk_ble_active_profile_changed *ev = as_zmk_ble_active_profile_changed(eh);
    if (ev != NULL) {
        apply_os_layer(ev->index);
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(os_layer, os_layer_listener);
ZMK_SUBSCRIPTION(os_layer, zmk_ble_active_profile_changed);

// At startup the selected slot comes from settings, and ZMK doesn't always announce it, so check
// once they've loaded.
static void os_layer_startup(struct k_work *work) { apply_os_layer(zmk_ble_active_profile_index()); }

static K_WORK_DELAYABLE_DEFINE(os_layer_startup_work, os_layer_startup);

static int os_layer_settings_commit(void) {
    k_work_schedule(&os_layer_startup_work, K_MSEC(100));
    return 0;
}

SETTINGS_STATIC_HANDLER_DEFINE(kyles_os_layer, "kyles_os_layer", NULL, NULL,
                               os_layer_settings_commit, NULL);
