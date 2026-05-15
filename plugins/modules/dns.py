#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns
short_description: Configure DNS servers on Unraid
description:
    - Configure the DNS nameservers used by an Unraid server via the
      GraphQL API.
    - DNS settings are persisted to C(/boot/config/network.cfg) so they
      survive reboots.
    - Compares current DNS configuration against desired state and only
      applies changes when necessary.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    nameservers:
        description:
            - List of DNS nameserver IP addresses to configure.
            - Order is preserved and determines resolution priority.
        type: list
        elements: str
        required: true
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Set DNS to Cloudflare
  stevefulme1.unraid.dns:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    nameservers:
      - 1.1.1.1
      - 1.0.0.1

- name: Set DNS to local Pi-hole and Google fallback
  stevefulme1.unraid.dns:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    nameservers:
      - 192.168.1.53
      - 8.8.8.8
      - 8.8.4.4
"""

RETURN = r"""
nameservers:
    description: The configured DNS nameservers after changes.
    returned: success
    type: list
    elements: str
    sample:
        - "1.1.1.1"
        - "1.0.0.1"
diff:
    description: Configuration differences that were applied.
    returned: changed
    type: dict
    contains:
        before:
            description: Previous DNS nameservers.
            type: dict
        after:
            description: New DNS nameservers.
            type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_DNS = """
{
    network {
        dns {
            nameservers
        }
    }
}
"""

MUTATION_SET_DNS = """
mutation($input: DnsInput!) {
    setDns(input: $input)
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        nameservers=dict(type="list", elements="str", required=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    nameservers = module.params["nameservers"]

    if not nameservers:
        module.fail_json(msg="At least one nameserver must be provided")

    try:
        client = get_client(module)
        data = client.query(QUERY_DNS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query DNS configuration: {exc}")

    current = data.get("network", {}).get("dns", {}).get("nameservers", [])

    if current == nameservers:
        module.exit_json(changed=False, nameservers=current)
        return

    diff = {
        "before": {"nameservers": current},
        "after": {"nameservers": nameservers},
    }

    if module.check_mode:
        module.exit_json(changed=True, nameservers=nameservers, diff=diff)
        return

    try:
        client.mutate(
            MUTATION_SET_DNS,
            variables={"input": {"nameservers": nameservers}},
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to update DNS configuration: {exc}")

    module.exit_json(changed=True, nameservers=nameservers, diff=diff)


if __name__ == "__main__":
    main()
