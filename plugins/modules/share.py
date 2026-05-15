#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing Unraid user shares."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: share
short_description: Manage user shares on Unraid
version_added: "1.0.0"
description:
  - Query and validate user shares on an Unraid server.
  - The Unraid GraphQL API provides read-only access to share information.
    Creating, modifying, or deleting shares requires SSH access and direct
    manipulation of configuration files at C(/boot/config/shares/).
  - This module operates in a B(read-check) mode. It queries the current
    shares via the API and reports whether the desired share exists and
    what its current state is versus the desired parameters.
  - When I(state=present) and the share does not exist, the module reports
    C(changed=True) but cannot create the share via the API alone. Use the
    C(ansible.builtin.command) or C(ansible.builtin.template) modules with
    SSH to create shares on the Unraid boot device.
  - When I(state=absent) and the share exists, the module reports
    C(changed=True) but cannot delete the share via the API alone.
options:
  name:
    description:
      - The name of the user share.
    type: str
    required: true
  state:
    description:
      - The desired state of the share.
      - C(present) checks that the share exists.
      - C(absent) checks that the share does not exist.
      - B(Note:) This module can only report desired vs actual state.
        Actual creation or deletion requires SSH and config file manipulation.
    type: str
    choices: [present, absent]
    default: present
  allocation_method:
    description:
      - The disk allocation method for the share.
      - Only used for state reporting and comparison.
    type: str
    choices: [highwater, fillup, most_free]
    required: false
  cache:
    description:
      - The cache setting for the share.
      - Only used for state reporting and comparison.
    type: str
    choices: ["yes", "no", "only", "prefer"]
    required: false
  include_disks:
    description:
      - List of disks to include for this share.
      - Only used for state reporting and comparison.
    type: list
    elements: str
    required: false
  exclude_disks:
    description:
      - List of disks to exclude from this share.
      - Only used for state reporting and comparison.
    type: list
    elements: str
    required: false
  smb_export:
    description:
      - Whether to export the share via SMB/CIFS.
      - Only used for state reporting and comparison.
    type: bool
    required: false
  nfs_export:
    description:
      - Whether to export the share via NFS.
      - Only used for state reporting and comparison.
    type: bool
    required: false
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - The Unraid GraphQL API is read-only for shares. This module cannot
    create, modify, or delete shares through the API.
  - To create a share, write a configuration file to
    C(/boot/config/shares/<sharename>.cfg) via SSH and restart the share
    service.
  - This module is useful for validation and compliance checks in playbooks.
"""

EXAMPLES = r"""
- name: Check if appdata share exists
  stevefulme1.unraid.share:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: appdata
    state: present
  register: share_result

- name: Report share status
  ansible.builtin.debug:
    msg: >
      Share '{{ share_result.share.name }}' exists with
      {{ share_result.share.size }} bytes total,
      {{ share_result.share.free }} bytes free

- name: Validate share does not exist
  stevefulme1.unraid.share:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: temp-share
    state: absent

- name: Check share with desired parameters
  stevefulme1.unraid.share:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: media
    state: present
    allocation_method: highwater
    cache: "yes"
    smb_export: true
    nfs_export: false
  register: media_share

- name: Show desired vs actual state
  ansible.builtin.debug:
    var: media_share.desired_config
  when: media_share.changed
"""

RETURN = r"""
share:
  description: The share information from the API, if the share exists.
  returned: when the share exists
  type: dict
  contains:
    name:
      description: The share name.
      type: str
    free:
      description: Free space in bytes.
      type: int
    used:
      description: Used space in bytes.
      type: int
    size:
      description: Total size in bytes.
      type: int
  sample:
    name: "appdata"
    free: 1073741824
    used: 536870912
    size: 1610612736
exists:
  description: Whether the share currently exists on the server.
  returned: always
  type: bool
  sample: true
desired_config:
  description:
    - The desired configuration as specified in the module parameters.
    - Only returned when there are desired parameters beyond name and state.
    - Since the API is read-only for shares, this shows what would need to
      be configured via SSH or the WebGUI.
  returned: when desired configuration params are provided
  type: dict
  sample:
    allocation_method: "highwater"
    cache: "yes"
    smb_export: true
msg:
  description: A message describing the result and any required manual actions.
  returned: always
  type: str
"""

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)
from ansible.module_utils.basic import AnsibleModule


QUERY_SHARES = """
{
  shares {
    name
    free
    used
    size
  }
}
"""


def get_shares(client):
    """Return the list of shares from the API."""
    result = client.query(QUERY_SHARES)
    return result.get("shares", [])


def find_share(shares, name):
    """Find a share by name in the share list."""
    for share in shares:
        if share.get("name") == name:
            return share
    return None


def build_desired_config(module):
    """Build a dict of desired configuration from module params."""
    config = {}
    config_params = [
        "allocation_method",
        "cache",
        "include_disks",
        "exclude_disks",
        "smb_export",
        "nfs_export",
    ]
    for param in config_params:
        value = module.params.get(param)
        if value is not None:
            config[param] = value
    return config


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        allocation_method=dict(
            type="str",
            choices=["highwater", "fillup", "most_free"],
            required=False,
        ),
        cache=dict(
            type="str",
            choices=["yes", "no", "only", "prefer"],
            required=False,
        ),
        include_disks=dict(type="list", elements="str", required=False),
        exclude_disks=dict(type="list", elements="str", required=False),
        smb_export=dict(type="bool", required=False),
        nfs_export=dict(type="bool", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]

    try:
        client = get_client(module)
        shares = get_shares(client)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    existing = find_share(shares, name)
    exists = existing is not None
    desired_config = build_desired_config(module)

    result = {
        "exists": exists,
    }

    if desired_config:
        result["desired_config"] = desired_config

    # --- state: absent ---
    if state == "absent":
        if not exists:
            result["changed"] = False
            result["msg"] = f"Share '{name}' does not exist."
            module.exit_json(**result)

        result["changed"] = True
        result["share"] = existing
        result["msg"] = (
            f"Share '{name}' exists but cannot be deleted via the API. "
            f"Remove the share configuration at /boot/config/shares/{name}.cfg "
            f"via SSH and restart the share service."
        )
        module.exit_json(**result)

    # --- state: present ---
    if exists:
        result["share"] = existing

        if desired_config:
            result["changed"] = True
            result["msg"] = (
                f"Share '{name}' exists. Desired configuration parameters were "
                f"specified but cannot be verified or applied via the read-only "
                f"GraphQL API. Review desired_config and configure via SSH or "
                f"the WebGUI if needed."
            )
        else:
            result["changed"] = False
            result["msg"] = f"Share '{name}' exists."

        module.exit_json(**result)

    # Share does not exist
    result["changed"] = True
    result["msg"] = (
        f"Share '{name}' does not exist and cannot be created via the API. "
        f"Create the share configuration at /boot/config/shares/{name}.cfg "
        f"via SSH and restart the share service."
    )
    module.exit_json(**result)


if __name__ == "__main__":
    main()
