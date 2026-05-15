#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: system
short_description: Reboot or shut down an Unraid server
description:
    - Issue a reboot or shutdown command to the Unraid server.
    - This is a fire-and-forget operation. The module always reports
      C(changed=true) because the API does not return pre-action state.
    - In check mode, the module reports what would happen without
      sending the command.
    - The connection to the server will be lost after the command
      executes. Use C(wait_for_connection) in a subsequent task if
      you need to wait for the server to come back after a reboot.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    state:
        description:
            - The system action to perform.
            - C(rebooted) restarts the Unraid server.
            - C(shutdown) powers off the Unraid server.
        type: str
        required: true
        choices:
            - rebooted
            - shutdown
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Reboot the Unraid server
  stevefulme1.unraid.system:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    state: rebooted

- name: Shut down the Unraid server
  stevefulme1.unraid.system:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    state: shutdown

- name: Reboot and wait for return
  block:
    - name: Reboot server
      stevefulme1.unraid.system:
        api_url: https://tower.local
        api_key: "{{ unraid_api_key }}"
        state: rebooted

    - name: Wait for server to come back
      ansible.builtin.wait_for_connection:
        delay: 30
        timeout: 300
"""

RETURN = r"""
action:
    description: The action that was performed.
    returned: always
    type: str
    sample: reboot
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_REBOOT = """
mutation {
    system {
        reboot
    }
}
"""

MUTATION_SHUTDOWN = """
mutation {
    system {
        shutdown
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        state=dict(type="str", required=True, choices=["rebooted", "shutdown"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    desired_state = module.params["state"]
    action = "reboot" if desired_state == "rebooted" else "shutdown"

    if module.check_mode:
        module.exit_json(
            changed=True,
            action=action,
            msg=f"Would {action} the Unraid server",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    mutation = MUTATION_REBOOT if desired_state == "rebooted" else MUTATION_SHUTDOWN

    try:
        client.mutate(mutation)
    except UnraidError as exc:
        # Connection errors are expected after reboot/shutdown is issued.
        # If the error is a connection failure, the command likely succeeded.
        error_msg = str(exc).lower()
        if any(term in error_msg for term in ("connection", "timeout", "refused", "reset")):
            module.exit_json(
                changed=True,
                action=action,
                msg=f"Server {action} initiated (connection lost as expected)",
            )
        module.fail_json(msg=f"Failed to {action} server: {exc}")

    module.exit_json(
        changed=True,
        action=action,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
