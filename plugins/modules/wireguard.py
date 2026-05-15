#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: wireguard
short_description: Manage WireGuard tunnels on Unraid
description:
    - Activate, deactivate, or remove WireGuard VPN tunnels on an Unraid
      server via the GraphQL API.
    - WireGuard is managed through the Unraid WireGuard plugin
      (C(dynamix.wireguard)) which must be installed on the server.
    - Tunnel configuration files are stored in
      C(/boot/config/wireguard/) on the USB flash drive.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    name:
        description:
            - Name of the WireGuard tunnel (e.g., C(wg0), C(remote-access)).
        type: str
        required: true
    state:
        description:
            - Desired state of the tunnel.
            - C(active) starts the tunnel if not already running.
            - C(inactive) stops the tunnel if running.
            - C(absent) removes the tunnel configuration entirely.
        type: str
        choices:
            - active
            - inactive
            - absent
        default: active
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Activate WireGuard tunnel wg0
  stevefulme1.unraid.wireguard:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: wg0
    state: active

- name: Stop WireGuard tunnel
  stevefulme1.unraid.wireguard:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: wg0
    state: inactive

- name: Remove WireGuard tunnel
  stevefulme1.unraid.wireguard:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: wg0
    state: absent
"""

RETURN = r"""
tunnel:
    description: The WireGuard tunnel state after changes.
    returned: success
    type: dict
    contains:
        name:
            description: Tunnel name.
            type: str
        state:
            description: Current tunnel state.
            type: str
    sample:
        name: wg0
        state: active
diff:
    description: State differences that were applied.
    returned: changed
    type: dict
    contains:
        before:
            description: Previous state.
            type: dict
        after:
            description: New state.
            type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_TUNNELS = """
{
    wireguard {
        tunnels {
            name
            state
        }
    }
}
"""

MUTATION_SET_TUNNEL_STATE = """
mutation($name: String!, $state: WireguardTunnelState!) {
    setWireguardTunnelState(name: $name, state: $state)
}
"""

MUTATION_DELETE_TUNNEL = """
mutation($name: String!) {
    deleteWireguardTunnel(name: $name)
}
"""


def find_tunnel(tunnels, name):
    """Find an existing tunnel by name."""
    for t in tunnels:
        if t.get("name") == name:
            return t
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(
            type="str",
            choices=["active", "inactive", "absent"],
            default="active",
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]

    try:
        client = get_client(module)
        data = client.query(QUERY_TUNNELS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query WireGuard tunnels: {exc}")

    tunnels = data.get("wireguard", {}).get("tunnels", [])
    existing = find_tunnel(tunnels, name)

    if state == "absent":
        if not existing:
            module.exit_json(changed=False, tunnel={})
            return

        if module.check_mode:
            module.exit_json(
                changed=True,
                tunnel={},
                diff={"before": {"name": name, "state": existing.get("state")}, "after": {}},
            )
            return

        try:
            client.mutate(MUTATION_DELETE_TUNNEL, variables={"name": name})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to delete tunnel {name}: {exc}")

        module.exit_json(
            changed=True,
            tunnel={},
            diff={"before": {"name": name}, "after": {}},
        )
        return

    # state is active or inactive
    current_state = existing.get("state") if existing else None
    desired_result = dict(name=name, state=state)

    if existing and current_state == state:
        module.exit_json(changed=False, tunnel=desired_result)
        return

    if not existing:
        module.fail_json(
            msg=f"WireGuard tunnel '{name}' does not exist. "
            "Create the tunnel configuration through the Unraid WireGuard "
            "plugin before managing its state with this module."
        )

    diff = {
        "before": {"name": name, "state": current_state},
        "after": desired_result,
    }

    if module.check_mode:
        module.exit_json(changed=True, tunnel=desired_result, diff=diff)
        return

    try:
        client.mutate(
            MUTATION_SET_TUNNEL_STATE,
            variables={"name": name, "state": state},
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to set tunnel {name} to {state}: {exc}")

    module.exit_json(changed=True, tunnel=desired_result, diff=diff)


if __name__ == "__main__":
    main()
