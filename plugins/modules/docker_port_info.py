#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_port_info
short_description: Check for Docker port conflicts on Unraid
version_added: "1.0.0"
description:
    - Query the Unraid GraphQL API for Docker port conflicts.
    - Returns a list of ports that are used by multiple containers,
      which can cause networking issues.
    - Useful for pre-deployment validation and health-check playbooks.
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
- name: Check for port conflicts
  stevefulme1.unraid.docker_port_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: ports

- name: Display port conflicts
  ansible.builtin.debug:
    msg: "Port {{ item.port }} is used by: {{ item.containers | join(', ') }}"
  loop: "{{ ports.conflicts }}"

- name: Fail if port conflicts exist
  ansible.builtin.fail:
    msg: "Port conflicts detected on {{ ports.conflicts | length }} port(s)"
  when: ports.conflicts | length > 0

- name: Check if specific port has conflict
  ansible.builtin.debug:
    msg: "Port 8080 conflict: {{ ports.conflicts | selectattr('port', 'equalto', 8080) | list }}"
"""

RETURN = r"""
conflicts:
    description: List of port conflicts detected.
    type: list
    elements: dict
    returned: success
    contains:
        port:
            description: The conflicting port number.
            type: int
        containers:
            description: List of container names using this port.
            type: list
            elements: str
has_conflicts:
    description: Whether any port conflicts were detected.
    type: bool
    returned: success
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_PORT_CONFLICTS = """
{
    docker {
        portConflicts {
            port
            containers
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
        data = client.query(QUERY_PORT_CONFLICTS)
        conflicts = data.get("docker", {}).get("portConflicts", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query port conflicts: %s" % str(exc))

    module.exit_json(
        changed=False,
        conflicts=conflicts,
        has_conflicts=len(conflicts) > 0,
    )


if __name__ == "__main__":
    main()
