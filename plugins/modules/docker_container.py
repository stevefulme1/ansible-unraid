#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_container
short_description: Manage Docker container lifecycle on Unraid
version_added: "1.0.0"
description:
    - Start, stop, restart, pause, unpause, update, or remove Docker
      containers on an Unraid server via the GraphQL API.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Name of the container.
            - At least one of O(name) or O(id) is required.
        type: str
    id:
        description:
            - Docker container ID (full or short).
            - At least one of O(name) or O(id) is required.
        type: str
    state:
        description:
            - Desired state of the container.
        type: str
        required: true
        choices:
            - started
            - stopped
            - restarted
            - paused
            - unpaused
            - absent
            - updated
    remove_image:
        description:
            - When O(state=absent), also remove the container image.
        type: bool
        default: false
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Start a container by name
  stevefulme1.unraid.docker_container:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: plex
    state: started

- name: Stop a container by ID
  stevefulme1.unraid.docker_container:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    id: abc123def456
    state: stopped

- name: Remove a container and its image
  stevefulme1.unraid.docker_container:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: old-container
    state: absent
    remove_image: true

- name: Restart a container
  stevefulme1.unraid.docker_container:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: nginx
    state: restarted

- name: Update a container to latest image
  stevefulme1.unraid.docker_container:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: grafana
    state: updated
"""

RETURN = r"""
container:
    description: Container details after the operation.
    type: dict
    returned: success
    contains:
        id:
            description: Docker container ID.
            type: str
        names:
            description: List of container names.
            type: list
            elements: str
        state:
            description: Current container state.
            type: str
        auto_start:
            description: Whether the container is set to auto-start.
            type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_CONTAINERS = """
{
    docker {
        containers {
            id
            names
            state
            autoStart
        }
    }
}
"""

# Map desired states to their GraphQL mutations
STATE_MUTATIONS = {
    "started": 'mutation($id: String!) { docker { start(id: $id) } }',
    "stopped": 'mutation($id: String!) { docker { stop(id: $id) } }',
    "restarted": 'mutation($id: String!) { docker { restart(id: $id) } }',
    "paused": 'mutation($id: String!) { docker { pause(id: $id) } }',
    "unpaused": 'mutation($id: String!) { docker { unpause(id: $id) } }',
    "updated": 'mutation($id: String!) { docker { updateContainer(id: $id) } }',
}

MUTATION_REMOVE = """
mutation($id: String!, $withImage: Boolean) {
    docker {
        removeContainer(id: $id, withImage: $withImage)
    }
}
"""

# Docker states as reported by the API
RUNNING_STATES = ("running",)
PAUSED_STATES = ("paused",)
STOPPED_STATES = ("exited", "created", "dead")


def find_container(containers, name=None, container_id=None):
    """Find a container by name or ID from the list returned by the API."""
    for container in containers:
        if container_id and container.get("id", "").startswith(container_id):
            return container
        if name:
            names = container.get("names", [])
            # Docker names may have a leading slash
            clean_names = [n.lstrip("/") for n in names]
            if name in clean_names or name in names:
                return container
    return None


def is_state_change_needed(current_state, desired_state):
    """Check whether a mutation is needed given the current container state."""
    current = (current_state or "").lower()

    if desired_state == "started":
        return current not in RUNNING_STATES
    if desired_state == "stopped":
        return current not in STOPPED_STATES
    if desired_state == "paused":
        return current not in PAUSED_STATES
    if desired_state == "unpaused":
        return current in PAUSED_STATES
    # restarted, updated, and absent always trigger a change
    return True


def run_module():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str"),
        id=dict(type="str"),
        state=dict(
            type="str",
            required=True,
            choices=[
                "started",
                "stopped",
                "restarted",
                "paused",
                "unpaused",
                "absent",
                "updated",
            ],
        ),
        remove_image=dict(type="bool", default=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["name", "id"]],
        supports_check_mode=True,
    )

    name = module.params["name"]
    container_id = module.params["id"]
    state = module.params["state"]
    remove_image = module.params["remove_image"]

    client = get_client(module)
    result = dict(changed=False)

    try:
        data = client.query(QUERY_CONTAINERS)
        containers = data.get("docker", {}).get("containers", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query containers: %s" % str(exc))

    container = find_container(containers, name=name, container_id=container_id)

    # For absent state, no container means already absent
    if state == "absent":
        if container is None:
            module.exit_json(**result)
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)
        try:
            client.mutate(
                MUTATION_REMOVE,
                variables={"id": container["id"], "withImage": remove_image},
            )
        except UnraidError as exc:
            module.fail_json(msg="Failed to remove container: %s" % str(exc))
        module.exit_json(**result)

    # All other states require the container to exist
    if container is None:
        identifier = name if name else container_id
        module.fail_json(msg="Container '%s' not found." % identifier)

    current_state = container.get("state", "")
    cid = container["id"]

    if not is_state_change_needed(current_state, state):
        result["container"] = container
        module.exit_json(**result)

    result["changed"] = True
    if module.check_mode:
        result["container"] = container
        module.exit_json(**result)

    mutation = STATE_MUTATIONS.get(state)
    try:
        client.mutate(mutation, variables={"id": cid})
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to set container to '%s': %s" % (state, str(exc))
        )

    # Re-query to return updated state
    try:
        data = client.query(QUERY_CONTAINERS)
        containers = data.get("docker", {}).get("containers", [])
        container = find_container(containers, container_id=cid)
    except UnraidError:
        pass  # Return what we had before

    if container:
        result["container"] = container
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
