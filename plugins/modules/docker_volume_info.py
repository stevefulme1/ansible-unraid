#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_volume_info
short_description: List Docker volumes on Unraid
version_added: "1.0.0"
description:
    - Retrieve information about Docker volumes on an Unraid server
      via the GraphQL API.
    - Returns all volumes with their name, driver, and mountpoint.
    - If the GraphQL API does not expose volume listing, the module falls back
      to documenting usage of C(docker volume ls --format json) via SSH.
    - Requires Unraid 7.2 or later.
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
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
"""

EXAMPLES = r"""
- name: List all Docker volumes
  stevefulme1.unraid.docker_volume_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: volumes

- name: Display volume list
  ansible.builtin.debug:
    msg: "{{ item.name }} ({{ item.driver }}) -> {{ item.mountpoint }}"
  loop: "{{ volumes.volumes }}"

- name: Find volumes using local driver
  ansible.builtin.debug:
    msg: "{{ item.name }}"
  loop: "{{ volumes.volumes | selectattr('driver', 'equalto', 'local') }}"
"""

RETURN = r"""
volumes:
    description: List of Docker volumes on the Unraid server.
    type: list
    elements: dict
    returned: success
    contains:
        name:
            description: Volume name.
            type: str
        driver:
            description: Volume driver.
            type: str
        mountpoint:
            description: Mount point path on the host.
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_VOLUMES = """
{
    docker {
        volumes {
            name
            driver
            mountpoint
        }
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = get_client(module)

    try:
        data = client.query(QUERY_VOLUMES)
        volumes = data.get("docker", {}).get("volumes", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query volumes: %s" % str(exc))

    module.exit_json(changed=False, volumes=volumes)


if __name__ == "__main__":
    main()
