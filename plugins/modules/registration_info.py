#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for querying Unraid license/registration info."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: registration_info
short_description: Query Unraid license and registration information
version_added: "1.0.0"
description:
  - Retrieve license and registration details from an Unraid server via
    the GraphQL API.
  - Returns the license type (Basic, Plus, Pro, etc.), registration state,
    and expiration information.
  - This is an info module and never changes state on the target.
  - Useful for compliance checks, inventory audits, and ensuring license
    validity across a fleet of Unraid servers.
  - Requires Unraid 7.2 or later.
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - Registration information is read-only. License management must be
    performed through the Unraid WebGUI or at C(https://unraid.net/account).
  - The C(expiration) field may be null for lifetime licenses.
"""

EXAMPLES = r"""
- name: Get registration info
  stevefulme1.unraid.registration_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: reg_info

- name: Display license type
  ansible.builtin.debug:
    msg: "License: {{ reg_info.registration.type }}, State: {{ reg_info.registration.state }}"

- name: Check license is valid
  stevefulme1.unraid.registration_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: reg_info

- name: Assert license is registered
  ansible.builtin.assert:
    that:
      - reg_info.registration.state == "registered"
    fail_msg: "Unraid server is not properly registered"
"""

RETURN = r"""
registration:
  description: License and registration details.
  returned: always
  type: dict
  contains:
    type:
      description: License type (e.g. Basic, Plus, Pro, Trial).
      type: str
    state:
      description: Registration state (e.g. registered, expired, trial).
      type: str
    expiration:
      description:
        - License expiration date.
        - May be null for lifetime licenses.
      type: str
  sample:
    type: "Pro"
    state: "registered"
    expiration: null
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_REGISTRATION = """
{
    registration {
        type
        state
        expiration
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = get_client(module)

    try:
        data = client.query(QUERY_REGISTRATION)
        registration = data.get("registration", {})
    except UnraidError as exc:
        module.fail_json(msg="Failed to query registration info: %s" % str(exc))

    module.exit_json(changed=False, registration=registration)


if __name__ == "__main__":
    main()
