#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: var_info
short_description: Query system runtime variables from Unraid
description:
    - Retrieves system runtime variables from an Unraid server via the
      GraphQL API.
    - Returns hostname, Unraid version, timezone, CSRF token, and other
      system variables exposed by the C(vars) query.
    - This is a read-only module that never makes changes.
    - Useful for gathering system facts or validating server identity
      and configuration.
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
- name: Get system variables
  stevefulme1.unraid.var_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: sysvar

- name: Display hostname and version
  ansible.builtin.debug:
    msg: "{{ sysvar.vars.hostname }} running Unraid {{ sysvar.vars.version }}"

- name: Use timezone in conditional
  ansible.builtin.debug:
    msg: "Server is in Eastern time"
  when: sysvar.vars.timezone == "America/New_York"
"""

RETURN = r"""
vars:
    description: System runtime variables.
    returned: success
    type: dict
    contains:
        hostname:
            description: The server hostname.
            type: str
        version:
            description: The Unraid OS version.
            type: str
        timezone:
            description: The configured timezone.
            type: str
        csrf_token:
            description: The current CSRF token.
            type: str
    sample:
        hostname: Tower
        version: "7.2.0"
        timezone: America/New_York
        csrf_token: "abc123def456"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY = """
{
    vars {
        hostname
        version
        timezone
        csrfToken
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
        raw = data.get("vars", {})
        result = dict(
            hostname=raw.get("hostname"),
            version=raw.get("version"),
            timezone=raw.get("timezone"),
            csrf_token=raw.get("csrfToken"),
        )
        module.exit_json(changed=False, vars=result)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
