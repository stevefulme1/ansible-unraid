#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for querying detailed Unraid share information."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: share_info
short_description: Query detailed share information on Unraid
version_added: "1.0.0"
description:
  - Retrieve detailed information about user shares on an Unraid server
    via the GraphQL API.
  - Returns comprehensive share details including name, size, free space,
    used space, and configuration settings when available.
  - Can return all shares or filter to a specific share by name.
  - This is an info module and never changes state on the target.
  - Requires Unraid 7.2 or later.
options:
  name:
    description:
      - Name of a specific share to retrieve.
      - When omitted, information for all shares is returned.
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
notes:
  - This module returns more detailed information than the
    M(stevefulme1.unraid.share) module, which is focused on state management.
  - Share configuration details (allocation method, cache settings, SMB/NFS
    export settings) availability depends on the Unraid GraphQL API schema
    version.
  - For managing share state (present/absent checks), use the
    M(stevefulme1.unraid.share) module instead.
"""

EXAMPLES = r"""
- name: Get all share details
  stevefulme1.unraid.share_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: all_shares

- name: Display share summary
  ansible.builtin.debug:
    msg: "{{ item.name }}: {{ item.used | default(0) }} used / {{ item.size | default(0) }} total"
  loop: "{{ all_shares.shares }}"

- name: Get a specific share
  stevefulme1.unraid.share_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    name: appdata
  register: appdata

- name: Show appdata share details
  ansible.builtin.debug:
    var: appdata.shares[0]

- name: Calculate total storage usage
  stevefulme1.unraid.share_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: all_shares

- name: Report total used space
  ansible.builtin.debug:
    msg: "Total used: {{ all_shares.shares | map(attribute='used') | select('defined') | map('int') | sum }} bytes"
"""

RETURN = r"""
shares:
  description: List of share details.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Share name.
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
    comment:
      description: Share description/comment.
      type: str
    allocator:
      description: Disk allocation method (highwater, fillup, most_free).
      type: str
    floor:
      description: Minimum free space floor in bytes.
      type: str
    splitLevel:
      description: Split level setting for the share.
      type: str
    include:
      description: Included disks.
      type: str
    exclude:
      description: Excluded disks.
      type: str
    cache:
      description: Cache pool usage setting.
      type: str
    cachePool:
      description: Name of the cache pool used by this share.
      type: str
    cow:
      description: Copy-on-write setting.
      type: str
    smbExport:
      description: SMB/CIFS export setting.
      type: str
    nfsExport:
      description: NFS export setting.
      type: str
  sample:
    - name: "appdata"
      free: 1073741824
      used: 536870912
      size: 1610612736
      comment: "Application data"
count:
  description: Number of shares returned.
  returned: always
  type: int
  sample: 5
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_SHARES = """
{
    shares {
        name
        free
        used
        size
        comment
        allocator
        floor
        splitLevel
        include
        exclude
        cache
        cachePool
        cow
        smbExport
        nfsExport
    }
}
"""

# Fallback query if the extended fields are not supported
QUERY_SHARES_BASIC = """
{
    shares {
        name
        free
        used
        size
    }
}
"""


def main():
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

    # Try extended query first, fall back to basic
    shares = None
    try:
        data = client.query(QUERY_SHARES)
        shares = data.get("shares", [])
    except UnraidError:
        try:
            data = client.query(QUERY_SHARES_BASIC)
            shares = data.get("shares", [])
        except UnraidError as exc:
            module.fail_json(msg="Failed to query shares: %s" % str(exc))

    if shares is None:
        shares = []

    if name is not None:
        shares = [s for s in shares if s.get("name") == name]
        if not shares:
            module.fail_json(msg="Share '%s' not found." % name)

    module.exit_json(changed=False, shares=shares, count=len(shares))


if __name__ == "__main__":
    main()
