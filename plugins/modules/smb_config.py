#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing global SMB/Samba configuration on Unraid."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: smb_config
short_description: Manage global SMB/Samba configuration on Unraid
version_added: "1.0.0"
description:
  - Query and configure global SMB (Samba) settings on an Unraid server.
  - This module queries the current SMB configuration via the GraphQL API
    and attempts to apply changes through GraphQL mutations when available.
  - If mutations are not supported in the current API version, the module
    provides guidance on configuring SMB via the Unraid WebGUI or by
    editing configuration files directly.
  - Global SMB settings affect all SMB-exported shares on the server.
  - The Unraid SMB extra configuration file is located at
    C(/boot/config/smb-extra.conf) for advanced Samba directives.
  - Requires Unraid 7.2 or later.
options:
  workgroup:
    description:
      - The SMB workgroup/domain name.
      - Corresponds to the C(workgroup) directive in C(smb.conf).
    type: str
  local_master:
    description:
      - Whether this server should be a local master browser.
      - Corresponds to the C(local master) directive in C(smb.conf).
    type: bool
  enhanced_security:
    description:
      - Enable enhanced SMB security settings.
      - When enabled, enforces SMB signing and restricts older protocol
        versions.
    type: bool
  hide_dot_files:
    description:
      - Whether to hide files and directories starting with a dot.
      - Corresponds to the C(hide dot files) directive in C(smb.conf).
    type: bool
  fruit_enabled:
    description:
      - Enable Apple (macOS) Time Machine and Finder compatibility via
        the C(vfs_fruit) Samba module.
      - Improves interoperability with macOS clients.
    type: bool
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - At least one configuration parameter must be provided.
  - The Unraid GraphQL API may not support all SMB configuration mutations
    in every version. When mutations are unavailable, configure settings
    through the Unraid WebGUI at C(Settings > SMB) or edit configuration
    files directly.
  - For advanced Samba configuration directives, edit the extra config file
    at C(/boot/config/smb-extra.conf) via SSH or the
    C(ansible.builtin.template) module.
  - Changes to SMB configuration may require a service restart to take
    effect. The module does not automatically restart the SMB service.
  - The main Samba configuration is managed by Unraid at
    C(/etc/samba/smb.conf) and is regenerated from Unraid settings. Do not
    edit it directly; use C(smb-extra.conf) for custom directives.
"""

EXAMPLES = r"""
- name: Set SMB workgroup
  stevefulme1.unraid.smb_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    workgroup: MYWORKGROUP

- name: Enable enhanced security
  stevefulme1.unraid.smb_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    enhanced_security: true

- name: Configure multiple SMB settings
  stevefulme1.unraid.smb_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    workgroup: HOMENET
    local_master: true
    hide_dot_files: true
    fruit_enabled: true

- name: Disable local master browser
  stevefulme1.unraid.smb_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    local_master: false
"""

RETURN = r"""
config:
  description: Current SMB configuration after any changes.
  returned: success
  type: dict
  contains:
    workgroup:
      description: SMB workgroup name.
      type: str
    localMaster:
      description: Local master browser setting.
      type: bool
    enhancedSecurity:
      description: Enhanced security setting.
      type: bool
    hideDotFiles:
      description: Hide dot files setting.
      type: bool
    fruitEnabled:
      description: Apple/macOS compatibility (vfs_fruit) setting.
      type: bool
  sample:
    workgroup: "WORKGROUP"
    localMaster: true
    enhancedSecurity: false
    hideDotFiles: true
    fruitEnabled: true
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

QUERY_SMB_CONFIG = """
{
    smbConfig {
        workgroup
        localMaster
        enhancedSecurity
        hideDotFiles
        fruitEnabled
    }
}
"""

MUTATION_SMB_CONFIG = """
mutation($input: SmbConfigInput!) {
    setSmbConfig(input: $input) {
        workgroup
        localMaster
        enhancedSecurity
        hideDotFiles
        fruitEnabled
    }
}
"""

# Mapping from module param names to GraphQL field names
PARAM_TO_FIELD = {
    "workgroup": "workgroup",
    "local_master": "localMaster",
    "enhanced_security": "enhancedSecurity",
    "hide_dot_files": "hideDotFiles",
    "fruit_enabled": "fruitEnabled",
}


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        workgroup=dict(type="str"),
        local_master=dict(type="bool"),
        enhanced_security=dict(type="bool"),
        hide_dot_files=dict(type="bool"),
        fruit_enabled=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[
            ["workgroup", "local_master", "enhanced_security", "hide_dot_files", "fruit_enabled"],
        ],
        supports_check_mode=True,
    )

    client = get_client(module)
    result = dict(changed=False)

    # Query current config
    current_config = {}
    try:
        data = client.query(QUERY_SMB_CONFIG)
        current_config = data.get("smbConfig", {})
    except UnraidError:
        # API may not support this query; proceed with empty config
        pass

    # Build desired changes
    changes = {}
    for param_name, field_name in PARAM_TO_FIELD.items():
        value = module.params.get(param_name)
        if value is not None:
            current_value = current_config.get(field_name)
            if current_value != value:
                changes[field_name] = value

    if not changes:
        result["config"] = current_config
        result["msg"] = "SMB configuration is already in the desired state."
        module.exit_json(**result)

    result["changed"] = True
    if module.check_mode:
        result["config"] = current_config
        result["msg"] = "Would update SMB settings: %s." % ", ".join(changes.keys())
        module.exit_json(**result)

    # Apply changes via mutation
    try:
        data = client.mutate(MUTATION_SMB_CONFIG, variables={"input": changes})
        updated_config = data.get("setSmbConfig", {})
        result["config"] = updated_config if updated_config else current_config
        result["msg"] = "SMB configuration updated: %s." % ", ".join(changes.keys())
    except UnraidError as exc:
        error_msg = str(exc)
        result["config"] = current_config
        result["msg"] = (
            "SMB configuration mutation is not available in this Unraid API "
            "version (%s). Configure SMB settings through the Unraid WebGUI "
            "at Settings > SMB, or edit /boot/config/smb-extra.conf via SSH "
            "for advanced directives." % error_msg
        )
        # Still report changed=True since we could not verify
        result["changed"] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
