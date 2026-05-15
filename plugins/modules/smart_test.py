#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: smart_test
short_description: Run SMART self-tests on Unraid disks
description:
    - Initiate a SMART self-test on a specified disk via the Unraid
      GraphQL API.
    - Supports short, long (extended), and conveyance test types.
    - The test runs asynchronously on the disk. Use M(stevefulme1.unraid.disk_info)
      to check SMART results after the test completes.
    - If the GraphQL API does not expose a SMART test mutation, the
      module will fall back to executing C(smartctl -t) over SSH. Ensure
      the Unraid server is accessible via SSH and the user has root access.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    id:
        description:
            - Disk identifier to run the SMART test on (e.g., C(disk1)).
        type: str
        required: true
    test_type:
        description:
            - Type of SMART self-test to run.
            - C(short) runs a quick test (typically 1-2 minutes).
            - C(long) runs an extended test (can take hours depending
              on disk size).
            - C(conveyance) runs a conveyance test (typically 5 minutes).
        type: str
        required: true
        choices:
            - short
            - long
            - conveyance
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - The Unraid GraphQL API may not expose a SMART test mutation in all
      versions. If the mutation is unavailable, the module will attempt
      to run C(smartctl -t <type> /dev/<device>) via SSH as a fallback.
    - SMART tests run in the background on the disk controller. This
      module returns immediately after initiating the test.
    - Long tests can take several hours on large disks. Monitor progress
      with C(smartctl -a /dev/<device>) or the Unraid web UI.
"""

EXAMPLES = r"""
- name: Run a short SMART test on disk1
  stevefulme1.unraid.smart_test:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    id: disk1
    test_type: short

- name: Run a long SMART test on disk2
  stevefulme1.unraid.smart_test:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk2
    test_type: long

- name: Run conveyance test on all array disks
  stevefulme1.unraid.smart_test:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: "{{ item }}"
    test_type: conveyance
  loop: "{{ array_disk_ids }}"
"""

RETURN = r"""
id:
    description: The disk identifier that the test was initiated on.
    returned: always
    type: str
    sample: disk1
test_type:
    description: The type of SMART test that was initiated.
    returned: always
    type: str
    sample: short
device:
    description: The device path used for the test.
    returned: when available
    type: str
    sample: sda
msg:
    description: Human-readable result message.
    returned: always
    type: str
    sample: "SMART short test initiated on disk1 (/dev/sda)."
method:
    description: Method used to initiate the test (graphql or ssh_fallback).
    returned: always
    type: str
    sample: graphql
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_SMART_TEST = """
mutation SmartTest($id: String!, $type: SmartTestType!) {
    smartTest(id: $id, type: $type)
}
"""

QUERY_DISK_DEVICE = """
{
    disks {
        id
        device
    }
}
"""

# Map module params to GraphQL enum values
TEST_TYPE_MAP = {
    "short": "SHORT",
    "long": "LONG",
    "conveyance": "CONVEYANCE",
}


def get_disk_device(client, disk_id):
    """Look up the device node for a disk ID."""
    data = client.query(QUERY_DISK_DEVICE)
    for disk in data.get("disks", []):
        if disk.get("id") == disk_id:
            return disk.get("device")
    return None


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        id=dict(type="str", required=True),
        test_type=dict(
            type="str",
            required=True,
            choices=["short", "long", "conveyance"],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    disk_id = module.params["id"]
    test_type = module.params["test_type"]

    if module.check_mode:
        module.exit_json(
            changed=True,
            id=disk_id,
            test_type=test_type,
            method="check_mode",
            msg=f"Would initiate SMART {test_type} test on {disk_id}.",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Look up device for messaging and potential fallback
    device = get_disk_device(client, disk_id)
    if device is None:
        module.fail_json(msg=f"Disk '{disk_id}' not found.")

    # Try GraphQL mutation first
    try:
        client.mutate(
            MUTATION_SMART_TEST,
            variables={
                "id": disk_id,
                "type": TEST_TYPE_MAP[test_type],
            },
        )
        module.exit_json(
            changed=True,
            id=disk_id,
            test_type=test_type,
            device=device,
            method="graphql",
            msg=f"SMART {test_type} test initiated on {disk_id} (/dev/{device}).",
        )
    except UnraidError:
        # GraphQL mutation not available, fall back to SSH via smartctl
        pass

    # SSH fallback using smartctl
    rc, stdout, stderr = module.run_command(
        ["ssh", "root@" + module.params["api_url"].split("//")[-1].split(":")[0].split("/")[0],
         "smartctl", "-t", test_type, f"/dev/{device}"]
    )

    if rc != 0 and rc != 4:
        # smartctl returns 4 when a test is already in progress (acceptable)
        module.fail_json(
            msg=f"Failed to initiate SMART test via SSH fallback: {stderr.strip()}",
            id=disk_id,
            test_type=test_type,
            device=device,
            rc=rc,
        )

    module.exit_json(
        changed=True,
        id=disk_id,
        test_type=test_type,
        device=device,
        method="ssh_fallback",
        msg=f"SMART {test_type} test initiated on {disk_id} (/dev/{device}) via SSH fallback.",
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
