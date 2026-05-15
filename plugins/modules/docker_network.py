#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_network
short_description: Manage Docker networks on Unraid
version_added: "1.0.0"
description:
    - Create or remove Docker networks on an Unraid server via the
      GraphQL API.
    - Requires Unraid 7.2 or later.
    - Network creation uses the C(docker.createNetwork) mutation. If
      the Unraid API version does not support this mutation, creation
      will fail with a clear error message.
options:
    name:
        description:
            - Name of the Docker network.
        type: str
        required: true
    state:
        description:
            - Desired state of the network.
        type: str
        default: present
        choices:
            - present
            - absent
    driver:
        description:
            - Network driver to use when creating.
        type: str
        default: bridge
    subnet:
        description:
            - Subnet in CIDR notation (e.g. V(172.18.0.0/16)).
            - Only used when O(state=present) and the network does not
              already exist.
        type: str
    gateway:
        description:
            - Gateway IP address for the network.
            - Only used when O(state=present) and the network does not
              already exist.
        type: str
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Create a custom bridge network
  stevefulme1.unraid.docker_network:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: my_network
    state: present
    driver: bridge
    subnet: "172.18.0.0/16"
    gateway: "172.18.0.1"

- name: Ensure a network exists (defaults)
  stevefulme1.unraid.docker_network:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: app_network
    state: present

- name: Remove a Docker network
  stevefulme1.unraid.docker_network:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: old_network
    state: absent
"""

RETURN = r"""
network:
    description: Network details after the operation.
    type: dict
    returned: when state=present and network exists
    contains:
        id:
            description: Docker network ID.
            type: str
        name:
            description: Network name.
            type: str
        driver:
            description: Network driver.
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_NETWORKS = """
{
    docker {
        networks {
            id
            name
            driver
        }
    }
}
"""

MUTATION_CREATE_NETWORK = """
mutation($name: String!, $driver: String!, $subnet: String, $gateway: String) {
    docker {
        createNetwork(name: $name, driver: $driver, subnet: $subnet, gateway: $gateway)
    }
}
"""

MUTATION_REMOVE_NETWORK = """
mutation($id: String!) {
    docker {
        removeNetwork(id: $id)
    }
}
"""


def find_network(networks, name):
    """Find a network by name."""
    for network in networks:
        if network.get("name") == name:
            return network
    return None


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        driver=dict(type="str", default="bridge"),
        subnet=dict(type="str"),
        gateway=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    driver = module.params["driver"]
    subnet = module.params["subnet"]
    gateway = module.params["gateway"]

    client = get_client(module)
    result = dict(changed=False)

    try:
        data = client.query(QUERY_NETWORKS)
        networks = data.get("docker", {}).get("networks", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query networks: %s" % str(exc))

    network = find_network(networks, name)

    if state == "absent":
        if network is None:
            module.exit_json(**result)
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)
        try:
            client.mutate(
                MUTATION_REMOVE_NETWORK,
                variables={"id": network["id"]},
            )
        except UnraidError as exc:
            module.fail_json(msg="Failed to remove network '%s': %s" % (name, str(exc)))
        module.exit_json(**result)

    # state == present
    if network is not None:
        result["network"] = network
        module.exit_json(**result)

    result["changed"] = True
    if module.check_mode:
        result["network"] = {"name": name, "driver": driver}
        module.exit_json(**result)

    variables = {"name": name, "driver": driver}
    if subnet:
        variables["subnet"] = subnet
    if gateway:
        variables["gateway"] = gateway

    try:
        client.mutate(MUTATION_CREATE_NETWORK, variables=variables)
    except UnraidError as exc:
        msg = str(exc)
        # Provide a clear hint if the API does not support this mutation
        if "Cannot query field" in msg or "Unknown field" in msg:
            module.fail_json(
                msg=(
                    "The Unraid API does not appear to support the "
                    "createNetwork mutation. Network creation may not be "
                    "available in your Unraid version. Original error: %s"
                )
                % msg
            )
        module.fail_json(msg="Failed to create network '%s': %s" % (name, msg))

    # Re-query to return created network
    try:
        data = client.query(QUERY_NETWORKS)
        networks = data.get("docker", {}).get("networks", [])
        network = find_network(networks, name)
    except UnraidError:
        network = {"name": name, "driver": driver}

    if network:
        result["network"] = network
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
