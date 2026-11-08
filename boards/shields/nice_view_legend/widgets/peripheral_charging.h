/*
 *
 * SPDX-License-Identifier: MIT
 *
 */

#pragma once

#include <zephyr/kernel.h>
#include <zmk/event_manager.h>

/*
 * Whether the right half is on USB power, relayed to the left half so its screen can say so. The
 * left half otherwise only gets the right half's battery level, which reads as full while it
 * charges. One byte, to fit the split relay payload (CONFIG_ZMK_SPLIT_RELAY_EVENT_DATA_LEN).
 */
struct zmk_peripheral_charging_changed {
    uint8_t charging;
};

ZMK_EVENT_DECLARE(zmk_peripheral_charging_changed);
