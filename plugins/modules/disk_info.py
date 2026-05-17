#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: disk_info
short_description: Retrieve detailed per-disk information from Unraid
description:
    - Query the Unraid GraphQL API for detailed information about
      all disks or a single disk by ID.
    - Returns device identifiers, size, temperature, serial number,
      status, standby state, partition layout, and SMART health data.
    - This is a read-only info module and makes no changes.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    id:
        description:
            - Disk identifier to filter results to a single disk.
            - When omitted, information for all disks is returned.
        type: str
        required: false

    limit:
      description:
        - Maximum number of results to return.
      type: int
      default: 100
    offset:
      description:
        - Number of results to skip for pagination.
      type: int
      default: 0
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Get information about all disks
  stevefulme1.unraid.disk_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
  register: all_disks

- name: Get information about a specific disk
  stevefulme1.unraid.disk_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: disk1
  register: single_disk

- name: Display disk temperatures
  ansible.builtin.debug:
    msg: "{{ item.name }}: {{ item.temperature }}C"
  loop: "{{ all_disks.disks }}"
  when: item.temperature is not none
"""

RETURN = r"""
disks:
    description: List of disk information dictionaries.
    returned: always
    type: list
    elements: dict
    contains:
        id:
            description: Disk identifier.
            type: str
            sample: disk1
        device:
            description: Device node path.
            type: str
            sample: sda
        name:
            description: Human-readable disk name.
            type: str
            sample: "Disk 1"
        size:
            description: Total disk size in bytes.
            type: int
            sample: 4000787030016
        temperature:
            description: Current disk temperature in Celsius.
            type: int
            sample: 35
        serial:
            description: Disk serial number.
            type: str
            sample: WDC_WD40EFRX-68N32N0_WD-WCC7K0123456
        status:
            description: Current disk status.
            type: str
            sample: DISK_OK
        standby:
            description: Whether the disk is in standby mode.
            type: bool
            sample: false
        partitions:
            description: List of partitions on the disk.
            type: list
            elements: dict
            contains:
                name:
                    description: Partition name.
                    type: str
                    sample: sda1
                size:
                    description: Partition size in bytes.
                    type: int
                    sample: 4000785129472
                fsType:
                    description: Filesystem type.
                    type: str
                    sample: xfs
        smart:
            description: SMART health data for the disk.
            type: dict
            contains:
                passed:
                    description: Whether the SMART self-assessment passed.
                    type: bool
                    sample: true
                attributes:
                    description: List of SMART attributes.
                    type: list
                    elements: dict
                    contains:
                        id:
                            description: SMART attribute ID.
                            type: int
                            sample: 1
                        name:
                            description: SMART attribute name.
                            type: str
                            sample: Raw_Read_Error_Rate
                        value:
                            description: Current attribute value.
                            type: int
                            sample: 200
                        worst:
                            description: Worst recorded attribute value.
                            type: int
                            sample: 200
                        threshold:
                            description: Failure threshold.
                            type: int
                            sample: 51
                        rawValue:
                            description: Raw attribute value.
                            type: str
                            sample: "0"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_DISKS = """
{
    disks {
        id
        device
        name
        size
        temperature
        serial
        status
        standby
        partitions {
            name
            size
            fsType
        }
        smart {
            passed
            attributes {
                id
                name
                value
                worst
                threshold
                rawValue
            }
        }
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        id=dict(type="str", required=False, default=None),
    )
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    disk_id = module.params["id"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        data = client.query(QUERY_DISKS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query disk information: {exc}")

    disks = data.get("disks", [])

    if disk_id is not None:
        disks = [d for d in disks if d.get("id") == disk_id]
        if not disks:
            module.fail_json(msg=f"Disk with id '{disk_id}' not found.")

    module.exit_json(changed=False, disks=disks)


def main():
    run_module()


if __name__ == "__main__":
    main()
