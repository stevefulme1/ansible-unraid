#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_log
short_description: Retrieve Docker container logs from Unraid
version_added: "1.0.0"
description:
    - Retrieve log output from a Docker container on an Unraid server
      via the GraphQL API.
    - Returns the most recent log lines with timestamps.
    - Useful for monitoring, debugging, and health-check playbooks.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Name of the container.
            - At least one of O(name) or O(id) is required.
        type: str
    id:
        description:
            - Docker container ID (full or short).
            - At least one of O(name) or O(id) is required.
        type: str
    lines:
        description:
            - Number of most recent log lines to retrieve.
        type: int
        default: 100
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Get last 100 log lines for a container
  stevefulme1.unraid.docker_log:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: nginx
  register: logs

- name: Get last 50 log lines by container ID
  stevefulme1.unraid.docker_log:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: abc123def456
    lines: 50
  register: logs

- name: Display log output
  ansible.builtin.debug:
    msg: "{{ item.timestamp }}: {{ item.message }}"
  loop: "{{ logs.log_entries }}"

- name: Check for errors in logs
  ansible.builtin.fail:
    msg: "Errors found in container logs"
  when: logs.log_entries | selectattr('message', 'search', 'ERROR') | list | length > 0
"""

RETURN = r"""
log_entries:
    description: List of log entries from the container.
    type: list
    elements: dict
    returned: success
    contains:
        timestamp:
            description: Timestamp of the log entry.
            type: str
        message:
            description: Log message content.
            type: str
container_id:
    description: The resolved container ID.
    type: str
    returned: success
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
        }
    }
}
"""

QUERY_LOGS = """
query($id: String!, $lines: Int) {
    docker {
        logs(id: $id, tail: $lines) {
            timestamp
            message
        }
    }
}
"""


def find_container(containers, name=None, container_id=None):
    """Find a container by name or ID from the list returned by the API."""
    for container in containers:
        if container_id and container.get("id", "").startswith(container_id):
            return container
        if name:
            names = container.get("names", [])
            clean_names = [n.lstrip("/") for n in names]
            if name in clean_names or name in names:
                return container
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str"),
        id=dict(type="str"),
        lines=dict(type="int", default=100),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["name", "id"]],
        mutually_exclusive=[["name", "id"]],
        supports_check_mode=True,
    )

    name = module.params["name"]
    container_id = module.params["id"]
    lines = module.params["lines"]

    client = get_client(module)

    # Resolve container ID if name was provided
    if name:
        try:
            data = client.query(QUERY_CONTAINERS)
            containers = data.get("docker", {}).get("containers", [])
        except UnraidError as exc:
            module.fail_json(msg="Failed to query containers: %s" % str(exc))

        container = find_container(containers, name=name)
        if container is None:
            module.fail_json(msg="Container '%s' not found." % name)
        container_id = container["id"]

    # Query logs
    try:
        data = client.query(
            QUERY_LOGS,
            variables={"id": container_id, "lines": lines},
        )
        log_entries = data.get("docker", {}).get("logs", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to retrieve logs: %s" % str(exc))

    module.exit_json(
        changed=False,
        log_entries=log_entries,
        container_id=container_id,
    )


if __name__ == "__main__":
    main()
