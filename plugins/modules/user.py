#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing Unraid user accounts."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: user
short_description: Create user accounts on Unraid
version_added: "1.0.0"
description:
  - Create user accounts on an Unraid server via the GraphQL API.
  - The Unraid GraphQL API (7.2+) only supports creating users via C(addUser).
  - There is no API support for deleting or modifying users. Those operations
    must be performed through the Unraid WebGUI or via SSH.
  - If a user already exists, the module reports no change.
options:
  name:
    description:
      - The username for the new account.
    type: str
    required: true
  password:
    description:
      - The password for the new account.
      - Required when creating a new user.
    type: str
    required: false
  description:
    description:
      - An optional description for the user account.
    type: str
    required: false
  state:
    description:
      - The desired state of the user account.
      - Only C(present) is supported because the Unraid GraphQL API does not
        expose a user deletion mutation.
    type: str
    choices: [present]
    default: present
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Create a new user
  stevefulme1.unraid.user:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: mediauser
    password: "{{ user_password }}"
    description: "Media library access"

- name: Ensure user exists (idempotent)
  stevefulme1.unraid.user:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: mediauser
    password: "{{ user_password }}"
"""

RETURN = r"""
user:
  description: The username that was created or already existed.
  returned: success
  type: str
  sample: mediauser
created:
  description: Whether a new user was created.
  returned: success
  type: bool
  sample: true
"""

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)
from ansible.module_utils.basic import AnsibleModule


QUERY_USERS = "{ users }"

ADD_USER_MUTATION = """
mutation($name: String!, $password: String!, $description: String) {
  addUser(name: $name, password: $password, description: $description)
}
"""


def get_existing_users(client):
    """Return the list of existing usernames."""
    result = client.query(QUERY_USERS)
    return result.get("users", [])


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        password=dict(type="str", required=False, no_log=True),
        description=dict(type="str", required=False),
        state=dict(type="str", choices=["present"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["password"], False),
        ],
    )

    name = module.params["name"]
    password = module.params["password"]
    description = module.params.get("description")

    try:
        client = get_client(module)
        existing_users = get_existing_users(client)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    if name in existing_users:
        module.exit_json(changed=False, user=name, created=False)

    if module.check_mode:
        module.exit_json(changed=True, user=name, created=True)

    variables = {"name": name, "password": password}
    if description is not None:
        variables["description"] = description

    try:
        client.mutate(ADD_USER_MUTATION, variables)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to create user '{name}': {exc}")

    module.exit_json(changed=True, user=name, created=True)


if __name__ == "__main__":
    main()
