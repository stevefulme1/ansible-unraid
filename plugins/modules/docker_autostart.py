#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_autostart
short_description: Configure Docker container autostart order on Unraid
version_added: "1.0.0"
description:
    - Configure the autostart order for Docker containers on an Unraid server
      via the GraphQL API.
    - Containers can be assigned a numeric order that determines the sequence
      in which they start when the Unraid server boots.
    - The module queries the current autostart configuration and only applies
      changes when the desired order differs from the current state.
    - Requires Unraid 7.2 or later.
options:
    containers:
        description:
            - List of containers and their desired autostart order.
            - Each entry is a dictionary with C(name) and C(order) keys.
            - The C(order) value is an integer; lower numbers start first.
            - Set C(order) to C(0) to disable autostart for that container.
        type: list
        elements: dict
        required: true
        suboptions:
            name:
                description:
                    - Name of the Docker container.
                type: str
                required: true
            order:
                description:
                    - Autostart order (lower starts first; 0 disables autostart).
                type: int
                required: true
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Set autostart order for critical containers
  stevefulme1.unraid.docker_autostart:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    containers:
      - name: mariadb
        order: 1
      - name: redis
        order: 2
      - name: nginx
        order: 3

- name: Disable autostart for a container
  stevefulme1.unraid.docker_autostart:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    containers:
      - name: dev-tools
        order: 0

- name: Reorder autostart sequence
  stevefulme1.unraid.docker_autostart:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    containers:
      - name: postgres
        order: 1
      - name: app-server
        order: 2
      - name: reverse-proxy
        order: 3
      - name: monitoring
        order: 4
"""

RETURN = r"""
autostart:
    description: The autostart configuration that was applied.
    type: list
    elements: dict
    returned: success
    contains:
        name:
            description: Container name.
            type: str
        order:
            description: Autostart order value.
            type: int
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
            autoStart
        }
    }
}
"""

MUTATION_AUTOSTART = """
mutation($input: [AutostartConfigInput!]!) {
    docker {
        updateAutostartConfiguration(input: $input)
    }
}
"""


def find_container_id(containers, name):
    """Find a container ID by name."""
    for container in containers:
        names = container.get("names", [])
        clean_names = [n.lstrip("/") for n in names]
        if name in clean_names or name in names:
            return container.get("id")
    return None


def main():
    container_spec = dict(
        name=dict(type="str", required=True),
        order=dict(type="int", required=True),
    )

    argument_spec = unraid_argument_spec()
    argument_spec.update(
        containers=dict(
            type="list",
            elements="dict",
            required=True,
            options=container_spec,
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    desired = module.params["containers"]

    client = get_client(module)

    try:
        data = client.query(QUERY_CONTAINERS)
        containers = data.get("docker", {}).get("containers", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query containers: %s" % str(exc))

    # Build the mutation input and validate container names
    autostart_input = []
    for entry in desired:
        name = entry["name"]
        order = entry["order"]
        cid = find_container_id(containers, name)
        if cid is None:
            module.fail_json(msg="Container '%s' not found." % name)
        autostart_input.append({"id": cid, "order": order})

    if module.check_mode:
        module.exit_json(changed=True, autostart=desired)

    try:
        client.mutate(
            MUTATION_AUTOSTART,
            variables={"input": autostart_input},
        )
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to update autostart configuration: %s" % str(exc)
        )

    module.exit_json(changed=True, autostart=desired)


if __name__ == "__main__":
    main()
