#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for querying Unraid Connect status."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connect_info
short_description: Query Unraid Connect status
version_added: "1.0.0"
description:
  - Retrieve the current Unraid Connect status and configuration from an
    Unraid server via the GraphQL API.
  - Unraid Connect provides remote access, flash backup, dynamic DNS, and
    other cloud-connected features.
  - Returns the connection status, remote access state, and related
    configuration details.
  - This is an info module and never changes state on the target.
  - Requires Unraid 7.2 or later.

options:
    limit:
        description:
            - Maximum number of results to return.
        type: int
        default: 100
    offset:
        description:
            - Number of results to skip for pagination.
        type: int
        default: 0
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - This module is read-only. To configure Unraid Connect settings, use
    the M(stevefulme1.unraid.connect_config) module.
  - Unraid Connect requires an active Unraid.net account and the server
    to be signed in at C(Settings > Management Access > Unraid Connect).
"""

EXAMPLES = r"""
- name: Get Unraid Connect status
  stevefulme1.unraid.connect_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: connect

- name: Display connect status
  ansible.builtin.debug:
    msg: "Connect status: {{ connect.connect.status | default('unknown') }}"

- name: Check remote access is available
  stevefulme1.unraid.connect_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: connect

- name: Report on connect configuration
  ansible.builtin.debug:
    var: connect.connect
"""

RETURN = r"""
connect:
  description: Unraid Connect status and configuration details.
  returned: always
  type: dict
  contains:
    status:
      description: Connection status (e.g. connected, disconnected).
      type: str
    remoteAccess:
      description: Remote access status.
      type: str
    dynamicDns:
      description: Dynamic DNS configuration state.
      type: str
    flashBackup:
      description: Flash backup status.
      type: str
  sample:
    status: "connected"
    remoteAccess: "enabled"
    dynamicDns: "enabled"
    flashBackup: "enabled"
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


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = get_client(module)

    try:
        data = client.query(QUERY_CONNECT)
        connect = data.get("connect", {})
    except UnraidError as exc:
        module.fail_json(msg="Failed to query Connect status: %s" % str(exc))

    module.exit_json(changed=False, connect=connect)


if __name__ == "__main__":
    main()
