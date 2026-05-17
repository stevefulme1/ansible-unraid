#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for listing Unraid user accounts."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: user_info
short_description: List user accounts on Unraid
version_added: "1.0.0"
description:
  - Retrieve information about user accounts on an Unraid server via the
    GraphQL API.
  - Returns a list of all configured user accounts with available details.
  - This is an info module and never changes state on the target.
  - Requires Unraid 7.2 or later.

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
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - The Unraid GraphQL API returns usernames as a simple list. Detailed
    user attributes (groups, permissions) are not currently available via
    the API.
  - To manage users, see the M(stevefulme1.unraid.user) module.
"""

EXAMPLES = r"""
- name: List all users
  stevefulme1.unraid.user_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: user_list

- name: Display usernames
  ansible.builtin.debug:
    msg: "{{ user_list.users }}"

- name: Check if a specific user exists
  stevefulme1.unraid.user_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: user_list

- name: Assert user is present
  ansible.builtin.assert:
    that:
      - "'mediauser' in user_list.users"
    fail_msg: "User 'mediauser' is not configured"
"""

RETURN = r"""
users:
  description: List of user accounts on the Unraid server.
  returned: always
  type: list
  elements: str
  sample:
    - root
    - mediauser
    - backupuser
count:
  description: Total number of user accounts.
  returned: always
  type: int
  sample: 3
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_USERS = "{ users }"


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
        data = client.query(QUERY_USERS)
        users = data.get("users", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query users: %s" % str(exc))

    module.exit_json(changed=False, users=users, count=len(users))


if __name__ == "__main__":
    main()
