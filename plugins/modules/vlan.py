#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: vlan
short_description: Manage VLANs on Unraid
description:
    - Create or remove VLAN interfaces on an Unraid server via the
      GraphQL API.
    - VLAN configuration is persisted to C(/boot/config/network.cfg) so
      settings survive reboots.
    - Each VLAN is attached to a parent interface (e.g., C(eth0), C(bond0),
      C(br0)) and identified by a numeric VLAN ID.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    id:
        description:
            - VLAN ID (1-4094).
        type: int
        required: true
    parent:
        description:
            - Parent interface to attach the VLAN to (e.g., C(eth0), C(bond0),
              C(br0)).
        type: str
        required: true
    state:
        description:
            - Whether the VLAN should exist or be removed.
        type: str
        choices:
            - present
            - absent
        default: present
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Create VLAN 100 on eth0
  stevefulme1.unraid.vlan:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: 100
    parent: eth0
    state: present

- name: Create VLAN for IoT devices on bond0
  stevefulme1.unraid.vlan:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: 200
    parent: bond0

- name: Remove VLAN 100
  stevefulme1.unraid.vlan:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: 100
    parent: eth0
    state: absent
"""

RETURN = r"""
vlan:
    description: The VLAN configuration after changes.
    returned: success
    type: dict
    contains:
        id:
            description: VLAN ID.
            type: int
        parent:
            description: Parent interface name.
            type: str
        name:
            description: Resulting interface name (e.g., C(eth0.100)).
            type: str
    sample:
        id: 100
        parent: eth0
        name: eth0.100
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

QUERY_VLANS = """
{
    network {
        interfaces {
            name
            type
            vlanId
            vlanParent
        }
    }
}
"""

MUTATION_CREATE_VLAN = """
mutation($input: VlanInput!) {
    createVlan(input: $input)
}
"""

MUTATION_DELETE_VLAN = """
mutation($name: String!) {
    deleteVlan(name: $name)
}
"""


def find_vlan(interfaces, vlan_id, parent):
    """Find an existing VLAN by ID and parent."""
    vlan_name = f"{parent}.{vlan_id}"
    for iface in interfaces:
        if iface.get("type") == "vlan" and iface.get("name") == vlan_name:
            return iface
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        id=dict(type="int", required=True),
        parent=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    vlan_id = module.params["id"]
    parent = module.params["parent"]
    state = module.params["state"]
    vlan_name = f"{parent}.{vlan_id}"

    if vlan_id < 1 or vlan_id > 4094:
        module.fail_json(msg="VLAN ID must be between 1 and 4094")

    try:
        client = get_client(module)
        data = client.query(QUERY_VLANS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query network interfaces: {exc}")

    interfaces = data.get("network", {}).get("interfaces", [])
    existing = find_vlan(interfaces, vlan_id, parent)

    if state == "absent":
        if not existing:
            module.exit_json(changed=False, vlan={})
            return

        if module.check_mode:
            module.exit_json(
                changed=True,
                vlan={},
                diff={"before": {"name": vlan_name}, "after": {}},
            )
            return

        try:
            client.mutate(MUTATION_DELETE_VLAN, variables={"name": vlan_name})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to delete VLAN {vlan_name}: {exc}")

        module.exit_json(
            changed=True,
            vlan={},
            diff={"before": {"name": vlan_name}, "after": {}},
        )
        return

    # state == present
    desired = dict(id=vlan_id, parent=parent, name=vlan_name)

    if existing:
        module.exit_json(changed=False, vlan=desired)
        return

    if module.check_mode:
        module.exit_json(
            changed=True,
            vlan=desired,
            diff={"before": {}, "after": desired},
        )
        return

    try:
        client.mutate(
            MUTATION_CREATE_VLAN,
            variables={
                "input": {
                    "vlanId": vlan_id,
                    "parent": parent,
                }
            },
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to create VLAN {vlan_name}: {exc}")

    module.exit_json(
        changed=True,
        vlan=desired,
        diff={"before": {}, "after": desired},
    )


if __name__ == "__main__":
    main()
