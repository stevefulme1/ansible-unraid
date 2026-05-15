#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cache_mover
short_description: Trigger the Unraid cache mover
description:
    - Trigger the Unraid mover to move files from the cache pool(s)
      to the array.
    - This is a fire-and-forget action. The mover process runs
      asynchronously on the Unraid server.
    - The module always reports C(changed=true) because the mover
      trigger is an imperative action with no idempotent check.
    - The mover follows the per-share cache settings configured in
      the Unraid web UI to determine which files to move.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - The mover runs in the background. The module returns immediately
      after triggering the mover.
    - Files are moved according to per-share mover settings configured
      in the Unraid web UI.
    - Running the mover when no files need to be moved is harmless.
"""

EXAMPLES = r"""
- name: Trigger the cache mover
  stevefulme1.unraid.cache_mover:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false

- name: Move cache files after large download completes
  block:
    - name: Wait for download to finish
      ansible.builtin.wait_for:
        path: /mnt/cache/downloads/large_file.iso
        state: present

    - name: Trigger mover to move files to array
      stevefulme1.unraid.cache_mover:
        api_url: https://tower.local
        api_key: "{{ unraid_api_key }}"
"""

RETURN = r"""
msg:
    description: Human-readable result message.
    returned: always
    type: str
    sample: "Mover triggered successfully."
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_TRIGGER_MOVER = """
mutation {
    triggerMover
}
"""


def run_module():
    argument_spec = unraid_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(
            changed=True,
            msg="Would trigger the cache mover.",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        client.mutate(MUTATION_TRIGGER_MOVER)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to trigger mover: {exc}")

    module.exit_json(
        changed=True,
        msg="Mover triggered successfully.",
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
