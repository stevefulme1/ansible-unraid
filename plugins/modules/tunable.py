#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: tunable
short_description: Manage Unraid system tunables
description:
    - Manage system tunables (sysctl parameters) on an Unraid server.
    - Supports setting, updating, and removing tunables via the Unraid
      GraphQL API settings mutation.
    - If the GraphQL API does not expose a tunable management mutation,
      the module falls back to SSH to read and write C(/boot/config/sysctl.conf)
      and apply settings with C(sysctl -w).
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    name:
        description:
            - Name of the sysctl tunable parameter.
            - Uses standard sysctl dotted notation
              (e.g., C(vm.dirty_ratio), C(net.core.rmem_max)).
        type: str
        required: true
    value:
        description:
            - Desired value for the tunable parameter.
            - Required when I(state=present).
        type: str
        required: false
    state:
        description:
            - Desired state of the tunable.
            - C(present) ensures the tunable is set to the specified value.
            - C(absent) removes the tunable, reverting to the system default.
        type: str
        required: true
        choices:
            - present
            - absent
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - Changes to tunables take effect immediately via C(sysctl -w) but
      are also persisted to C(/boot/config/sysctl.conf) for survival
      across reboots.
    - The Unraid GraphQL API may not expose tunable management in all
      versions. The module will fall back to SSH-based management when
      the API mutation is unavailable.
    - Use caution when modifying kernel parameters. Incorrect values
      can impact system stability.
"""

EXAMPLES = r"""
- name: Set vm.dirty_ratio to 10
  stevefulme1.unraid.tunable:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    name: vm.dirty_ratio
    value: "10"
    state: present

- name: Increase network buffer size
  stevefulme1.unraid.tunable:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: net.core.rmem_max
    value: "16777216"
    state: present

- name: Remove custom tunable
  stevefulme1.unraid.tunable:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: vm.dirty_ratio
    state: absent
"""

RETURN = r"""
name:
    description: The tunable parameter name.
    returned: always
    type: str
    sample: vm.dirty_ratio
value:
    description: The current value of the tunable after the operation.
    returned: when state is present
    type: str
    sample: "10"
previous_value:
    description: The value of the tunable before the operation.
    returned: when changed
    type: str
    sample: "20"
method:
    description: Method used for the operation (graphql or ssh_fallback).
    returned: always
    type: str
    sample: ssh_fallback
msg:
    description: Human-readable result message.
    returned: always
    type: str
    sample: "Tunable 'vm.dirty_ratio' set to '10'."
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_SET_TUNABLE = """
mutation SetTunable($name: String!, $value: String!) {
    setTunable(name: $name, value: $value)
}
"""

MUTATION_REMOVE_TUNABLE = """
mutation RemoveTunable($name: String!) {
    removeTunable(name: $name)
}
"""

SYSCTL_CONF = "/boot/config/sysctl.conf"


def get_ssh_host(module):
    """Extract hostname from api_url for SSH connection."""
    return module.params["api_url"].split("//")[-1].split(":")[0].split("/")[0]


def ssh_get_current_value(module, host, name):
    """Read the current sysctl value via SSH."""
    rc, stdout, stderr = module.run_command(
        ["ssh", f"root@{host}", "sysctl", "-n", name]
    )
    if rc == 0:
        return stdout.strip()
    return None


def ssh_set_tunable(module, host, name, value):
    """Set a sysctl value immediately and persist it."""
    # Apply immediately
    rc, stdout, stderr = module.run_command(
        ["ssh", f"root@{host}", "sysctl", "-w", f"{name}={value}"]
    )
    if rc != 0:
        module.fail_json(
            msg=f"Failed to set tunable '{name}': {stderr.strip()}",
            name=name,
            value=value,
        )

    # Persist to sysctl.conf
    # Read current config, update or add the entry
    rc, conf_content, stderr = module.run_command(
        ["ssh", f"root@{host}", "cat", SYSCTL_CONF]
    )
    if rc != 0:
        conf_content = ""

    lines = conf_content.strip().split("\n") if conf_content.strip() else []
    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{name}=") or stripped.startswith(f"{name} ="):
            new_lines.append(f"{name}={value}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"{name}={value}")

    new_content = "\n".join(new_lines) + "\n"
    module.run_command(
        ["ssh", f"root@{host}", "tee", SYSCTL_CONF],
        data=new_content,
    )


def ssh_remove_tunable(module, host, name):
    """Remove a tunable from sysctl.conf."""
    rc, conf_content, stderr = module.run_command(
        ["ssh", f"root@{host}", "cat", SYSCTL_CONF]
    )
    if rc != 0:
        return

    lines = conf_content.strip().split("\n") if conf_content.strip() else []
    new_lines = [
        line for line in lines
        if not line.strip().startswith(f"{name}=")
        and not line.strip().startswith(f"{name} =")
    ]

    new_content = "\n".join(new_lines) + "\n" if new_lines else ""
    module.run_command(
        ["ssh", f"root@{host}", "tee", SYSCTL_CONF],
        data=new_content,
    )


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        value=dict(type="str", required=False, default=None),
        state=dict(type="str", required=True, choices=["present", "absent"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["value"]),
        ],
    )

    name = module.params["name"]
    value = module.params["value"]
    state = module.params["state"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Try GraphQL first
    if state == "present":
        try:
            client.mutate(
                MUTATION_SET_TUNABLE,
                variables={"name": name, "value": value},
            )
            module.exit_json(
                changed=True,
                name=name,
                value=value,
                method="graphql",
                msg=f"Tunable '{name}' set to '{value}'.",
            )
        except UnraidError:
            pass
    else:
        try:
            client.mutate(
                MUTATION_REMOVE_TUNABLE,
                variables={"name": name},
            )
            module.exit_json(
                changed=True,
                name=name,
                method="graphql",
                msg=f"Tunable '{name}' removed.",
            )
        except UnraidError:
            pass

    # SSH fallback
    host = get_ssh_host(module)
    current_value = ssh_get_current_value(module, host, name)

    if state == "present":
        if current_value == value:
            module.exit_json(
                changed=False,
                name=name,
                value=value,
                method="ssh_fallback",
                msg=f"Tunable '{name}' is already set to '{value}'.",
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                name=name,
                value=value,
                previous_value=current_value,
                method="check_mode",
                msg=f"Would set tunable '{name}' to '{value}'.",
            )

        ssh_set_tunable(module, host, name, value)
        module.exit_json(
            changed=True,
            name=name,
            value=value,
            previous_value=current_value,
            method="ssh_fallback",
            msg=f"Tunable '{name}' set to '{value}'.",
        )

    if state == "absent":
        if module.check_mode:
            module.exit_json(
                changed=True,
                name=name,
                method="check_mode",
                msg=f"Would remove tunable '{name}'.",
            )

        ssh_remove_tunable(module, host, name)
        module.exit_json(
            changed=True,
            name=name,
            previous_value=current_value,
            method="ssh_fallback",
            msg=f"Tunable '{name}' removed.",
        )


def main():
    run_module()


if __name__ == "__main__":
    main()
