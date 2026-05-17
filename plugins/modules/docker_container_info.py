#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_container_info
short_description: Retrieve detailed Docker container information from Unraid
version_added: "1.0.0"
description:
    - Query detailed information about Docker containers on an Unraid server
      via the GraphQL API.
    - Return all containers or filter by name or ID.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Name of the container to filter by.
            - Mutually exclusive with O(id).
        type: str
    id:
        description:
            - Docker container ID (full or short) to filter by.
            - Mutually exclusive with O(name).
        type: str

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
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Get info about all containers
  stevefulme1.unraid.docker_container_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: all_containers

- name: Get info about a specific container by name
  stevefulme1.unraid.docker_container_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: plex
  register: plex_info

- name: Get info about a specific container by ID
  stevefulme1.unraid.docker_container_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: abc123def456
  register: container_info

- name: Display container states
  ansible.builtin.debug:
    msg: "{{ item.names[0] }} is {{ item.state }}"
  loop: "{{ all_containers.containers }}"
"""

RETURN = r"""
containers:
    description: List of container details matching the filter criteria.
    type: list
    elements: dict
    returned: success
    contains:
        id:
            description: Docker container ID.
            type: str
        names:
            description: List of container names.
            type: list
            elements: str
        image:
            description: Image used by the container.
            type: str
        state:
            description: Current container state (e.g. running, exited).
            type: str
        status:
            description: Human-readable status string.
            type: str
        ports:
            description: Port mappings for the container.
            type: list
        autoStart:
            description: Whether the container is set to auto-start.
            type: bool
        created:
            description: Container creation timestamp.
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_CONTAINERS = """
{
    docker {
        containers {
            id
            names
            image
            state
            status
            ports
            autoStart
            created
        }
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str"),
        id=dict(type="str"),
    )
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["name", "id"]],
        supports_check_mode=True,
    )

    name = module.params["name"]
    container_id = module.params["id"]

    client = get_client(module)

    try:
        data = client.query(QUERY_CONTAINERS)
        containers = data.get("docker", {}).get("containers", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query containers: %s" % str(exc))

    # Filter if name or id provided
    if name:
        containers = [
            c for c in containers
            if name in c.get("names", [])
            or name in [n.lstrip("/") for n in c.get("names", [])]
        ]
    elif container_id:
        containers = [
            c for c in containers
            if c.get("id", "").startswith(container_id)
        ]

    module.exit_json(changed=False, containers=containers)


if __name__ == "__main__":
    main()
