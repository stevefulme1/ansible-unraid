#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: plugin_info
short_description: List installed plugins on an Unraid server
description:
    - Retrieves the list of installed Community Apps plugins.
    - Returns plugin name and module information.
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
- name: List installed plugins
  stevefulme1.unraid.plugin_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: plugins

- name: Show plugin names
  ansible.builtin.debug:
    msg: "{{ plugins.plugins | map(attribute='name') | list }}"
"""

RETURN = r"""
plugins:
    description: List of installed plugins.
    returned: success
    type: list
    elements: dict
    sample:
        - name: "dynamix.system.stats"
          module: "dynamix.system.stats.plg"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY = """
{
    plugins {
        name
        module
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
        module.exit_json(changed=False, plugins=data.get("plugins", []))
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
