#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: bond
short_description: Configure network bonds on Unraid
description:
    - Create, update, or remove network bond interfaces on an Unraid server.
    - Bond configuration is persisted to C(/boot/config/network.cfg) via
      the GraphQL API so settings survive reboots.
    - Supports all standard Linux bonding modes.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    name:
        description:
            - Name of the bond interface (e.g., C(bond0), C(bond1)).
        type: str
        required: true
    mode:
        description:
            - Bonding mode that determines how traffic is distributed
              across member interfaces.
        type: str
        choices:
            - balance-rr
            - active-backup
            - balance-xor
            - broadcast
            - 802.3ad
            - balance-tlb
            - balance-alb
    members:
        description:
            - List of physical interfaces to include in the bond
              (e.g., C([eth0, eth1])).
        type: list
        elements: str
    state:
        description:
            - Whether the bond should exist or be removed.
        type: str
        choices:
            - present
            - absent
        default: present
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Create a bond with two interfaces using active-backup
  stevefulme1.unraid.bond:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: bond0
    mode: active-backup
    members:
      - eth0
      - eth1
    state: present

- name: Create a bond using LACP (802.3ad)
  stevefulme1.unraid.bond:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: bond0
    mode: 802.3ad
    members:
      - eth0
      - eth1
      - eth2

- name: Remove a bond interface
  stevefulme1.unraid.bond:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: bond0
    state: absent
"""

RETURN = r"""
bond:
    description: The bond configuration after changes.
    returned: success
    type: dict
    contains:
        name:
            description: Bond interface name.
            type: str
        mode:
            description: Bonding mode.
            type: str
        members:
            description: Member interfaces.
            type: list
            elements: str
    sample:
        name: bond0
        mode: active-backup
        members:
            - eth0
            - eth1
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

QUERY_BONDS = """
{
    network {
        interfaces {
            name
            type
            bondMode
            bondMembers
        }
    }
}
"""

MUTATION_CREATE_BOND = """
mutation($input: BondInput!) {
    createBond(input: $input)
}
"""

MUTATION_DELETE_BOND = """
mutation($name: String!) {
    deleteBond(name: $name)
}
"""


def find_bond(interfaces, name):
    """Find an existing bond by name."""
    for iface in interfaces:
        if iface.get("name") == name and iface.get("type") == "bond":
            return iface
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        mode=dict(
            type="str",
            choices=[
                "balance-rr",
                "active-backup",
                "balance-xor",
                "broadcast",
                "802.3ad",
                "balance-tlb",
                "balance-alb",
            ],
        ),
        members=dict(type="list", elements="str"),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["mode", "members"]),
        ],
    )

    name = module.params["name"]
    mode = module.params["mode"]
    members = module.params["members"]
    state = module.params["state"]

    try:
        client = get_client(module)
        data = client.query(QUERY_BONDS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query network interfaces: {exc}")

    interfaces = data.get("network", {}).get("interfaces", [])
    existing = find_bond(interfaces, name)

    if state == "absent":
        if not existing:
            module.exit_json(changed=False, bond={})
            return

        if module.check_mode:
            module.exit_json(
                changed=True,
                bond={},
                diff={"before": {"name": name}, "after": {}},
            )
            return

        try:
            client.mutate(MUTATION_DELETE_BOND, variables={"name": name})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to delete bond {name}: {exc}")

        module.exit_json(
            changed=True,
            bond={},
            diff={"before": {"name": name}, "after": {}},
        )
        return

    # state == present
    desired = dict(name=name, mode=mode, members=sorted(members))

    if existing:
        current = dict(
            name=existing.get("name"),
            mode=existing.get("bondMode"),
            members=sorted(existing.get("bondMembers", [])),
        )
        if current == desired:
            module.exit_json(changed=False, bond=current)
            return
        diff = {"before": current, "after": desired}
    else:
        diff = {"before": {}, "after": desired}

    if module.check_mode:
        module.exit_json(changed=True, bond=desired, diff=diff)
        return

    try:
        client.mutate(
            MUTATION_CREATE_BOND,
            variables={
                "input": {
                    "name": name,
                    "mode": mode,
                    "members": members,
                }
            },
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to configure bond {name}: {exc}")

    module.exit_json(changed=True, bond=desired, diff=diff)


if __name__ == "__main__":
    main()
