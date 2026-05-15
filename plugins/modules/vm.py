#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: vm
short_description: Manage VM lifecycle on Unraid
version_added: "1.0.0"
description:
    - Start, stop, pause, resume, force-stop, or reboot virtual machines
      on an Unraid server via the GraphQL API.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Name of the virtual machine.
            - At least one of O(name) or O(id) is required.
        type: str
    id:
        description:
            - VM identifier (UUID).
            - At least one of O(name) or O(id) is required.
        type: str
    state:
        description:
            - Desired state of the virtual machine.
            - V(started) powers on the VM.
            - V(stopped) performs a graceful shutdown (ACPI).
            - V(paused) suspends execution.
            - V(resumed) resumes a paused VM.
            - V(force_stopped) immediately terminates the VM (use with
              caution).
            - V(rebooted) performs a graceful reboot.
        type: str
        required: true
        choices:
            - started
            - stopped
            - paused
            - resumed
            - force_stopped
            - rebooted
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Start a VM
  stevefulme1.unraid.vm:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: Windows11
    state: started

- name: Gracefully stop a VM
  stevefulme1.unraid.vm:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: Ubuntu
    state: stopped

- name: Force-stop an unresponsive VM
  stevefulme1.unraid.vm:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: Ubuntu
    state: force_stopped

- name: Pause a VM
  stevefulme1.unraid.vm:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: DevBox
    state: paused

- name: Resume a paused VM
  stevefulme1.unraid.vm:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: DevBox
    state: resumed

- name: Reboot a VM
  stevefulme1.unraid.vm:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    state: rebooted
"""

RETURN = r"""
vm:
    description: VM details after the operation.
    type: dict
    returned: success
    contains:
        id:
            description: VM identifier (UUID).
            type: str
        name:
            description: VM name.
            type: str
        state:
            description: Current VM state.
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_VMS = """
{
    vms {
        id
        name
        state
    }
}
"""

STATE_MUTATIONS = {
    "started": 'mutation($id: String!) { vm { start(id: $id) } }',
    "stopped": 'mutation($id: String!) { vm { stop(id: $id) } }',
    "paused": 'mutation($id: String!) { vm { pause(id: $id) } }',
    "resumed": 'mutation($id: String!) { vm { resume(id: $id) } }',
    "force_stopped": 'mutation($id: String!) { vm { forceStop(id: $id) } }',
    "rebooted": 'mutation($id: String!) { vm { reboot(id: $id) } }',
}

# API state values mapped to logical groups
VM_RUNNING = ("running", "started")
VM_STOPPED = ("shutoff", "stopped", "shut off")
VM_PAUSED = ("paused",)


def find_vm(vms, name=None, vm_id=None):
    """Find a VM by name or ID."""
    for vm in vms:
        if vm_id and vm.get("id") == vm_id:
            return vm
        if name and vm.get("name") == name:
            return vm
    return None


def is_state_change_needed(current_state, desired_state):
    """Check whether a mutation is needed given current VM state."""
    current = (current_state or "").lower()

    if desired_state == "started":
        return current not in VM_RUNNING
    if desired_state == "stopped":
        return current not in VM_STOPPED
    if desired_state == "force_stopped":
        return current not in VM_STOPPED
    if desired_state == "paused":
        return current not in VM_PAUSED
    if desired_state == "resumed":
        return current in VM_PAUSED
    # rebooted always triggers
    return True


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str"),
        id=dict(type="str"),
        state=dict(
            type="str",
            required=True,
            choices=[
                "started",
                "stopped",
                "paused",
                "resumed",
                "force_stopped",
                "rebooted",
            ],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["name", "id"]],
        supports_check_mode=True,
    )

    name = module.params["name"]
    vm_id = module.params["id"]
    state = module.params["state"]

    client = get_client(module)
    result = dict(changed=False)

    try:
        data = client.query(QUERY_VMS)
        vms = data.get("vms", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query VMs: %s" % str(exc))

    vm = find_vm(vms, name=name, vm_id=vm_id)

    if vm is None:
        identifier = name if name else vm_id
        module.fail_json(msg="VM '%s' not found." % identifier)

    current_state = vm.get("state", "")
    vid = vm["id"]

    if not is_state_change_needed(current_state, state):
        result["vm"] = vm
        module.exit_json(**result)

    result["changed"] = True
    if module.check_mode:
        result["vm"] = vm
        module.exit_json(**result)

    mutation = STATE_MUTATIONS[state]
    try:
        client.mutate(mutation, variables={"id": vid})
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to set VM to '%s': %s" % (state, str(exc))
        )

    # Re-query to return updated state
    try:
        data = client.query(QUERY_VMS)
        vms = data.get("vms", [])
        vm = find_vm(vms, vm_id=vid)
    except UnraidError:
        pass

    if vm:
        result["vm"] = vm
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
