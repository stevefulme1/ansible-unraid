#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing Unraid VM snapshots."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: vm_snapshot
short_description: Manage VM snapshots on Unraid
version_added: "1.0.0"
description:
  - Create, delete, or revert virtual machine snapshots on an Unraid server.
  - The Unraid GraphQL API (7.2+) does not currently expose snapshot management
    mutations. This module uses SSH to execute C(virsh) commands on the Unraid
    host as a fallback.
  - Requires the C(ansible.builtin.command) module to be available for SSH
    execution when GraphQL snapshot mutations are not supported.
  - Snapshot operations use C(virsh snapshot-create-as), C(virsh snapshot-delete),
    and C(virsh snapshot-revert) under the hood.
  - The module queries the GraphQL API to validate that the target VM exists
    before attempting any snapshot operation.
options:
  vm_name:
    description:
      - Name of the virtual machine to manage snapshots for.
    type: str
    required: true
  snapshot_name:
    description:
      - Name of the snapshot to create, delete, or revert to.
      - Required when I(state=present), I(state=absent), or I(state=reverted).
    type: str
  state:
    description:
      - Desired state of the snapshot.
      - V(present) creates a new snapshot of the VM.
      - V(absent) deletes an existing snapshot.
      - V(reverted) reverts the VM to the specified snapshot.
    type: str
    required: true
    choices:
      - present
      - absent
      - reverted
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - The Unraid GraphQL API does not currently support snapshot mutations.
    This module falls back to SSH and C(virsh) commands for snapshot operations.
  - Ensure SSH access to the Unraid host is configured (key-based authentication
    recommended) when using this module.
  - Snapshots require the VM to be using a qcow2 disk image format. Raw disk
    images do not support snapshots.
  - Reverting a snapshot will discard all changes made after the snapshot was taken.
"""

EXAMPLES = r"""
- name: Create a VM snapshot
  stevefulme1.unraid.vm_snapshot:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    vm_name: Windows11
    snapshot_name: before-update
    state: present

- name: Delete a VM snapshot
  stevefulme1.unraid.vm_snapshot:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    vm_name: Windows11
    snapshot_name: before-update
    state: absent

- name: Revert VM to a snapshot
  stevefulme1.unraid.vm_snapshot:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    vm_name: Ubuntu
    snapshot_name: clean-state
    state: reverted

- name: Create snapshot with SSH fallback (typical usage)
  stevefulme1.unraid.vm_snapshot:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    vm_name: DevBox
    snapshot_name: "pre-deploy-{{ ansible_date_time.iso8601 }}"
    state: present
"""

RETURN = r"""
vm_name:
  description: Name of the VM the snapshot operation was performed on.
  returned: always
  type: str
  sample: Windows11
snapshot_name:
  description: Name of the snapshot.
  returned: always
  type: str
  sample: before-update
snapshots:
  description:
    - List of existing snapshots for the VM after the operation.
    - Each item contains the snapshot name and creation time when available.
  returned: success
  type: list
  elements: dict
  contains:
    name:
      description: Snapshot name.
      type: str
    creation_time:
      description: Snapshot creation timestamp.
      type: str
  sample:
    - name: before-update
      creation_time: "2026-01-15T10:30:00"
method:
  description: The method used to perform the operation (graphql or ssh/virsh).
  returned: always
  type: str
  sample: ssh/virsh
msg:
  description: Human-readable result message.
  returned: always
  type: str
