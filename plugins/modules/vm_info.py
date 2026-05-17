#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: vm_info
short_description: Query VM information from Unraid
version_added: "1.0.0"
description:
    - Retrieve information about virtual machines on an Unraid server
      via the GraphQL API.
    - Can return all VMs or filter to a specific VM by name.
    - This is an info module and never changes state on the target.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Name of a specific VM to retrieve.
            - When omitted, information for all VMs is returned.
        type: str

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
"""

EXAMPLES = r"""
- name: Get all VMs
  stevefulme1.unraid.vm_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: all_vms

- name: Display VM names
  ansible.builtin.debug:
    msg: "{{ all_vms.vms | map(attribute='name') | list }}"

- name: Get a specific VM
  stevefulme1.unraid.vm_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: Windows11
  register: win_vm

- name: Show VM state
  ansible.builtin.debug:
    msg: "{{ win_vm.vms[0].state }}"
"""

RETURN = r"""
vms:
    description: List of VM details.
    type: list
    elements: dict
    returned: always
    contains:
        id:
            description: VM identifier (UUID).
            type: str
        name:
            description: VM name.
            type: str
        state:
            description: Current VM state (e.g. running, shutoff, paused).
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


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str"),
    )
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    client = get_client(module)

    try:
        data = client.query(QUERY_VMS)
        vms = data.get("vms", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query VMs: %s" % str(exc))

    if name is not None:
        vms = [vm for vm in vms if vm.get("name") == name]
        if not vms:
            module.fail_json(msg="VM '%s' not found." % name)

    module.exit_json(changed=False, vms=vms)


def main():
    run_module()


if __name__ == "__main__":
    main()
