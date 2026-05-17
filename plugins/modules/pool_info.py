#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pool_info
short_description: List Unraid cache and storage pools
description:
    - Query the Unraid GraphQL API for information about all
      configured cache and storage pools.
    - Returns pool identifiers, status, capacity, and filesystem details.
    - This is a read-only info module and makes no changes.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)

options:
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
- name: List all cache pools
  stevefulme1.unraid.pool_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
  register: pools

- name: Display pool usage
  ansible.builtin.debug:
    msg: "{{ item.name }}: {{ item.used | default(0) }} / {{ item.size }} bytes"
  loop: "{{ pools.pools }}"
"""

RETURN = r"""
pools:
    description: List of cache/storage pool information dictionaries.
    returned: always
    type: list
    elements: dict
    contains:
        id:
            description: Pool identifier.
            type: str
            sample: cache
        name:
            description: Pool name.
            type: str
            sample: cache
        status:
            description: Current pool status.
            type: str
            sample: DISK_OK
        size:
            description: Total pool size in bytes.
            type: int
            sample: 500107862016
        free:
            description: Free space in bytes.
            type: int
            sample: 300000000000
        used:
            description: Used space in bytes.
            type: int
            sample: 200107862016
        fsType:
            description: Filesystem type.
            type: str
            sample: btrfs
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_POOLS = """
{
    array {
        caches {
            id
            name
            status
            size
            free
            used
            fsType
        }
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
        data = client.query(QUERY_POOLS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query pool information: {exc}")

    pools = data.get("array", {}).get("caches", [])

    module.exit_json(changed=False, pools=pools)


def main():
    run_module()


if __name__ == "__main__":
    main()
