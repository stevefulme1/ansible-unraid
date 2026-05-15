#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: syslog_config
short_description: Configure syslog settings on Unraid
description:
    - Configure remote syslog forwarding on an Unraid server via the
      GraphQL API C(updateSettings) mutation.
    - Allows setting a remote syslog server, port, and protocol for
      centralized log collection.
    - Compares current settings against desired state and only applies
      changes when necessary.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    remote_server:
        description:
            - Hostname or IP address of the remote syslog server.
            - Set to an empty string to disable remote syslog forwarding.
        type: str
    remote_port:
        description:
            - Port number for the remote syslog server.
        type: int
    protocol:
        description:
            - Transport protocol to use for syslog forwarding.
        type: str
        choices:
            - udp
            - tcp
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Forward syslog to remote server via UDP
  stevefulme1.unraid.syslog_config:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    remote_server: syslog.example.com
    remote_port: 514
    protocol: udp

- name: Forward syslog via TCP on a custom port
  stevefulme1.unraid.syslog_config:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    remote_server: 192.168.1.50
    remote_port: 1514
    protocol: tcp

- name: Disable remote syslog
  stevefulme1.unraid.syslog_config:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    remote_server: ""
"""

RETURN = r"""
syslog:
    description: The syslog configuration after changes.
    returned: success
    type: dict
    contains:
        remote_server:
            description: Remote syslog server address.
            type: str
        remote_port:
            description: Remote syslog port.
            type: int
        protocol:
            description: Transport protocol (udp or tcp).
            type: str
    sample:
        remote_server: syslog.example.com
        remote_port: 514
        protocol: udp
diff:
    description: Configuration differences that were applied.
    returned: changed
    type: dict
    contains:
        before:
            description: Previous configuration values.
            type: dict
        after:
            description: New configuration values.
            type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_SYSLOG = """
{
    vars {
        syslogServer
        syslogPort
        syslogProtocol
    }
}
"""

MUTATION_UPDATE_SETTINGS = """
mutation UpdateSettings($input: SettingsInput!) {
    updateSettings(input: $input)
}
"""

# Maps module params to GraphQL settings field names
PARAM_TO_SETTING = {
    "remote_server": "syslogServer",
    "remote_port": "syslogPort",
    "protocol": "syslogProtocol",
}

# Maps module params to query response field names
PARAM_TO_QUERY = {
    "remote_server": "syslogServer",
    "remote_port": "syslogPort",
    "protocol": "syslogProtocol",
}


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        remote_server=dict(type="str"),
        remote_port=dict(type="int"),
        protocol=dict(type="str", choices=["udp", "tcp"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["remote_server", "remote_port", "protocol"]],
    )

    try:
        client = get_client(module)
        data = client.query(QUERY_SYSLOG)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query syslog settings: {exc}")

    current_vars = data.get("vars", {})

    settings_update = {}
    diff_before = {}
    diff_after = {}

    for param_name, setting_key in PARAM_TO_SETTING.items():
        desired = module.params.get(param_name)
        if desired is None:
            continue

        query_key = PARAM_TO_QUERY[param_name]
        current = current_vars.get(query_key)

        if str(desired) == str(current) if current is not None else False:
            continue

        settings_update[setting_key] = desired
        diff_before[param_name] = current
        diff_after[param_name] = desired

    result = dict(
        remote_server=module.params.get("remote_server") or current_vars.get("syslogServer"),
        remote_port=module.params.get("remote_port") or current_vars.get("syslogPort"),
        protocol=module.params.get("protocol") or current_vars.get("syslogProtocol"),
    )

    if not settings_update:
        module.exit_json(changed=False, syslog=result)
        return

    diff = {"before": diff_before, "after": diff_after}

    if module.check_mode:
        module.exit_json(changed=True, syslog=result, diff=diff)
        return

    try:
        client.mutate(
            MUTATION_UPDATE_SETTINGS,
            variables={"input": settings_update},
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to update syslog settings: {exc}")

    module.exit_json(changed=True, syslog=result, diff=diff)


if __name__ == "__main__":
    main()
