#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for configuring Unraid UPS settings."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ups
short_description: Configure UPS settings on Unraid
version_added: "1.0.0"
description:
  - Query and configure UPS (Uninterruptible Power Supply) settings on an
    Unraid server via the GraphQL API.
  - Compares the current configuration against the desired state and only
    applies changes when necessary.
options:
  mode:
    description:
      - The UPS operation mode (e.g., C(standalone), C(net-client), C(net-server)).
    type: str
    required: false
  cable:
    description:
      - The UPS cable type.
    type: str
    required: false
  device:
    description:
      - The UPS device path or network address.
    type: str
    required: false
  battery_level:
    description:
      - The battery level percentage at which to initiate shutdown.
      - Valid range is 1-100.
    type: int
    required: false
  shutdown_timeout:
    description:
      - The number of seconds to wait on battery before initiating shutdown.
      - Set to C(-1) to disable timeout-based shutdown.
    type: int
    required: false
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Configure UPS in standalone mode
  stevefulme1.unraid.ups:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    mode: standalone
    cable: USB
    device: /dev/usb/hiddev0
    battery_level: 20
    shutdown_timeout: 300

- name: Set UPS battery shutdown threshold
  stevefulme1.unraid.ups:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    battery_level: 10

- name: Configure UPS as network client
  stevefulme1.unraid.ups:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    mode: net-client
    device: "192.168.1.100"
"""

RETURN = r"""
ups_config:
  description: The UPS configuration after applying changes.
  returned: success
  type: dict
  contains:
    service:
      description: The UPS service mode.
      type: str
    cable:
      description: The cable type.
      type: str
    type:
      description: The UPS driver type.
      type: str
    device:
      description: The device path or address.
      type: str
  sample:
    service: "standalone"
    cable: "USB"
    type: "usb"
    device: "/dev/usb/hiddev0"
diff:
  description: The configuration differences that were applied.
  returned: changed
  type: dict
  contains:
    before:
      description: Previous configuration values for changed fields.
      type: dict
    after:
      description: New configuration values for changed fields.
      type: dict
"""

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)
from ansible.module_utils.basic import AnsibleModule


QUERY_UPS_CONFIG = """
{
  upsConfiguration {
    service
    cable
    type
    device
  }
}
"""

CONFIGURE_UPS = """
mutation($config: UpsConfigInput!) {
  configureUps(config: $config)
}
"""

# Maps module params to GraphQL config field names
PARAM_TO_CONFIG = {
    "mode": "service",
    "cable": "cable",
    "device": "device",
    "battery_level": "batteryLevel",
    "shutdown_timeout": "shutdownTimeout",
}

# Maps module params to query response field names for comparison
PARAM_TO_QUERY = {
    "mode": "service",
    "cable": "cable",
    "device": "device",
}


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        mode=dict(type="str", required=False),
        cable=dict(type="str", required=False),
        device=dict(type="str", required=False),
        battery_level=dict(type="int", required=False),
        shutdown_timeout=dict(type="int", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    # Validate that at least one UPS setting is provided
    ups_params = {
        k: module.params[k]
        for k in PARAM_TO_CONFIG
        if module.params.get(k) is not None
    }

    if not ups_params:
        module.fail_json(
            msg="At least one UPS configuration parameter must be provided "
            "(mode, cable, device, battery_level, shutdown_timeout)."
        )

    try:
        client = get_client(module)
        result = client.query(QUERY_UPS_CONFIG)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query UPS configuration: {exc}")

    current_config = result.get("upsConfiguration", {})

    # Determine what needs to change
    config_update = {}
    diff_before = {}
    diff_after = {}

    for param_name, param_value in ups_params.items():
        config_key = PARAM_TO_CONFIG[param_name]
        query_key = PARAM_TO_QUERY.get(param_name)

        # Compare with current value if available in the query response
        if query_key and query_key in current_config:
            current_value = current_config[query_key]
            if str(current_value) == str(param_value):
                continue

            diff_before[param_name] = current_value
            diff_after[param_name] = param_value

        config_update[config_key] = param_value

    if not config_update:
        module.exit_json(changed=False, ups_config=current_config)

    if module.check_mode:
        module.exit_json(
            changed=True,
            ups_config=current_config,
            diff={"before": diff_before, "after": diff_after},
        )

    try:
        client.mutate(CONFIGURE_UPS, {"config": config_update})
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to configure UPS: {exc}")

    # Re-fetch to return updated state
    try:
        result = client.query(QUERY_UPS_CONFIG)
        updated_config = result.get("upsConfiguration", {})
    except UnraidError:
        updated_config = current_config

    module.exit_json(
        changed=True,
        ups_config=updated_config,
        diff={"before": diff_before, "after": diff_after},
    )


if __name__ == "__main__":
    main()
