#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: service_info
short_description: Query running services on an Unraid server
description:
    - Retrieves information about running services on an Unraid server.
    - Returns service name, online status, version, and uptime.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
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
"""

EXAMPLES = r"""
- name: List all running services
  stevefulme1.unraid.service_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: services

- name: Show services
  ansible.builtin.debug:
    var: services.services
"""

RETURN = r"""
services:
    description: List of services and their status.
    returned: success
    type: list
    elements: dict
    sample:
        - name: docker
          online: true
          version: "24.0.7"
          uptime: 86400
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY = """
{
    services {
        name
        online
        version
        uptime
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    try:
        client = get_client(module)
        data = client.query(QUERY)
        module.exit_json(changed=False, services=data.get("services", []))
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
