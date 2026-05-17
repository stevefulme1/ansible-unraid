#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: update_info
short_description: Check for Unraid OS updates
description:
    - Queries the current Unraid OS version and available update information.
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
- name: Check for updates
  stevefulme1.unraid.update_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: update_status

- name: Notify if update available
  ansible.builtin.debug:
    msg: "Update available: {{ update_status.info.version }}"
"""

RETURN = r"""
info:
    description: System version and update information.
    returned: success
    type: dict
    sample:
        version: "7.2.5"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY = """
{
    info {
        os {
            version
        }
    }
    vars {
        version
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
        info = {
            "version": data.get("vars", {}).get("version", ""),
            "os": data.get("info", {}).get("os", {}),
        }
        module.exit_json(changed=False, info=info)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
