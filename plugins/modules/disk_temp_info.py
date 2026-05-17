#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: disk_temp_info
short_description: Query disk temperatures from Unraid
description:
    - Query the Unraid GraphQL API for current disk temperatures.
    - Returns only disk identifiers, names, and temperature readings.
    - Useful for monitoring playbooks and alerting on thermal thresholds.
    - This is a read-only info module and makes no changes.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)

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
- name: Get all disk temperatures
  stevefulme1.unraid.disk_temp_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
  register: temps

- name: Alert on disks over 45C
  ansible.builtin.debug:
    msg: "WARNING: {{ item.name }} ({{ item.id }}) is at {{ item.temperature }}C!"
  loop: "{{ temps.disks }}"
  when: item.temperature is not none and item.temperature | int > 45

- name: Find hottest disk
  ansible.builtin.debug:
    msg: >-
      Hottest disk: {{ (temps.disks | sort(attribute='temperature', reverse=True) | first).name }}
      at {{ (temps.disks | sort(attribute='temperature', reverse=True) | first).temperature }}C
  when: temps.disks | selectattr('temperature', 'ne', none) | list | length > 0
"""

RETURN = r"""
disks:
    description: List of disk temperature readings.
    returned: always
    type: list
    elements: dict
    contains:
        id:
            description: Disk identifier.
            type: str
            sample: disk1
        name:
            description: Human-readable disk name.
            type: str
            sample: "Disk 1"
        temperature:
            description: Current disk temperature in Celsius. Null if unavailable (e.g., disk in standby).
            type: int
            sample: 35
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_DISK_TEMPS = """
{
    disks {
        id
        name
        temperature
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        data = client.query(QUERY_DISK_TEMPS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query disk temperatures: {exc}")

    disks = data.get("disks", [])

    # Return only the fields relevant to temperature monitoring
    result = [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "temperature": d.get("temperature"),
        }
        for d in disks
    ]

    module.exit_json(changed=False, disks=result)


def main():
    run_module()


if __name__ == "__main__":
    main()
