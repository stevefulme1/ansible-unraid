#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for configuring Unraid Connect settings."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connect_config
short_description: Configure Unraid Connect settings
version_added: "1.0.0"
description:
  - Configure Unraid Connect features including remote access and dynamic
    DNS on an Unraid server via the GraphQL API.
  - Unraid Connect provides cloud-connected features such as remote access
    (WAN access to the Unraid WebGUI), dynamic DNS, and flash backup.
  - This module attempts to use GraphQL mutations to apply settings. If the
    mutations are not available in the current API version, it provides
    guidance on configuring settings through the WebGUI.
  - Requires Unraid 7.2 or later with an active Unraid Connect account.
options:
  remote_access:
    description:
      - Enable or disable remote access via Unraid Connect.
      - V(enabled) allows WAN access to the Unraid WebGUI through the
        Unraid Connect relay.
      - V(disabled) restricts access to the local network only.
    type: str
    choices:
      - enabled
      - disabled
  dynamic_dns:
    description:
      - Enable or disable dynamic DNS provided by Unraid Connect.
      - When enabled, Unraid automatically maintains a DNS record for
        the server at C(<hash>.unraid.net).
    type: bool
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - Unraid Connect must be configured and the server signed in before
    these settings can be modified.
  - Remote access uses Unraid's WireGuard-based relay and does not
    require port forwarding.
  - If the GraphQL mutations for Connect configuration are not available,
    configure these settings through the Unraid WebGUI at
    C(Settings > Management Access > Unraid Connect).
  - At least one of I(remote_access) or I(dynamic_dns) must be provided.
"""

EXAMPLES = r"""
- name: Enable remote access
  stevefulme1.unraid.connect_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    remote_access: enabled

- name: Disable remote access
  stevefulme1.unraid.connect_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    remote_access: disabled

- name: Enable dynamic DNS
  stevefulme1.unraid.connect_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    dynamic_dns: true

- name: Configure both settings
  stevefulme1.unraid.connect_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    remote_access: enabled
    dynamic_dns: true
"""

RETURN = r"""
connect:
  description: Current Unraid Connect status after configuration change.
  returned: success
  type: dict
  contains:
    status:
      description: Connection status.
      type: str
    remoteAccess:
      description: Remote access state.
      type: str
    dynamicDns:
      description: Dynamic DNS state.
      type: str
  sample:
    status: "connected"
    remoteAccess: "enabled"
    dynamicDns: "enabled"
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

QUERY_CONNECT = """
{
    connect {
        status
        remoteAccess
        dynamicDns
        flashBackup
    }
}
"""

MUTATION_REMOTE_ACCESS = """
mutation($enabled: Boolean!) {
    setRemoteAccess(enabled: $enabled)
}
"""

MUTATION_DYNAMIC_DNS = """
mutation($enabled: Boolean!) {
    setDynamicDns(enabled: $enabled)
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        remote_access=dict(type="str", choices=["enabled", "disabled"]),
        dynamic_dns=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["remote_access", "dynamic_dns"]],
        supports_check_mode=True,
    )

    remote_access = module.params.get("remote_access")
    dynamic_dns = module.params.get("dynamic_dns")

    client = get_client(module)
    result = dict(changed=False)

    # Query current state
    try:
        data = client.query(QUERY_CONNECT)
        connect = data.get("connect", {})
    except UnraidError as exc:
        module.fail_json(msg="Failed to query Connect status: %s" % str(exc))

    changes_needed = []
    mutations_failed = []

    # Check remote access
    if remote_access is not None:
        current_ra = (connect.get("remoteAccess") or "").lower()
        desired_ra = remote_access.lower()
        if current_ra != desired_ra:
            changes_needed.append("remote_access")

    # Check dynamic DNS
    if dynamic_dns is not None:
        current_ddns = (connect.get("dynamicDns") or "").lower()
        desired_ddns = "enabled" if dynamic_dns else "disabled"
        if current_ddns != desired_ddns:
            changes_needed.append("dynamic_dns")

    if not changes_needed:
        result["connect"] = connect
        result["msg"] = "Unraid Connect settings are already in the desired state."
        module.exit_json(**result)

    result["changed"] = True
    if module.check_mode:
        result["connect"] = connect
        result["msg"] = "Would update Unraid Connect settings: %s." % ", ".join(
            changes_needed
        )
        module.exit_json(**result)

    # Apply remote access change
    if "remote_access" in changes_needed:
        enabled = remote_access == "enabled"
        try:
            client.mutate(MUTATION_REMOTE_ACCESS, variables={"enabled": enabled})
        except UnraidError as exc:
            mutations_failed.append(
                "remote_access: %s" % str(exc)
            )

    # Apply dynamic DNS change
    if "dynamic_dns" in changes_needed:
        try:
            client.mutate(MUTATION_DYNAMIC_DNS, variables={"enabled": dynamic_dns})
        except UnraidError as exc:
            mutations_failed.append(
                "dynamic_dns: %s" % str(exc)
            )

    if mutations_failed:
        result["msg"] = (
            "Some Connect settings could not be applied via the API: %s. "
            "Configure these settings through the Unraid WebGUI at "
            "Settings > Management Access > Unraid Connect."
            % "; ".join(mutations_failed)
        )
    else:
        result["msg"] = "Unraid Connect settings updated: %s." % ", ".join(
            changes_needed
        )

    # Re-query current state
    try:
        data = client.query(QUERY_CONNECT)
        connect = data.get("connect", {})
    except UnraidError:
        pass

    result["connect"] = connect
    module.exit_json(**result)


if __name__ == "__main__":
    main()
