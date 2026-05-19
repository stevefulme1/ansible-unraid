#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing SSH authorized keys on Unraid."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: ssh_key
short_description: Manage SSH authorized keys on Unraid
version_added: "1.0.0"
description:
  - Add or remove SSH public keys from the authorized_keys file on an
    Unraid server.
  - On Unraid, the persistent SSH authorized_keys file for root is located
    at C(/boot/config/ssh/root/.ssh/authorized_keys). This path survives
    reboots because it resides on the boot USB device.
  - This module connects to the Unraid GraphQL API to validate connectivity,
    then uses SSH commands to manage the authorized_keys file directly.
  - The standard C(/root/.ssh/authorized_keys) is a symlink or copy of the
    persistent file on Unraid.
options:
  key:
    description:
      - The SSH public key string to manage.
      - Must be a valid SSH public key (e.g. C(ssh-rsa AAAA... user@host)
        or C(ssh-ed25519 AAAA... user@host)).
      - The full key line including the key type, key data, and optional
        comment.
    type: str
    required: true
  state:
    description:
      - Whether the key should be present or absent.
      - V(present) adds the key if it does not already exist.
      - V(absent) removes the key if it exists.
    type: str
    choices:
      - present
      - absent
    default: present
  user:
    description:
      - The user account to manage SSH keys for.
      - On Unraid, the primary user is C(root).
      - The authorized_keys file path is constructed as
        C(/boot/config/ssh/<user>/.ssh/authorized_keys).
    type: str
    default: root
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - This module requires SSH access to the Unraid host to manage
    authorized_keys files.
  - The persistent authorized_keys path on Unraid is
    C(/boot/config/ssh/root/.ssh/authorized_keys), not the standard
    C(/root/.ssh/authorized_keys).
  - Keys are matched by their key data (type + base64 portion), not by
    the comment field.
  - Consider using C(ansible.posix.authorized_key) as an alternative if
    you do not need Unraid-specific persistent path handling.
"""

EXAMPLES = r"""
- name: Add an SSH key for root
  stevefulme1.unraid.ssh_key:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG... user@workstation"
    state: present

- name: Remove an SSH key
  stevefulme1.unraid.ssh_key:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    key: "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB... oldkey@host"
    state: absent

- name: Add key for a specific user
  stevefulme1.unraid.ssh_key:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG... backup@server"
    user: backupuser
    state: present
"""

RETURN = r"""
key:
  description: The SSH public key that was managed.
  returned: always
  type: str
  sample: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG... user@workstation"
path:
  description: The authorized_keys file path that was modified.
  returned: always
  type: str
  sample: "/boot/config/ssh/root/.ssh/authorized_keys"
state:
  description: The resulting state of the key.
  returned: always
  type: str
  sample: present
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


def get_key_id(key_string):
    """Extract the key type and key data for comparison (ignore comment)."""
    parts = key_string.strip().split()
    if len(parts) >= 2:
        return parts[0] + " " + parts[1]
    return key_string.strip()


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        key=dict(type="str", required=True, no_log=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        user=dict(type="str", default="root"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    key = module.params["key"].strip()
    state = module.params["state"]
    user = module.params["user"]

    # Validate API connectivity
    client = get_client(module)
    try:
        client.query("{ info { os { hostname } } }")
    except UnraidError as exc:
        module.fail_json(msg="Failed to connect to Unraid API: %s" % str(exc))

    auth_keys_path = "/boot/config/ssh/%s/.ssh/authorized_keys" % user
    key_id = get_key_id(key)

    result = dict(
        changed=False,
        key=key,
        path=auth_keys_path,
        state=state,
    )

    # Ensure parent directory exists
    mkdir_cmd = "mkdir -p /boot/config/ssh/%s/.ssh" % user
    module.run_command(mkdir_cmd)

    # Read current authorized_keys
    rc, stdout, stderr = module.run_command("cat %s 2>/dev/null" % auth_keys_path)
    current_keys = stdout.strip().splitlines() if rc == 0 else []

    # Check if key already exists (match on type + key data)
    key_found = False
    for existing_key in current_keys:
        if get_key_id(existing_key) == key_id:
            key_found = True
            break

    if state == "present":
        if key_found:
            result["msg"] = "SSH key already present in %s." % auth_keys_path
            module.exit_json(**result)

        result["changed"] = True
        if module.check_mode:
            result["msg"] = "Would add SSH key to %s." % auth_keys_path
            module.exit_json(**result)

        # Append the key using safe list-form command with stdin
        rc, stdout, stderr = module.run_command(
            ["tee", "-a", auth_keys_path],
            data=key + "\n",
        )
        if rc != 0:
            module.fail_json(
                msg="Failed to add SSH key: %s" % stderr.strip()
            )

        # Set permissions
        module.run_command("chmod 600 %s" % auth_keys_path)
        result["msg"] = "SSH key added to %s." % auth_keys_path

    elif state == "absent":
        if not key_found:
            result["msg"] = "SSH key not found in %s." % auth_keys_path
            module.exit_json(**result)

        result["changed"] = True
        if module.check_mode:
            result["msg"] = "Would remove SSH key from %s." % auth_keys_path
            module.exit_json(**result)

        # Remove the key by filtering it out
        new_keys = [
            k for k in current_keys if get_key_id(k) != key_id
        ]
        new_content = "\n".join(new_keys) + "\n" if new_keys else ""

        rc, stdout, stderr = module.run_command(
            ["tee", auth_keys_path],
            data=new_content,
        )
        if rc != 0:
            module.fail_json(
                msg="Failed to remove SSH key: %s" % stderr.strip()
            )

        module.run_command("chmod 600 %s" % auth_keys_path)
        result["msg"] = "SSH key removed from %s." % auth_keys_path

    module.exit_json(**result)


if __name__ == "__main__":
    main()
