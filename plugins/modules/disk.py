#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: disk
short_description: Spin an Unraid disk up or down
description:
    - Manage the spin state of individual disks on an Unraid server.
    - Queries the current disk status and only issues a spin-up or
      spin-down command when the current state differs from the desired state.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    id:
        description:
            - The disk device identifier (e.g. C(disk1), C(cache), C(parity)).
        type: str
        required: true
    state:
        description:
            - Desired spin state of the disk.
            - C(spun_up) ensures the disk is spinning.
            - C(spun_down) puts the disk into standby.
        type: str
        required: true
        choices:
            - spun_up
            - spun_down
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Spin up disk1
  stevefulme1.unraid.disk:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk1
    state: spun_up

- name: Spin down the cache disk
  stevefulme1.unraid.disk:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: cache
    state: spun_down
"""

RETURN = r"""
disk:
    description: Disk information after the operation.
    returned: always
    type: dict
    contains:
        id:
            description: Disk device identifier.
            type: str
            sample: disk1
        status:
            description: Current disk status.
            type: str
            sample: DISK_OK
        spun_down:
            description: Whether the disk is currently spun down.
            type: bool
            sample: false
previous_spun_down:
    description: Whether the disk was spun down before the operation.
    returned: always
    type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_DISK_STATUS = """
query GetDisk($id: String!) {
    disks(id: $id) {
        id
        name
        status
        spindownDelay
        standby
    }
}
"""

MUTATION_SPIN_UP = """
mutation SpinUp($id: String!) {
    disk {
        spinUp(id: $id) {
            id
            status
            standby
        }
    }
}
"""

MUTATION_SPIN_DOWN = """
mutation SpinDown($id: String!) {
    disk {
        spinDown(id: $id) {
            id
            status
            standby
        }
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        id=dict(type="str", required=True),
        state=dict(type="str", required=True, choices=["spun_up", "spun_down"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    disk_id = module.params["id"]
    desired_state = module.params["state"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Query current disk status
    try:
        data = client.query(QUERY_DISK_STATUS, variables={"id": disk_id})
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query disk {disk_id}: {exc}")

    # Handle both list and single-object responses
    disks = data.get("disks", [])
    if isinstance(disks, list):
        if not disks:
            module.fail_json(msg=f"Disk '{disk_id}' not found")
        disk = disks[0]
    else:
        disk = disks

    # Determine current spin state via standby field
    is_spun_down = disk.get("standby", False)

    # Check if already in desired state
    if desired_state == "spun_down" and is_spun_down:
        module.exit_json(
            changed=False,
            disk=dict(id=disk_id, status=disk.get("status"), spun_down=True),
            previous_spun_down=True,
        )
    elif desired_state == "spun_up" and not is_spun_down:
        module.exit_json(
            changed=False,
            disk=dict(id=disk_id, status=disk.get("status"), spun_down=False),
            previous_spun_down=False,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            disk=dict(id=disk_id, status=disk.get("status"), spun_down=(desired_state == "spun_down")),
            previous_spun_down=is_spun_down,
            msg=f"Would {'spin down' if desired_state == 'spun_down' else 'spin up'} disk {disk_id}",
        )

    # Execute spin up/down
    try:
        if desired_state == "spun_up":
            result = client.mutate(MUTATION_SPIN_UP, variables={"id": disk_id})
            new_disk = result.get("disk", {}).get("spinUp", {})
        else:
            result = client.mutate(MUTATION_SPIN_DOWN, variables={"id": disk_id})
            new_disk = result.get("disk", {}).get("spinDown", {})
    except UnraidError as exc:
        module.fail_json(
            msg=f"Failed to {desired_state.replace('_', ' ')} disk {disk_id}: {exc}",
            previous_spun_down=is_spun_down,
        )

    module.exit_json(
        changed=True,
        disk=dict(
            id=new_disk.get("id", disk_id),
            status=new_disk.get("status", ""),
            spun_down=new_disk.get("standby", desired_state == "spun_down"),
        ),
        previous_spun_down=is_spun_down,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
