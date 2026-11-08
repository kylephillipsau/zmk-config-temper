/*
 *
 * SPDX-License-Identifier: MIT
 *
 */

#include <string.h>
#include <zephyr/kernel.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/event_manager.h>

#include "peripheral_charging.h"

ZMK_EVENT_IMPL(zmk_peripheral_charging_changed);

#if IS_ENABLED(CONFIG_ZMK_SPLIT) && IS_ENABLED(CONFIG_ZMK_SPLIT_RELAY_EVENT)

#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL)

// Central: re-raise the relayed event locally for the display widget.
ZMK_RELAY_EVENT_HANDLE(zmk_peripheral_charging_changed, chg, );

#elif IS_ENABLED(CONFIG_USB_DEVICE_STACK)

#include <zmk/usb.h>
#include <zmk/events/usb_conn_state_changed.h>
#include <zmk/events/split_peripheral_status_changed.h>

static void send_charging(struct k_work *work) {
    raise_zmk_peripheral_charging_changed(
        (struct zmk_peripheral_charging_changed){.charging = zmk_usb_is_powered()});
}

static K_WORK_DELAYABLE_DEFINE(send_charging_work, send_charging);

static int charging_listener(const zmk_event_t *eh) {
    const struct zmk_split_peripheral_status_changed *link =
        as_zmk_split_peripheral_status_changed(eh);

    if (link == NULL) {
        // USB plugged in or out
        k_work_reschedule(&send_charging_work, K_NO_WAIT);
    } else if (link->connected) {
        // Send it again whenever the link comes up, as anything sent while it was down is lost.
        // The left half only subscribes a moment after connecting, so wait for that.
        k_work_reschedule(&send_charging_work, K_SECONDS(5));
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(peripheral_charging, charging_listener);
ZMK_SUBSCRIPTION(peripheral_charging, zmk_usb_conn_state_changed);
ZMK_SUBSCRIPTION(peripheral_charging, zmk_split_peripheral_status_changed);

ZMK_RELAY_EVENT_PERIPHERAL_TO_CENTRAL(zmk_peripheral_charging_changed, chg, );

#endif

#endif
