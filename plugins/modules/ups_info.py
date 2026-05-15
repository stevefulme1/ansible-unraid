#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ups_info
short_description: Query UPS device status on Unraid
description:
    - Retrieves UPS (Uninterruptible Power Supply) device status from an
      Unraid server via the GraphQL API.
    - Returns battery charge, runtime, load, input voltage, and overall
      status for all connected UPS devices.
    - This is a read-only module that never makes changes.
    - Separate from M(stevefulme1.unraid.ups) which configures UPS settings.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Get UPS status
  stevefulme1.unraid.ups_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: ups

- name: Display UPS battery charge
  ansible.builtin.debug:
    msg: "Battery: {{ item.battery_charge }}%"
  loop: "{{ ups.ups_devices }}"

- name: Alert if UPS battery below threshold
  ansible.builtin.fail:
    msg: "UPS battery critically low: {{ item.battery_charge }}%"
  loop: "{{ ups.ups_devices }}"
  when: item.battery_charge | int < 20
"""

RETURN = r"""
ups_devices:
    description: List of UPS devices with status information.
    returned: success
    type: list
    elements: dict
    contains:
        status:
            description:
                - UPS status string (e.g., C(OL) for online/on-line,
                  C(OB) for on battery, C(LB) for low battery).
            type: str
        battery_charge:
            description: Battery charge percentage (0-100).
            type: float
        runtime:
            description: Estimated runtime remaining in seconds.
            type: float
        load:
            description: Current UPS load percentage.
            type: float
        input_voltage:
            description: Input voltage in volts.
            type: float
    sample:
        - status: OL
          battery_charge: 100.0
          runtime: 3600.0
          load: 25.0
          input_voltage: 120.0
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY = """
{
    upsDevices {
        status
        batteryCharge
        runtime
        load
        inputVoltage
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    try:
        client = get_client(module)
        data = client.query(QUERY)
        raw = data.get("upsDevices", [])
        devices = []
        for dev in raw:
            devices.append(
                dict(
                    status=dev.get("status"),
                    battery_charge=dev.get("batteryCharge"),
                    runtime=dev.get("runtime"),
                    load=dev.get("load"),
                    input_voltage=dev.get("inputVoltage"),
                )
            )
        module.exit_json(changed=False, ups_devices=devices)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
