#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: filesystem_check
short_description: Check or repair filesystem on an Unraid disk
description:
    - Run a filesystem check or repair operation on a specified
      Unraid array or cache disk.
    - This module attempts to use the Unraid GraphQL API first.
      If the API does not expose filesystem check mutations, the
      module falls back to executing the appropriate filesystem
      check command over SSH.
    - For XFS filesystems, uses C(xfs_repair). For BTRFS, uses
      C(btrfs check). For ReiserFS, uses C(reiserfsck).
    - The target disk must be unmounted before running a check or
      repair operation.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    id:
        description:
            - Disk identifier to check or repair (e.g., C(disk1), C(cache)).
        type: str
        required: true
    action:
        description:
            - Filesystem action to perform.
            - C(check) performs a read-only filesystem consistency check.
            - C(repair) attempts to repair filesystem inconsistencies.
              Use with caution as repair operations modify the filesystem.
        type: str
        required: true
        choices:
            - check
            - repair
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - The target disk must be unmounted before running filesystem
      operations. Use M(stevefulme1.unraid.array_disk) with
      C(action=unmount) first.
    - The Unraid GraphQL API may not expose filesystem check mutations
      in all versions. The module will fall back to SSH commands
      (C(xfs_repair), C(btrfs check), C(reiserfsck)) when needed.
    - Repair operations can take a significant amount of time on
      large disks. Consider setting a higher C(api_timeout) or running
      the playbook with async.
    - Always back up critical data before running repair operations.
"""

EXAMPLES = r"""
- name: Check filesystem on disk1
  stevefulme1.unraid.filesystem_check:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    id: disk1
    action: check

- name: Repair filesystem on disk2
  stevefulme1.unraid.filesystem_check:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk2
    action: repair

- name: Unmount disk before filesystem check
  block:
    - name: Unmount the disk
      stevefulme1.unraid.array_disk:
        api_url: https://tower.local
        api_key: "{{ unraid_api_key }}"
        id: disk1
        action: unmount

    - name: Run filesystem check
      stevefulme1.unraid.filesystem_check:
        api_url: https://tower.local
        api_key: "{{ unraid_api_key }}"
        id: disk1
        action: check
"""

RETURN = r"""
id:
    description: The disk identifier that was checked.
    returned: always
    type: str
    sample: disk1
action:
    description: The filesystem action that was performed.
    returned: always
    type: str
    sample: check
device:
    description: The device path used.
    returned: when available
    type: str
    sample: sda1
fsType:
    description: The filesystem type detected.
    returned: when available
    type: str
    sample: xfs
method:
    description: Method used for the operation (graphql or ssh_fallback).
    returned: always
    type: str
    sample: ssh_fallback
msg:
    description: Human-readable result message.
    returned: always
    type: str
    sample: "Filesystem check completed on disk1 (/dev/sda1, xfs)."
stdout:
    description: Standard output from the filesystem check command.
    returned: when method is ssh_fallback
    type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_DISK_INFO = """
{
    disks {
        id
        device
        partitions {
            name
            fsType
        }
    }
}
"""

MUTATION_FS_CHECK = """
mutation FilesystemCheck($id: String!, $action: FilesystemAction!) {
    filesystemCheck(id: $id, action: $action)
}
"""

ACTION_MAP = {
    "check": "CHECK",
    "repair": "REPAIR",
}

# Map filesystem types to their check/repair commands
FS_COMMANDS = {
    "xfs": {
        "check": ["xfs_repair", "-n"],
        "repair": ["xfs_repair"],
    },
    "btrfs": {
        "check": ["btrfs", "check", "--readonly"],
        "repair": ["btrfs", "check", "--repair"],
    },
    "reiserfs": {
        "check": ["reiserfsck", "--check"],
        "repair": ["reiserfsck", "--fix-fixable", "-y"],
    },
}


def get_disk_details(client, disk_id):
    """Look up device and filesystem info for a disk ID."""
    data = client.query(QUERY_DISK_INFO)
    for disk in data.get("disks", []):
        if disk.get("id") == disk_id:
            partitions = disk.get("partitions", [])
            if partitions:
                return partitions[0].get("name"), partitions[0].get("fsType")
            return disk.get("device"), None
    return None, None


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        id=dict(type="str", required=True),
        action=dict(type="str", required=True, choices=["check", "repair"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    disk_id = module.params["id"]
    action = module.params["action"]

    if module.check_mode:
        module.exit_json(
            changed=True,
            id=disk_id,
            action=action,
            method="check_mode",
            msg=f"Would perform filesystem {action} on {disk_id}.",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Look up device and filesystem type
    device, fs_type = get_disk_details(client, disk_id)
    if device is None:
        module.fail_json(msg=f"Disk '{disk_id}' not found.")

    # Try GraphQL mutation first
    try:
        client.mutate(
            MUTATION_FS_CHECK,
            variables={
                "id": disk_id,
                "action": ACTION_MAP[action],
            },
        )
        module.exit_json(
            changed=True,
            id=disk_id,
            action=action,
            device=device,
            fsType=fs_type,
            method="graphql",
            msg=f"Filesystem {action} completed on {disk_id} (/dev/{device}, {fs_type}).",
        )
    except UnraidError:
        # GraphQL mutation not available, fall back to SSH
        pass

    # SSH fallback
    if fs_type is None:
        module.fail_json(
            msg=f"Cannot determine filesystem type for disk '{disk_id}'. "
                f"Unable to select the appropriate check tool.",
            id=disk_id,
        )

    fs_type_lower = fs_type.lower()
    if fs_type_lower not in FS_COMMANDS:
        module.fail_json(
            msg=f"Unsupported filesystem type '{fs_type}' on disk '{disk_id}'. "
                f"Supported types: {', '.join(FS_COMMANDS.keys())}.",
            id=disk_id,
            fsType=fs_type,
        )

    cmd_parts = FS_COMMANDS[fs_type_lower][action]
    host = module.params["api_url"].split("//")[-1].split(":")[0].split("/")[0]
    ssh_cmd = ["ssh", f"root@{host}"] + cmd_parts + [f"/dev/{device}"]

    rc, stdout, stderr = module.run_command(ssh_cmd)

    if rc != 0:
        module.fail_json(
            msg=f"Filesystem {action} failed on {disk_id}: {stderr.strip()}",
            id=disk_id,
            action=action,
            device=device,
            fsType=fs_type,
            rc=rc,
            stdout=stdout,
        )

    module.exit_json(
        changed=True if action == "repair" else False,
        id=disk_id,
        action=action,
        device=device,
        fsType=fs_type,
        method="ssh_fallback",
        stdout=stdout.strip(),
        msg=f"Filesystem {action} completed on {disk_id} (/dev/{device}, {fs_type}).",
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
