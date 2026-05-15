#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing roles on Unraid API keys."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: api_key_role
short_description: Add or remove roles on an Unraid API key
version_added: "1.0.0"
description:
  - Add or remove individual roles on an existing API key via the
    Unraid GraphQL API.
  - Use this module when you need to modify roles on a key without
    recreating it.
options:
  key_id:
    description:
      - The unique identifier of the API key to modify.
      - Obtain this from the C(api_key) module or the Unraid WebGUI.
    type: str
    required: true
  role:
    description:
      - The role to add or remove.
    type: str
    required: true
    choices: [ADMIN, CONNECT, GUEST]
  state:
    description:
      - C(present) adds the role to the API key.
      - C(absent) removes the role from the API key.
    type: str
    choices: [present, absent]
    default: present
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Add ADMIN role to an API key
  stevefulme1.unraid.api_key_role:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    key_id: "abc-123-def"
    role: ADMIN
    state: present

- name: Remove GUEST role from an API key
  stevefulme1.unraid.api_key_role:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    key_id: "abc-123-def"
    role: GUEST
    state: absent
"""

RETURN = r"""
key_id:
  description: The API key identifier that was modified.
  returned: always
  type: str
  sample: "abc-123-def"
role:
  description: The role that was added or removed.
  returned: always
  type: str
  sample: "ADMIN"
current_roles:
  description: The roles currently assigned to the API key after the operation.
  returned: success
  type: list
  elements: str
  sample: ["ADMIN", "CONNECT"]
"""

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)
from ansible.module_utils.basic import AnsibleModule


QUERY_API_KEYS = """
{
  apiKeys {
    id
    roles {
      role
    }
  }
}
"""

ADD_ROLE_MUTATION = """
mutation($id: String!, $role: String!) {
  apiKey {
    addRole(id: $id, role: $role)
  }
}
"""

REMOVE_ROLE_MUTATION = """
mutation($id: String!, $role: String!) {
  apiKey {
    removeRole(id: $id, role: $role)
  }
}
"""


def get_key_roles(client, key_id):
    """Get the current roles for a specific API key by ID."""
    result = client.query(QUERY_API_KEYS)
    for key in result.get("apiKeys", []):
        if key.get("id") == key_id:
            return [r["role"] for r in key.get("roles", [])]
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        key_id=dict(type="str", required=True),
        role=dict(type="str", required=True, choices=["ADMIN", "CONNECT", "GUEST"]),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    key_id = module.params["key_id"]
    role = module.params["role"]
    state = module.params["state"]

    try:
        client = get_client(module)
        current_roles = get_key_roles(client, key_id)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    if current_roles is None:
        module.fail_json(msg=f"API key with id '{key_id}' not found.")

    has_role = role in current_roles

    if state == "present" and has_role:
        module.exit_json(
            changed=False, key_id=key_id, role=role, current_roles=current_roles
        )

    if state == "absent" and not has_role:
        module.exit_json(
            changed=False, key_id=key_id, role=role, current_roles=current_roles
        )

    if module.check_mode:
        if state == "present":
            projected_roles = current_roles + [role]
        else:
            projected_roles = [r for r in current_roles if r != role]
        module.exit_json(
            changed=True, key_id=key_id, role=role, current_roles=projected_roles
        )

    mutation = ADD_ROLE_MUTATION if state == "present" else REMOVE_ROLE_MUTATION
    action = "add" if state == "present" else "remove"

    try:
        client.mutate(mutation, {"id": key_id, "role": role})
    except UnraidError as exc:
        module.fail_json(
            msg=f"Failed to {action} role '{role}' on API key '{key_id}': {exc}"
        )

    # Re-fetch to return accurate state
    try:
        updated_roles = get_key_roles(client, key_id)
    except UnraidError:
        updated_roles = None

    module.exit_json(
        changed=True,
        key_id=key_id,
        role=role,
        current_roles=updated_roles or [],
    )


if __name__ == "__main__":
    main()
