#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: spin_group
short_description: Spin up or down multiple Unraid disks at once
description:
    - Spin up or spin down a group of disks simultaneously via the
      Unraid GraphQL API.
    - Iterates over the provided disk IDs and issues spin up or spin
      down mutations for each.
    - Useful for power management, maintenance windows, or ensuring
      disks are active before scheduled operations.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    ids:
        description:
            - List of disk identifiers to spin up or down.
        type: list
        elements: str
        required: true
    state:
        description:
            - Desired spin state for the disks.
            - C(spun_up) spins up the disks (makes them active).
            - C(spun_down) spins down the disks (puts them in standby).
        type: str
        required: true
        choices:
            - spun_up
            - spun_down
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - Disks that are already in the desired state are skipped.
    - The module queries current standby state before issuing spin
      mutations to provide accurate changed status.
    - Spinning down a disk that is actively being accessed may fail
      or the disk may immediately spin back up.
"""

EXAMPLES = r"""
- name: Spin up all array disks
  stevefulme1.unraid.spin_group:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    ids:
      - disk1
      - disk2
      - disk3
    state: spun_up

- name: Spin down idle disks for power saving
  stevefulme1.unraid.spin_group:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    ids:
      - disk4
      - disk5
    state: spun_down

- name: Spin up disks before parity check
  stevefulme1.unraid.spin_group:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    ids: "{{ array_disk_ids }}"
    state: spun_up
"""

RETURN = r"""
results:
    description: Per-disk results of the spin operation.
    returned: always
    type: list
    elements: dict
    contains:
        id:
            description: Disk identifier.
            type: str
            sample: disk1
        changed:
            description: Whether the disk state was changed.
            type: bool
            sample: true
        previous_standby:
            description: Whether the disk was in standby before the operation.
            type: bool
            sample: true
        msg:
            description: Per-disk result message.
            type: str
            sample: "disk1 spun up."
        error:
            description: Error message if the operation failed for this disk.
            type: str
            sample: null
changed_count:
    description: Number of disks whose state was changed.
    returned: always
    type: int
    sample: 2
skipped_count:
    description: Number of disks already in the desired state.
    returned: always
    type: int
    sample: 1
failed_count:
    description: Number of disks that failed to change state.
    returned: always
    type: int
    sample: 0
msg:
    description: Summary message.
    returned: always
    type: str
    sample: "Spun up 2 disk(s), 1 already in desired state, 0 failed."
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_DISK_STANDBY = """
{
    disks {
        id
        standby
    }
}
"""

MUTATION_SPIN_UP = """
mutation SpinUp($id: String!) {
    spinUpDisk(id: $id)
}
"""

MUTATION_SPIN_DOWN = """
mutation SpinDown($id: String!) {
    spinDownDisk(id: $id)
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        ids=dict(type="list", elements="str", required=True),
        state=dict(type="str", required=True, choices=["spun_up", "spun_down"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    disk_ids = module.params["ids"]
    desired_state = module.params["state"]

    if not disk_ids:
        module.exit_json(
            changed=False,
            results=[],
            changed_count=0,
            skipped_count=0,
            failed_count=0,
            msg="No disk IDs provided.",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Query current standby state for all disks
    try:
        data = client.query(QUERY_DISK_STANDBY)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query disk standby states: {exc}")

    disk_standby_map = {
        d["id"]: d.get("standby", False)
        for d in data.get("disks", [])
    }

    # Determine desired standby value
    # spun_up means standby=False, spun_down means standby=True
    want_standby = desired_state == "spun_down"
    mutation = MUTATION_SPIN_DOWN if want_standby else MUTATION_SPIN_UP
    action_verb = "spun down" if want_standby else "spun up"

    results = []
    changed_count = 0
    skipped_count = 0
    failed_count = 0

    for disk_id in disk_ids:
        current_standby = disk_standby_map.get(disk_id)

        if current_standby is None:
            results.append({
                "id": disk_id,
                "changed": False,
                "previous_standby": None,
                "msg": f"Disk '{disk_id}' not found.",
                "error": f"Disk '{disk_id}' not found.",
            })
            failed_count += 1
            continue

        # Already in desired state
        if current_standby == want_standby:
            results.append({
                "id": disk_id,
                "changed": False,
                "previous_standby": current_standby,
                "msg": f"{disk_id} is already {action_verb}.",
                "error": None,
            })
            skipped_count += 1
            continue

        if module.check_mode:
            results.append({
                "id": disk_id,
                "changed": True,
                "previous_standby": current_standby,
                "msg": f"Would spin {'down' if want_standby else 'up'} {disk_id}.",
                "error": None,
            })
            changed_count += 1
            continue

        try:
            client.mutate(mutation, variables={"id": disk_id})
            results.append({
                "id": disk_id,
                "changed": True,
                "previous_standby": current_standby,
                "msg": f"{disk_id} {action_verb}.",
                "error": None,
            })
            changed_count += 1
        except UnraidError as exc:
            results.append({
                "id": disk_id,
                "changed": False,
                "previous_standby": current_standby,
                "msg": f"Failed to spin {'down' if want_standby else 'up'} {disk_id}.",
                "error": str(exc),
            })
            failed_count += 1

    overall_changed = changed_count > 0
    state_desc = "up" if desired_state == "spun_up" else "down"
    summary = (
        f"Spun {state_desc} {changed_count} disk(s), "
        f"{skipped_count} already in desired state, "
        f"{failed_count} failed."
    )

    if failed_count > 0 and changed_count == 0 and skipped_count == 0:
        module.fail_json(
            msg=summary,
            results=results,
            changed_count=changed_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

    module.exit_json(
        changed=overall_changed,
        results=results,
        changed_count=changed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        msg=summary,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
