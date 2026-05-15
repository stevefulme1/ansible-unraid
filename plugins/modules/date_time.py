#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: date_time
short_description: Configure timezone and NTP on Unraid
description:
    - Configure the system timezone and NTP server on an Unraid server
      via the GraphQL API C(updateSettings) mutation.
    - Compares current settings against desired state and only applies
      changes when necessary.
    - At least one of I(timezone) or I(ntp_server) must be provided.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    timezone:
        description:
            - IANA timezone string (e.g., C(America/New_York),
              C(Europe/London), C(UTC)).
        type: str
    ntp_server:
        description:
            - NTP server hostname or IP address used for time
              synchronization (e.g., C(pool.ntp.org)).
        type: str
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Set timezone to US Eastern
  stevefulme1.unraid.date_time:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    timezone: America/New_York

- name: Set NTP server
  stevefulme1.unraid.date_time:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    ntp_server: pool.ntp.org

- name: Set both timezone and NTP
  stevefulme1.unraid.date_time:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    timezone: America/Chicago
    ntp_server: time.google.com
"""

RETURN = r"""
date_time:
    description: The date/time configuration after changes.
    returned: success
    type: dict
    contains:
        timezone:
            description: The configured timezone.
            type: str
        ntp_server:
            description: The configured NTP server.
            type: str
    sample:
        timezone: America/New_York
        ntp_server: pool.ntp.org
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

QUERY_DATE_TIME = """
{
    vars {
        timezone
        ntpServer
    }
}
"""

MUTATION_UPDATE_SETTINGS = """
mutation UpdateSettings($input: SettingsInput!) {
    updateSettings(input: $input)
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        timezone=dict(type="str"),
        ntp_server=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["timezone", "ntp_server"]],
    )

    timezone = module.params["timezone"]
    ntp_server = module.params["ntp_server"]

    try:
        client = get_client(module)
        data = client.query(QUERY_DATE_TIME)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query date/time settings: {exc}")

    current_vars = data.get("vars", {})
    current_tz = current_vars.get("timezone")
    current_ntp = current_vars.get("ntpServer")

    settings_update = {}
    diff_before = {}
    diff_after = {}

    if timezone is not None and timezone != current_tz:
        settings_update["timezone"] = timezone
        diff_before["timezone"] = current_tz
        diff_after["timezone"] = timezone

    if ntp_server is not None and ntp_server != current_ntp:
        settings_update["ntpServer"] = ntp_server
        diff_before["ntp_server"] = current_ntp
        diff_after["ntp_server"] = ntp_server

    result = dict(
        timezone=timezone if timezone is not None else current_tz,
        ntp_server=ntp_server if ntp_server is not None else current_ntp,
    )

    if not settings_update:
        module.exit_json(changed=False, date_time=result)
        return

    diff = {"before": diff_before, "after": diff_after}

    if module.check_mode:
        module.exit_json(changed=True, date_time=result, diff=diff)
        return

    try:
        client.mutate(
            MUTATION_UPDATE_SETTINGS,
            variables={"input": settings_update},
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to update date/time settings: {exc}")

    module.exit_json(changed=True, date_time=result, diff=diff)


if __name__ == "__main__":
    main()
