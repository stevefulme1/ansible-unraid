#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: parity
short_description: Manage Unraid parity check operations
description:
    - Start, pause, resume, or cancel a parity check on the Unraid array.
    - When starting a parity check, the O(correct) option controls whether
      errors are automatically corrected.
    - Queries the current parity status and only acts when the requested
      operation makes sense for the current state.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    state:
        description:
            - Desired parity check operation.
            - C(running) starts a new parity check or resumes a paused one.
            - C(paused) pauses a running parity check.
            - C(cancelled) cancels an in-progress or paused parity check.
        type: str
        required: true
        choices:
            - running
            - paused
            - cancelled
    correct:
        description:
            - Whether to correct parity errors found during the check.
            - Only used when starting a new parity check.
        type: bool
        default: true
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Start a parity check with correction
  stevefulme1.unraid.parity:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    state: running
    correct: true

- name: Pause a running parity check
  stevefulme1.unraid.parity:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    state: paused

- name: Cancel parity check
  stevefulme1.unraid.parity:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    state: cancelled
"""

RETURN = r"""
parity:
    description: Parity status after the operation.
    returned: always
    type: dict
    contains:
        status:
            description: Current parity check status.
            type: str
            sample: RUNNING
        progress:
            description: Parity check progress percentage.
            type: float
            sample: 45.2
previous_status:
    description: Parity status before the operation.
    returned: always
    type: str
    sample: IDLE
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_PARITY_STATUS = """
{
    array {
        parity {
            status
            progress
        }
    }
}
"""

MUTATION_START = """
mutation StartParityCheck($correct: Boolean!) {
    parityCheck {
        start(correct: $correct) {
            status
            progress
        }
    }
}
"""

MUTATION_PAUSE = """
mutation {
    parityCheck {
        pause {
            status
            progress
        }
    }
}
"""

MUTATION_RESUME = """
mutation {
    parityCheck {
        resume {
            status
            progress
        }
    }
}
"""

MUTATION_CANCEL = """
mutation {
    parityCheck {
        cancel {
            status
            progress
        }
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        state=dict(
            type="str",
            required=True,
            choices=["running", "paused", "cancelled"],
        ),
        correct=dict(type="bool", default=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    desired_state = module.params["state"]
    correct = module.params["correct"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Query current parity status
    try:
        data = client.query(QUERY_PARITY_STATUS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query parity status: {exc}")

    parity = data.get("array", {}).get("parity", {})
    current_status = parity.get("status", "IDLE").upper()

    # Determine if action is needed
    if desired_state == "running" and current_status == "RUNNING":
        module.exit_json(changed=False, parity=parity, previous_status=current_status)
    elif desired_state == "paused" and current_status == "PAUSED":
        module.exit_json(changed=False, parity=parity, previous_status=current_status)
    elif desired_state == "cancelled" and current_status in ("IDLE", ""):
        module.exit_json(changed=False, parity=parity, previous_status=current_status)

    if module.check_mode:
        module.exit_json(
            changed=True,
            parity=parity,
            previous_status=current_status,
            msg=f"Would change parity state from {current_status} to {desired_state}",
        )

    # Execute the appropriate mutation
    try:
        if desired_state == "running":
            if current_status == "PAUSED":
                result = client.mutate(MUTATION_RESUME)
                new_parity = result.get("parityCheck", {}).get("resume", {})
            else:
                result = client.mutate(
                    MUTATION_START,
                    variables={"correct": correct},
                )
                new_parity = result.get("parityCheck", {}).get("start", {})

        elif desired_state == "paused":
            if current_status != "RUNNING":
                module.fail_json(
                    msg=f"Cannot pause parity check: current status is {current_status}, expected RUNNING",
                    previous_status=current_status,
                )
            result = client.mutate(MUTATION_PAUSE)
            new_parity = result.get("parityCheck", {}).get("pause", {})

        elif desired_state == "cancelled":
            if current_status not in ("RUNNING", "PAUSED"):
                module.fail_json(
                    msg=f"Cannot cancel parity check: current status is {current_status}",
                    previous_status=current_status,
                )
            result = client.mutate(MUTATION_CANCEL)
            new_parity = result.get("parityCheck", {}).get("cancel", {})

    except UnraidError as exc:
        module.fail_json(
            msg=f"Failed to {desired_state} parity check: {exc}",
            previous_status=current_status,
        )

    module.exit_json(
        changed=True,
        parity=new_parity,
        previous_status=current_status,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
