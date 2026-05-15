#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: array
short_description: Start or stop the Unraid disk array
description:
    - Manage the state of the Unraid disk array.
    - Queries the current array state and only makes changes when
      the desired state differs from the current state.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    state:
        description:
            - Desired state of the disk array.
        type: str
        required: true
        choices:
            - started
            - stopped
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Start the disk array
  stevefulme1.unraid.array:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
    state: started

- name: Stop the disk array
  stevefulme1.unraid.array:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    state: stopped
"""

RETURN = r"""
state:
    description: The current state of the array after the operation.
    returned: always
    type: str
    sample: STARTED
previous_state:
    description: The state of the array before the operation.
    returned: always
    type: str
    sample: STOPPED
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_ARRAY_STATE = """
{
    array {
        state
    }
}
"""

MUTATION_SET_STATE = """
mutation SetArrayState($desiredState: ArrayAction!) {
    array {
        setState(desiredState: $desiredState) {
            state
        }
    }
}
"""

# Map module param values to GraphQL enum values
STATE_MAP = {
    "started": "START",
    "stopped": "STOP",
}

# Map GraphQL state values to module param values for comparison
RUNNING_STATES = {
    "STARTED": "started",
    "STARTING": "started",
}
STOPPED_STATES = {
    "STOPPED": "stopped",
    "STOPPING": "stopped",
}


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        state=dict(type="str", required=True, choices=["started", "stopped"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    desired_state = module.params["state"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Query current state
    try:
        data = client.query(QUERY_ARRAY_STATE)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query array state: {exc}")

    current_state = data.get("array", {}).get("state", "UNKNOWN")

    # Determine if current state already matches desired
    if desired_state == "started" and current_state in RUNNING_STATES:
        module.exit_json(
            changed=False,
            state=current_state,
            previous_state=current_state,
        )
    elif desired_state == "stopped" and current_state in STOPPED_STATES:
        module.exit_json(
            changed=False,
            state=current_state,
            previous_state=current_state,
        )

    # Check mode: report what would change
    if module.check_mode:
        module.exit_json(
            changed=True,
            state=STATE_MAP[desired_state],
            previous_state=current_state,
            msg=f"Would change array state from {current_state} to {STATE_MAP[desired_state]}",
        )

    # Apply state change
    try:
        result = client.mutate(
            MUTATION_SET_STATE,
            variables={"desiredState": STATE_MAP[desired_state]},
        )
    except UnraidError as exc:
        module.fail_json(
            msg=f"Failed to set array state to {desired_state}: {exc}",
            previous_state=current_state,
        )

    new_state = result.get("array", {}).get("setState", {}).get("state", STATE_MAP[desired_state])

    module.exit_json(
        changed=True,
        state=new_state,
        previous_state=current_state,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
