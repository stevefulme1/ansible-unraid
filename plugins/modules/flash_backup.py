#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: flash_backup
short_description: Trigger an Unraid USB flash backup
description:
    - Initiates a backup of the Unraid USB flash drive configuration.
    - Always reports C(changed=true) because the backup is a one-shot
      operation with no idempotent state to compare.
    - In check mode, the module reports what would happen without
      triggering the backup.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Trigger a flash backup
  stevefulme1.unraid.flash_backup:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false

- name: Backup flash drive on schedule
  stevefulme1.unraid.flash_backup:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  tags: backup
"""

RETURN = r"""
msg:
    description: Status message about the backup operation.
    returned: always
    type: str
    sample: Flash backup initiated successfully
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_FLASH_BACKUP = """
mutation {
    initiateFlashBackup
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
            msg="Would initiate flash backup",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        client.mutate(MUTATION_FLASH_BACKUP)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to initiate flash backup: {exc}")

    module.exit_json(
        changed=True,
        msg="Flash backup initiated successfully",
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
