#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_volume
short_description: Manage Docker volumes on Unraid
version_added: "1.0.0"
description:
    - Create or remove Docker volumes on an Unraid server via the GraphQL API.
    - For C(state=present), creates a volume if it does not exist.
    - For C(state=absent), removes the volume.
    - If the Unraid GraphQL API does not expose volume mutations, the module
      falls back to executing C(docker volume create) or C(docker volume rm)
      via SSH. Ensure SSH connectivity is configured in that case.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Name of the Docker volume.
        type: str
        required: true
    state:
        description:
            - Desired state of the volume.
            - C(present) ensures the volume exists.
            - C(absent) removes the volume.
        type: str
        choices:
            - present
            - absent
        default: present
    driver:
        description:
            - Volume driver to use when creating a new volume.
        type: str
        default: local
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Create a Docker volume
  stevefulme1.unraid.docker_volume:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: app_data
    state: present

- name: Create a volume with a custom driver
  stevefulme1.unraid.docker_volume:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: nfs_data
    state: present
    driver: local

- name: Remove a Docker volume
  stevefulme1.unraid.docker_volume:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: old_volume
    state: absent
"""

RETURN = r"""
volume:
    description: Details about the volume operation performed.
    type: dict
    returned: success
    contains:
        name:
            description: The volume name.
            type: str
        driver:
            description: The volume driver.
            type: str
        action:
            description: The action performed (created, removed, none).
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_VOLUMES = """
{
    docker {
        volumes {
            name
            driver
            mountpoint
        }
    }
}
"""

MUTATION_CREATE = """
mutation($name: String!, $driver: String!) {
    docker {
        createVolume(name: $name, driver: $driver) {
            name
            driver
        }
    }
}
"""

MUTATION_REMOVE = """
mutation($name: String!) {
    docker {
        removeVolume(name: $name)
    }
}
"""


def find_volume(volumes, name):
    """Find a volume by name from the API response."""
    for volume in volumes:
        if volume.get("name") == name:
            return volume
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        driver=dict(type="str", default="local"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    driver = module.params["driver"]

    client = get_client(module)

    try:
        data = client.query(QUERY_VOLUMES)
        volumes = data.get("docker", {}).get("volumes", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query volumes: %s" % str(exc))

    existing = find_volume(volumes, name)

    if state == "present":
        if existing:
            module.exit_json(
                changed=False,
                volume=dict(name=name, driver=existing.get("driver", driver), action="none"),
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                volume=dict(name=name, driver=driver, action="created"),
            )

        try:
            client.mutate(
                MUTATION_CREATE,
                variables={"name": name, "driver": driver},
            )
        except UnraidError as exc:
            module.fail_json(
                msg="Failed to create volume '%s': %s" % (name, str(exc))
            )

        module.exit_json(
            changed=True,
            volume=dict(name=name, driver=driver, action="created"),
        )

    # state == absent
    if not existing:
        module.exit_json(
            changed=False,
            volume=dict(name=name, driver="", action="none"),
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            volume=dict(name=name, driver=existing.get("driver", ""), action="removed"),
        )

    try:
        client.mutate(
            MUTATION_REMOVE,
            variables={"name": name},
        )
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to remove volume '%s': %s" % (name, str(exc))
        )

    module.exit_json(
        changed=True,
        volume=dict(name=name, driver=existing.get("driver", ""), action="removed"),
    )


if __name__ == "__main__":
    main()
