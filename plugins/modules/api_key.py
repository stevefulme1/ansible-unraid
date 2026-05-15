#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing Unraid API keys."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: api_key
short_description: Manage API keys on Unraid
version_added: "1.0.0"
description:
  - Create, update, and delete API keys on an Unraid server via the GraphQL API.
  - When creating a key, the generated key value is returned in the result.
    Store it securely as it cannot be retrieved again.
options:
  name:
    description:
      - The name for the API key.
      - Used to identify the key when querying or matching existing keys.
    type: str
    required: true
  state:
    description:
      - The desired state of the API key.
      - C(present) creates or updates the key.
      - C(absent) deletes the key if it exists.
    type: str
    choices: [present, absent]
    default: present
  description:
    description:
      - An optional description for the API key.
    type: str
    required: false
  roles:
    description:
      - List of roles to assign to the API key.
      - Valid choices are C(ADMIN), C(CONNECT), and C(GUEST).
    type: list
    elements: str
    required: false
    default: []
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Create an admin API key
  stevefulme1.unraid.api_key:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: automation-key
    description: "Key for Ansible automation"
    roles:
      - ADMIN
  register: new_key

- name: Display the generated key
  ansible.builtin.debug:
    msg: "New API key value: {{ new_key.key_value }}"

- name: Delete an API key
  stevefulme1.unraid.api_key:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: automation-key
    state: absent
"""

RETURN = r"""
api_key:
  description: The API key object with id, name, and roles.
  returned: when state is present
  type: dict
  contains:
    id:
      description: The unique identifier of the API key.
      type: str
    name:
      description: The name of the API key.
      type: str
    roles:
      description: The roles assigned to the API key.
      type: list
      elements: str
  sample:
    id: "abc-123"
    name: "automation-key"
    roles: ["ADMIN"]
key_value:
  description:
    - The generated API key value. Only returned on creation.
    - This value cannot be retrieved again after creation.
  returned: when a new key is created
  type: str
  sample: "unraid_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
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
    name
    roles {
      role
    }
  }
}
"""

CREATE_API_KEY = """
mutation($input: ApiKeyInput!) {
  apiKey {
    create(input: $input)
  }
}
"""

UPDATE_API_KEY = """
mutation($id: String!, $input: ApiKeyInput!) {
  apiKey {
    update(id: $id, input: $input)
  }
}
"""

DELETE_API_KEY = """
mutation($id: String!) {
  apiKey {
    delete(id: $id)
  }
}
"""

VALID_ROLES = ["ADMIN", "CONNECT", "GUEST"]


def find_key_by_name(client, name):
    """Find an API key by name. Returns the key dict or None."""
    result = client.query(QUERY_API_KEYS)
    keys = result.get("apiKeys", [])
    for key in keys:
        if key.get("name") == name:
            return {
                "id": key["id"],
                "name": key["name"],
                "roles": [r["role"] for r in key.get("roles", [])],
            }
    return None


def build_input(module):
    """Build the API key input object from module params."""
    api_input = {"name": module.params["name"]}
    if module.params.get("description") is not None:
        api_input["description"] = module.params["description"]
    if module.params.get("roles"):
        api_input["roles"] = module.params["roles"]
    return api_input


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        description=dict(type="str", required=False),
        roles=dict(
            type="list",
            elements="str",
            required=False,
            default=[],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    # Validate roles
    for role in module.params.get("roles", []):
        if role not in VALID_ROLES:
            module.fail_json(
                msg=f"Invalid role '{role}'. Valid choices: {', '.join(VALID_ROLES)}"
            )

    name = module.params["name"]
    state = module.params["state"]

    try:
        client = get_client(module)
        existing = find_key_by_name(client, name)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # --- state: absent ---
    if state == "absent":
        if existing is None:
            module.exit_json(changed=False)
        if module.check_mode:
            module.exit_json(changed=True)
        try:
            client.mutate(DELETE_API_KEY, {"id": existing["id"]})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to delete API key '{name}': {exc}")
        module.exit_json(changed=True)

    # --- state: present ---
    api_input = build_input(module)
    desired_roles = sorted(module.params.get("roles", []))

    if existing is not None:
        # Check if update is needed
        current_roles = sorted(existing.get("roles", []))
        if current_roles == desired_roles:
            module.exit_json(changed=False, api_key=existing)

        if module.check_mode:
            module.exit_json(changed=True, api_key=existing)

        try:
            client.mutate(UPDATE_API_KEY, {"id": existing["id"], "input": api_input})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to update API key '{name}': {exc}")

        updated = find_key_by_name(client, name)
        module.exit_json(changed=True, api_key=updated)

    # Create new key
    if module.check_mode:
        module.exit_json(
            changed=True,
            api_key={"id": None, "name": name, "roles": desired_roles},
            key_value="(check mode - no key generated)",
        )

    try:
        result = client.mutate(CREATE_API_KEY, {"input": api_input})
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to create API key '{name}': {exc}")

    # Extract key value from nested response
    key_value = None
    api_key_data = result.get("apiKey", {})
    if isinstance(api_key_data, dict):
        key_value = api_key_data.get("create")

    created = find_key_by_name(client, name)
    result_data = {"changed": True, "api_key": created or {"name": name, "roles": desired_roles}}
    if key_value:
        result_data["key_value"] = key_value
    module.exit_json(**result_data)


if __name__ == "__main__":
    main()
