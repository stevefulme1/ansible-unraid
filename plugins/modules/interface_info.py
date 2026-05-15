#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: interface_info
short_description: List network interfaces on an Unraid server
description:
    - Retrieves detailed information about all network interfaces on an
      Unraid server via the GraphQL API.
    - Returns interface names, IP addresses, MAC addresses, link state,
      MTU, speed, and type for each interface.
    - This is a read-only module that never makes changes.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: List all network interfaces
  stevefulme1.unraid.interface_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: ifaces

- name: Show interface details
  ansible.builtin.debug:
    var: ifaces.interfaces

- name: Display only interfaces that are up
  ansible.builtin.debug:
    msg: "{{ item.name }} - {{ item.ipv4 }}"
  loop: "{{ ifaces.interfaces | selectattr('link_state', 'equalto', 'up') }}"
"""

RETURN = r"""
interfaces:
    description: List of network interfaces with details.
    returned: success
    type: list
    elements: dict
    contains:
        name:
            description: Interface name (e.g., C(eth0), C(br0), C(bond0)).
            type: str
        mac:
            description: MAC address of the interface.
            type: str
        ipv4:
            description: IPv4 address assigned to the interface.
            type: str
        ipv6:
            description: IPv6 address assigned to the interface.
            type: str
        link_state:
            description: Link state (e.g., C(up), C(down)).
            type: str
        mtu:
            description: Maximum transmission unit size.
            type: int
        speed:
            description: Link speed in Mbps.
            type: str
        type:
            description: Interface type (e.g., C(ethernet), C(bridge), C(bond), C(vlan)).
            type: str
    sample:
        - name: eth0
          mac: "00:11:22:33:44:55"
          ipv4: "192.168.1.10"
          ipv6: "fe80::1"
          link_state: up
          mtu: 1500
          speed: "1000"
          type: ethernet
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
        interfaces {
            name
            mac
            ipv4
            ipv6
            linkState
            mtu
            speed
            type
        }
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    try:
        client = get_client(module)
        data = client.query(QUERY)
        raw = data.get("network", {}).get("interfaces", [])
        interfaces = []
        for iface in raw:
            interfaces.append(
                dict(
                    name=iface.get("name"),
                    mac=iface.get("mac"),
                    ipv4=iface.get("ipv4"),
                    ipv6=iface.get("ipv6"),
                    link_state=iface.get("linkState"),
                    mtu=iface.get("mtu"),
                    speed=iface.get("speed"),
                    type=iface.get("type"),
                )
            )
        module.exit_json(changed=False, interfaces=interfaces)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
