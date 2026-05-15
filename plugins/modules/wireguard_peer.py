#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: wireguard_peer
short_description: Manage WireGuard peers on Unraid
description:
    - Add, update, or remove peers from WireGuard tunnels on an Unraid
      server via the GraphQL API.
    - WireGuard peers are managed through the Unraid WireGuard plugin
      (C(dynamix.wireguard)) which must be installed on the server.
    - Peer configurations are stored as part of the tunnel config in
      C(/boot/config/wireguard/) on the USB flash drive.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    tunnel:
        description:
            - Name of the WireGuard tunnel this peer belongs to
              (e.g., C(wg0)).
        type: str
        required: true
    name:
        description:
            - Friendly name for the peer (e.g., C(laptop), C(phone)).
        type: str
        required: true
    state:
        description:
            - Whether the peer should exist or be removed.
        type: str
        choices:
            - present
            - absent
        default: present
    allowed_ips:
        description:
            - List of allowed IP ranges for the peer in CIDR notation
              (e.g., C(10.0.0.2/32), C(192.168.1.0/24)).
            - Determines which traffic is routed through the tunnel
              for this peer.
        type: list
        elements: str
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Add a peer to wg0
  stevefulme1.unraid.wireguard_peer:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    tunnel: wg0
    name: laptop
    allowed_ips:
      - 10.0.0.2/32
    state: present

- name: Add a peer with full tunnel routing
  stevefulme1.unraid.wireguard_peer:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    tunnel: wg0
    name: phone
    allowed_ips:
      - 0.0.0.0/0
      - "::/0"

- name: Remove a peer from wg0
  stevefulme1.unraid.wireguard_peer:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    tunnel: wg0
    name: laptop
    state: absent
"""

RETURN = r"""
peer:
    description: The peer configuration after changes.
    returned: success
    type: dict
    contains:
        name:
            description: Peer name.
            type: str
        tunnel:
            description: Parent tunnel name.
            type: str
        allowed_ips:
            description: Allowed IP ranges for the peer.
            type: list
            elements: str
    sample:
        name: laptop
        tunnel: wg0
        allowed_ips:
            - "10.0.0.2/32"
diff:
    description: Configuration differences that were applied.
    returned: changed
    type: dict
    contains:
        before:
            description: Previous configuration values.
            type: dict
        after:
            description: New configuration values.
            type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_PEERS = """
query($tunnel: String!) {
    wireguard {
        tunnel(name: $tunnel) {
            name
            peers {
                name
                allowedIps
            }
        }
    }
}
"""

MUTATION_ADD_PEER = """
mutation($input: WireguardPeerInput!) {
    addWireguardPeer(input: $input)
}
"""

MUTATION_UPDATE_PEER = """
mutation($input: WireguardPeerInput!) {
    updateWireguardPeer(input: $input)
}
"""

MUTATION_DELETE_PEER = """
mutation($tunnel: String!, $name: String!) {
    deleteWireguardPeer(tunnel: $tunnel, name: $name)
}
"""


def find_peer(peers, name):
    """Find an existing peer by name."""
    for p in peers:
        if p.get("name") == name:
            return p
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        tunnel=dict(type="str", required=True),
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        allowed_ips=dict(type="list", elements="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["allowed_ips"]),
        ],
    )

    tunnel = module.params["tunnel"]
    name = module.params["name"]
    state = module.params["state"]
    allowed_ips = module.params.get("allowed_ips") or []

    try:
        client = get_client(module)
        data = client.query(QUERY_PEERS, variables={"tunnel": tunnel})
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query WireGuard tunnel '{tunnel}': {exc}")

    tunnel_data = data.get("wireguard", {}).get("tunnel")
    if not tunnel_data:
        module.fail_json(
            msg=f"WireGuard tunnel '{tunnel}' does not exist. "
            "Create the tunnel through the Unraid WireGuard plugin first."
        )

    peers = tunnel_data.get("peers", [])
    existing = find_peer(peers, name)

    if state == "absent":
        if not existing:
            module.exit_json(changed=False, peer={})
            return

        diff = {
            "before": {"name": name, "tunnel": tunnel},
            "after": {},
        }

        if module.check_mode:
            module.exit_json(changed=True, peer={}, diff=diff)
            return

        try:
            client.mutate(
                MUTATION_DELETE_PEER,
                variables={"tunnel": tunnel, "name": name},
            )
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to delete peer {name}: {exc}")

        module.exit_json(changed=True, peer={}, diff=diff)
        return

    # state == present
    desired = dict(name=name, tunnel=tunnel, allowed_ips=sorted(allowed_ips))

    if existing:
        current = dict(
            name=existing.get("name"),
            tunnel=tunnel,
            allowed_ips=sorted(existing.get("allowedIps", [])),
        )
        if current == desired:
            module.exit_json(changed=False, peer=current)
            return
        diff = {"before": current, "after": desired}
        mutation = MUTATION_UPDATE_PEER
    else:
        diff = {"before": {}, "after": desired}
        mutation = MUTATION_ADD_PEER

    if module.check_mode:
        module.exit_json(changed=True, peer=desired, diff=diff)
        return

    try:
        client.mutate(
            mutation,
            variables={
                "input": {
                    "tunnel": tunnel,
                    "name": name,
                    "allowedIps": allowed_ips,
                }
            },
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to configure peer {name}: {exc}")

    module.exit_json(changed=True, peer=desired, diff=diff)


if __name__ == "__main__":
    main()
