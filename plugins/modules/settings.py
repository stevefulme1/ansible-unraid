#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: settings
short_description: Update Unraid system settings
description:
    - Update system settings on an Unraid server via the GraphQL API.
    - Accepts a dictionary of settings key-value pairs and applies them
      using the C(updateSettings) mutation.
    - Always reports C(changed=true) because the settings API does not
      return a diff of previous values.
    - In check mode, the module reports what would happen without
      applying changes.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    settings:
        description:
            - Dictionary of settings to apply.
            - Keys and values correspond to the Unraid settings schema.
            - Consult the Unraid GraphQL API documentation or introspect
              the schema for valid keys.
        type: dict
        required: true
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Update share settings
  stevefulme1.unraid.settings:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    settings:
      shareSMBEnabled: true
      shareNFSEnabled: false

- name: Set notification preferences
  stevefulme1.unraid.settings:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    settings:
      notificationsEmail: admin@example.com
      notificationsLevel: warning
"""

RETURN = r"""
settings:
    description: The settings that were applied.
    returned: always
    type: dict
    sample:
        shareSMBEnabled: true
        shareNFSEnabled: false
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_UPDATE_SETTINGS = """
mutation UpdateSettings($input: SettingsInput!) {
    updateSettings(input: $input)
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        settings=dict(type="dict", required=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    settings = module.params["settings"]

    if not settings:
        module.fail_json(msg="The 'settings' parameter must not be empty")

    if module.check_mode:
        module.exit_json(
            changed=True,
            settings=settings,
            msg="Would apply settings update",
        )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        client.mutate(
            MUTATION_UPDATE_SETTINGS,
            variables={"input": settings},
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to update settings: {exc}")

    module.exit_json(
        changed=True,
        settings=settings,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