"""

import shlex

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

VIRSH_COMMANDS = {
    "list": "virsh snapshot-list --domain {vm_name} --name 2>/dev/null",
    "create": "virsh snapshot-create-as --domain {vm_name} --name {snapshot_name}",
    "delete": "virsh snapshot-delete --domain {vm_name} --snapshotname {snapshot_name}",
    "revert": "virsh snapshot-revert --domain {vm_name} --snapshotname {snapshot_name}",
}


def _build_virsh_cmd(template, vm_name, snapshot_name=None):
    """Build a virsh command with shell-escaped user-supplied values."""
    parts = {"vm_name": shlex.quote(vm_name)}
    if snapshot_name is not None:
        parts["snapshot_name"] = shlex.quote(snapshot_name)
    return template.format(**parts)


def find_vm(vms, name):
    """Find a VM by name."""
    for vm in vms:
        if vm.get("name") == name:
            return vm
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        vm_name=dict(type="str", required=True),
        snapshot_name=dict(type="str"),
        state=dict(
            type="str",
            required=True,
            choices=["present", "absent", "reverted"],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "present", ["snapshot_name"]),
            ("state", "absent", ["snapshot_name"]),
            ("state", "reverted", ["snapshot_name"]),
        ],
        supports_check_mode=True,
    )

    vm_name = module.params["vm_name"]
    snapshot_name = module.params["snapshot_name"]
    state = module.params["state"]

    client = get_client(module)

    # Validate the VM exists via GraphQL
    try:
        data = client.query(QUERY_VMS)
        vms = data.get("vms", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query VMs: %s" % str(exc))

    vm = find_vm(vms, vm_name)
    if vm is None:
        module.fail_json(msg="VM '%s' not found." % vm_name)

    result = dict(
        changed=False,
        vm_name=vm_name,
        snapshot_name=snapshot_name,
        method="ssh/virsh",
    )

    # List existing snapshots
    list_cmd = _build_virsh_cmd(VIRSH_COMMANDS["list"], vm_name)
    rc, stdout, stderr = module.run_command(list_cmd, use_unsafe_shell=True)
    existing_snapshots = [
        s.strip() for s in stdout.strip().splitlines() if s.strip()
    ]

    snapshot_exists = snapshot_name in existing_snapshots

    if state == "present":
        if snapshot_exists:
            result["msg"] = "Snapshot '%s' already exists for VM '%s'." % (
                snapshot_name,
                vm_name,
            )
        else:
            result["changed"] = True
            if module.check_mode:
                result["msg"] = (
                    "Would create snapshot '%s' for VM '%s'."
                    % (snapshot_name, vm_name)
                )
            else:
                cmd = _build_virsh_cmd(
                    VIRSH_COMMANDS["create"], vm_name, snapshot_name
                )
                rc, stdout, stderr = module.run_command(cmd)
                if rc != 0:
                    module.fail_json(
                        msg="Failed to create snapshot: %s" % stderr.strip()
                    )
                result["msg"] = (
                    "Snapshot '%s' created for VM '%s'."
                    % (snapshot_name, vm_name)
                )

    elif state == "absent":
        if not snapshot_exists:
            result["msg"] = (
                "Snapshot '%s' does not exist for VM '%s'."
                % (snapshot_name, vm_name)
            )
        else:
            result["changed"] = True
            if module.check_mode:
                result["msg"] = (
                    "Would delete snapshot '%s' from VM '%s'."
                    % (snapshot_name, vm_name)
                )
            else:
                cmd = _build_virsh_cmd(
                    VIRSH_COMMANDS["delete"], vm_name, snapshot_name
                )
                rc, stdout, stderr = module.run_command(cmd)
                if rc != 0:
                    module.fail_json(
                        msg="Failed to delete snapshot: %s" % stderr.strip()
                    )
                result["msg"] = (
                    "Snapshot '%s' deleted from VM '%s'."
                    % (snapshot_name, vm_name)
                )

    elif state == "reverted":
        if not snapshot_exists:
            module.fail_json(
                msg="Snapshot '%s' not found for VM '%s'."
                % (snapshot_name, vm_name)
            )
        result["changed"] = True
        if module.check_mode:
            result["msg"] = (
                "Would revert VM '%s' to snapshot '%s'."
                % (vm_name, snapshot_name)
            )
        else:
            cmd = _build_virsh_cmd(
                VIRSH_COMMANDS["revert"], vm_name, snapshot_name
            )
            rc, stdout, stderr = module.run_command(cmd)
            if rc != 0:
                module.fail_json(
                    msg="Failed to revert to snapshot: %s" % stderr.strip()
                )
            result["msg"] = "VM '%s' reverted to snapshot '%s'." % (
                vm_name,
                snapshot_name,
            )

    # Re-list snapshots for return value
    if not module.check_mode:
        rc, stdout, stderr = module.run_command(list_cmd, use_unsafe_shell=True)
        current_snapshots = [
            s.strip() for s in stdout.strip().splitlines() if s.strip()
        ]
        result["snapshots"] = [{"name": s} for s in current_snapshots]
    else:
        result["snapshots"] = [{"name": s} for s in existing_snapshots]

    module.exit_json(**result)


if __name__ == "__main__":
    main()
