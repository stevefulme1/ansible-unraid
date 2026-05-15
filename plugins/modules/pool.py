#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: pool
short_description: Manage Unraid cache/storage pools
description:
    - Manage the desired state of cache and storage pools on Unraid.
    - Queries the current pool configuration via the Unraid GraphQL API.
    - The Unraid GraphQL API currently provides read-only access to pool
      configuration. Pool creation and deletion must be performed through
      the Unraid web UI. This module validates that a pool exists (or does
      not exist) and reports accordingly.
    - When C(state=present), the module verifies the named pool exists.
    - When C(state=absent), the module verifies the named pool does not
      exist and warns that removal requires the web UI.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    name:
        description:
            - Name of the cache or storage pool to manage.
        type: str
        required: true
    state:
        description:
            - Desired state of the pool.
            - C(present) ensures the pool exists (read-only verification).
            - C(absent) checks whether the pool exists and warns that
              removal must be done via the Unraid web UI.
        type: str
        required: true
        choices:
            - present
            - absent
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - The Unraid GraphQL API does not currently support pool creation or
      deletion mutations. This module operates in a read-only validation
      mode. Use the Unraid web UI for pool management operations.
"""

EXAMPLES = r"""
- name: Verify cache pool exists
  stevefulme1.unraid.pool:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    name: cache
    state: present

- name: Verify pool has been removed
  stevefulme1.unraid.pool:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: fast_pool
    state: absent
"""

RETURN = r"""
pool:
    description: Pool details when the pool exists.
    returned: when pool is found
    type: dict
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
exists:
    description: Whether the pool currently exists.
    returned: always
    type: bool
    sample: true
msg:
    description: Human-readable result message.
    returned: always
    type: str
    sample: "Pool 'cache' exists."
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
        }
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", required=True, choices=["present", "absent"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    pool_name = module.params["name"]
    desired_state = module.params["state"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        data = client.query(QUERY_POOLS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query pools: {exc}")

    caches = data.get("array", {}).get("caches", [])
    pool = next((p for p in caches if p.get("name") == pool_name), None)
    pool_exists = pool is not None

    if desired_state == "present":
        if pool_exists:
            module.exit_json(
                changed=False,
                exists=True,
                pool=pool,
                msg=f"Pool '{pool_name}' exists.",
            )
        else:
            module.fail_json(
                msg=f"Pool '{pool_name}' does not exist. "
                    f"Pool creation is not supported via the GraphQL API. "
                    f"Use the Unraid web UI to create pools.",
                exists=False,
            )

    if desired_state == "absent":
        if not pool_exists:
            module.exit_json(
                changed=False,
                exists=False,
                msg=f"Pool '{pool_name}' does not exist.",
            )
        else:
            module.fail_json(
                msg=f"Pool '{pool_name}' exists but cannot be removed via "
                    f"the GraphQL API. Use the Unraid web UI to remove pools.",
                exists=True,
                pool=pool,
            )


def main():
    run_module()


if __name__ == "__main__":
    main()
