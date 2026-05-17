#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: network_info
short_description: Query network access URLs from an Unraid server
description:
    - Retrieves network access URLs including LAN, WAN, WireGuard, and mDNS.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
options:
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
"""

EXAMPLES = r"""
- name: Get network access URLs
  stevefulme1.unraid.network_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: network

- name: Show LAN URLs
  ansible.builtin.debug:
    var: network.network
"""

RETURN = r"""
network:
    description: Network access information.
    returned: success
    type: dict
    sample:
        lan:
            - "https://192.168.1.10"
        wan:
            - "https://tower.unraid.net"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY = """
{
    network {
        accessUrls {
            type
            urls
        }
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    try:
        client = get_client(module)
        data = client.query(QUERY)
        raw = data.get("network", {}).get("accessUrls", [])
        network = {entry["type"]: entry["urls"] for entry in raw}
        module.exit_json(changed=False, network=network)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
