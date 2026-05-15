#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for listing Unraid VM templates and definitions."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: vm_template
short_description: List VM templates and definitions on Unraid
version_added: "1.0.0"
description:
  - Query virtual machine templates and configuration definitions on an
    Unraid server via the GraphQL API.
  - Returns VM configuration details including CPU, memory, disk, and
    network settings for each VM definition.
  - This is a read-only info module and never changes state on the target.
  - VM creation on Unraid requires libvirt XML definitions and cannot be
    performed solely through the GraphQL API. Use C(ansible.builtin.template)
    to render a libvirt XML domain file and C(virsh define) via SSH to
    create new VMs.
  - Requires Unraid 7.2 or later.
options:
  name:
    description:
      - Name of a specific VM template or definition to retrieve.
      - When omitted, information for all VM definitions is returned.
    type: str
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - This module is read-only. VM creation requires libvirt XML domain
    definitions deployed via SSH.
  - VM templates on Unraid are stored as XML files under
    C(/etc/libvirt/qemu/) and as configuration files under
    C(/boot/config/domains/).
  - To create a VM from a template, render a libvirt XML file and use
    C(virsh define /path/to/domain.xml) on the Unraid host.
"""

EXAMPLES = r"""
- name: List all VM templates
  stevefulme1.unraid.vm_template:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: templates

- name: Display template names
  ansible.builtin.debug:
    msg: "{{ templates.vms | map(attribute='name') | list }}"

- name: Get a specific VM template
  stevefulme1.unraid.vm_template:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: Windows11
  register: win_template

- name: Show VM configuration details
  ansible.builtin.debug:
    var: win_template.vms[0]
"""

RETURN = r"""
vms:
  description: List of VM template/definition details.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: VM identifier (UUID).
      type: str
    name:
      description: VM name.
      type: str
    state:
      description: Current VM state (e.g. running, shutoff).
      type: str
    coreCount:
      description: Number of CPU cores allocated.
      type: int
    thread:
      description: Number of CPU threads per core.
      type: int
    memory:
      description: Memory allocation in bytes.
      type: int
  sample:
    - id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
      name: "Windows11"
      state: "shutoff"
      coreCount: 4
      thread: 1
      memory: 8589934592
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_VM_TEMPLATES = """
{
    vms {
        id
        name
        state
        coreCount
        thread
        memory
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    client = get_client(module)

    try:
        data = client.query(QUERY_VM_TEMPLATES)
        vms = data.get("vms", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query VM templates: %s" % str(exc))

    if name is not None:
        vms = [vm for vm in vms if vm.get("name") == name]
        if not vms:
            module.fail_json(msg="VM template '%s' not found." % name)

    module.exit_json(changed=False, vms=vms)


if __name__ == "__main__":
    main()
