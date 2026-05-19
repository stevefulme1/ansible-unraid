#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing Unraid SSO/OIDC users."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: sso_user
short_description: Manage SSO/OIDC users on Unraid
version_added: "1.0.0"
description:
  - Add or remove SSO (Single Sign-On) / OIDC users on an Unraid server.
  - Uses the C(unraid-api) CLI commands C(sso add-user) and C(sso remove-user)
    executed via SSH on the Unraid host.
  - SSO/OIDC integration allows users to authenticate with external identity
    providers (e.g. Google, GitHub, or custom OIDC providers) configured in
    the Unraid Connect settings.
  - The module validates API connectivity via GraphQL before executing SSH
    commands.
  - Requires Unraid 7.2 or later with SSO/OIDC configured.
options:
  email:
    description:
      - Email address of the SSO/OIDC user to manage.
      - Must match the email address from the identity provider.
    type: str
    required: true
  state:
    description:
      - Desired state of the SSO user.
      - V(present) adds the user if not already registered.
      - V(absent) removes the user.
    type: str
    choices:
      - present
      - absent
    default: present
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - This module requires SSH access to the Unraid host to execute
    C(unraid-api) CLI commands.
  - SSO/OIDC must be configured in Unraid Connect settings before users
    can be added.
  - The C(unraid-api) CLI tool must be available on the Unraid host
    (included with Unraid 7.0+).
  - There is no GraphQL mutation for SSO user management; this module
    relies entirely on SSH and the C(unraid-api) CLI.
"""

EXAMPLES = r"""
- name: Add an SSO user
  stevefulme1.unraid.sso_user:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    email: user@example.com
    state: present

- name: Remove an SSO user
  stevefulme1.unraid.sso_user:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    email: user@example.com
    state: absent

- name: Add multiple SSO users
  stevefulme1.unraid.sso_user:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    email: "{{ item }}"
    state: present
  loop:
    - alice@example.com
    - bob@example.com
"""

RETURN = r"""
email:
  description: The email address of the SSO user.
  returned: always
  type: str
  sample: user@example.com
state:
  description: The resulting state of the SSO user.
  returned: always
  type: str
  sample: present
command:
  description: The CLI command that was executed.
  returned: when changed
  type: str
  sample: "unraid-api sso add-user user@example.com"
msg:
  description: Human-readable result message.
  returned: always
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        email=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    email = module.params["email"]
    state = module.params["state"]

    # Validate API connectivity
    client = get_client(module)
    try:
        client.query("{ info { os { hostname } } }")
    except UnraidError as exc:
        module.fail_json(msg="Failed to connect to Unraid API: %s" % str(exc))

    result = dict(
        changed=False,
        email=email,
        state=state,
    )

    if state == "present":
        cmd = ["unraid-api", "sso", "add-user", email]

        if module.check_mode:
            result["changed"] = True
            result["command"] = " ".join(cmd)
            result["msg"] = "Would add SSO user '%s'." % email
            module.exit_json(**result)

        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            # Check if user already exists (common error message)
            if "already" in (stdout + stderr).lower():
                result["msg"] = "SSO user '%s' already exists." % email
                module.exit_json(**result)
            module.fail_json(
                msg="Failed to add SSO user '%s': %s"
                % (email, (stderr or stdout).strip())
            )

        result["changed"] = True
        result["command"] = " ".join(cmd)
        result["msg"] = "SSO user '%s' added successfully." % email

    elif state == "absent":
        cmd = ["unraid-api", "sso", "remove-user", email]

        if module.check_mode:
            result["changed"] = True
            result["command"] = " ".join(cmd)
            result["msg"] = "Would remove SSO user '%s'." % email
            module.exit_json(**result)

        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            # Check if user does not exist
            if "not found" in (stdout + stderr).lower() or "does not exist" in (stdout + stderr).lower():
                result["msg"] = "SSO user '%s' does not exist." % email
                module.exit_json(**result)
            module.fail_json(
                msg="Failed to remove SSO user '%s': %s"
                % (email, (stderr or stdout).strip())
            )

        result["changed"] = True
        result["command"] = " ".join(cmd)
        result["msg"] = "SSO user '%s' removed successfully." % email

    module.exit_json(**result)


if __name__ == "__main__":
    main()
