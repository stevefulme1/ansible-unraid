#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: array_disk
short_description: Add, remove, mount, or unmount disks in the Unraid array
description:
    - Manage individual disk membership and mount state in the Unraid
      disk array via the GraphQL API.
    - Supports adding a disk to a specific array slot, removing a disk,
      mounting a disk, or unmounting a disk.
    - The array must be in the appropriate state for each operation
      (e.g., stopped for add/remove, started for mount/unmount).
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    id:
        description:
            - Disk identifier to operate on (e.g., C(disk1), C(disk2)).
        type: str
        required: true
    action:
        description:
            - Action to perform on the disk.
            - C(add) adds the disk to the array at the specified slot.
            - C(remove) removes the disk from the array.
            - C(mount) mounts an array disk.
            - C(unmount) unmounts an array disk.
        type: str
        required: true
        choices:
            - add
            - remove
            - mount
            - unmount
    slot:
        description:
            - Array slot number to assign the disk to.
            - Required when I(action=add), ignored otherwise.
        type: int
        required: false
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - The C(add) and C(remove) actions typically require the array to be
      stopped. The C(mount) and C(unmount) actions require the array to
      be started.
"""

EXAMPLES = r"""
- name: Add a disk to array slot 3
  stevefulme1.unraid.array_disk:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    id: disk3
    action: add
    slot: 3

- name: Remove a disk from the array
  stevefulme1.unraid.array_disk:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk3
    action: remove

- name: Mount a disk in the running array
  stevefulme1.unraid.array_disk:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk1
    action: mount

- name: Unmount a disk
  stevefulme1.unraid.array_disk:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk1
    action: unmount
"""

RETURN = r"""
id:
    description: The disk identifier that was operated on.
    returned: always
    type: str
    sample: disk3
action:
    description: The action that was performed.
    returned: always
    type: str
    sample: add
result:
    description: The raw result from the GraphQL mutation.
    returned: on success
    type: dict
msg:
    description: Human-readable result message.
    returned: always
    type: str
    sample: "Successfully added disk 'disk3' to slot 3."
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_ADD_DISK = """
mutation AddDisk($id: String!, $slot: Int!) {
    array {
        addDiskToArray(id: $id, slot: $slot)
    }
}
"""

MUTATION_REMOVE_DISK = """
mutation RemoveDisk($id: String!) {
    array {
        removeDiskFromArray(id: $id)
    }
}
"""

MUTATION_MOUNT_DISK = """
mutation MountDisk($id: String!) {
    array {
        mountArrayDisk(id: $id)
    }
}
"""

MUTATION_UNMOUNT_DISK = """
mutation UnmountDisk($id: String!) {
    array {
        unmountArrayDisk(id: $id)
    }
}
"""

ACTION_CONFIG = {
    "add": {
        "mutation": MUTATION_ADD_DISK,
        "needs_slot": True,
        "msg": "added disk '{id}' to slot {slot}",
        "result_path": ["array", "addDiskToArray"],
    },
    "remove": {
        "mutation": MUTATION_REMOVE_DISK,
        "needs_slot": False,
        "msg": "removed disk '{id}' from the array",
        "result_path": ["array", "removeDiskFromArray"],
    },
    "mount": {
        "mutation": MUTATION_MOUNT_DISK,
        "needs_slot": False,
        "msg": "mounted disk '{id}'",
        "result_path": ["array", "mountArrayDisk"],
    },
    "unmount": {
        "mutation": MUTATION_UNMOUNT_DISK,
        "needs_slot": False,
        "msg": "unmounted disk '{id}'",
        "result_path": ["array", "unmountArrayDisk"],
    },
}


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        id=dict(type="str", required=True),
        action=dict(
            type="str",
            required=True,
            choices=["add", "remove", "mount", "unmount"],
        ),
        slot=dict(type="int", required=False, default=None),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("action", "add", ["slot"]),
        ],
    )

    disk_id = module.params["id"]
    action = module.params["action"]
    slot = module.params["slot"]
    config = ACTION_CONFIG[action]

    # Check mode
    if module.check_mode:
        msg = "Would have " + config["msg"].format(id=disk_id, slot=slot)
        module.exit_json(changed=True, id=disk_id, action=action, msg=msg)

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    variables = {"id": disk_id}
    if config["needs_slot"]:
        variables["slot"] = slot

    try:
        data = client.mutate(config["mutation"], variables=variables)
    except UnraidError as exc:
        module.fail_json(
            msg=f"Failed to {action} disk '{disk_id}': {exc}",
            id=disk_id,
            action=action,
        )

    # Extract result from nested path
    result = data
    for key in config["result_path"]:
        result = result.get(key, {}) if isinstance(result, dict) else result

    msg = "Successfully " + config["msg"].format(id=disk_id, slot=slot)
    module.exit_json(
        changed=True,
        id=disk_id,
        action=action,
        result=result,
        msg=msg,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
