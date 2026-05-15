#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: parity_history
short_description: Query Unraid parity check history
description:
    - Query the Unraid GraphQL API for historical parity check results.
    - Returns the date, duration, speed, and error count for each
      completed parity check.
    - This is a read-only info module and makes no changes.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    limit:
        description:
            - Maximum number of parity history entries to return.
            - Results are returned in reverse chronological order
              (most recent first).
        type: int
        required: false
        default: 10
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Get last 10 parity checks
  stevefulme1.unraid.parity_history:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
  register: parity

- name: Get last 5 parity checks
  stevefulme1.unraid.parity_history:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    limit: 5
  register: parity

- name: Alert on parity errors
  ansible.builtin.debug:
    msg: "ALERT: Parity check on {{ item.date }} had {{ item.errors }} errors!"
  loop: "{{ parity.history }}"
  when: item.errors | int > 0
"""

RETURN = r"""
history:
    description: List of parity check history entries.
    returned: always
    type: list
    elements: dict
    contains:
        date:
            description: Date and time of the parity check.
            type: str
            sample: "2026-01-15T03:00:00Z"
        duration:
            description: Duration of the parity check.
            type: str
            sample: "12 hours, 34 minutes"
        speed:
            description: Average speed of the parity check.
            type: str
            sample: "120.5 MB/s"
        errors:
            description: Number of parity errors found.
            type: int
            sample: 0
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_PARITY_HISTORY = """
{
    parityHistory {
        date
        duration
        speed
        errors
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        limit=dict(type="int", required=False, default=10),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    limit = module.params["limit"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    try:
        data = client.query(QUERY_PARITY_HISTORY)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query parity history: {exc}")

    history = data.get("parityHistory", [])

    # Apply limit
    if limit and limit > 0:
        history = history[:limit]

    module.exit_json(changed=False, history=history)


def main():
    run_module()


if __name__ == "__main__":
    main()
