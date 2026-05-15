#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_compose
short_description: Manage Docker Compose stacks on Unraid
version_added: "1.0.0"
description:
    - Start or stop Docker Compose stacks on an Unraid server via the
      GraphQL API.
    - Uses C(docker compose up -d) and C(docker compose down) operations
      through the Unraid API.
    - The compose file must already exist on the Unraid server at the
      specified path.
    - Requires Unraid 7.2 or later with Docker Compose support enabled.
options:
    project:
        description:
            - Name of the Docker Compose project (stack).
            - Used as the C(--project-name) argument for Compose commands.
        type: str
        required: true
    state:
        description:
            - Desired state of the Compose stack.
            - C(up) starts all services defined in the compose file.
            - C(down) stops and removes all services.
        type: str
        required: true
        choices:
            - up
            - down
    file:
        description:
            - Path to the Docker Compose file on the Unraid server.
            - Must be an absolute path.
            - If not specified, Docker Compose looks for C(docker-compose.yml)
              or C(compose.yml) in the project directory.
        type: str
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Start a Compose stack
  stevefulme1.unraid.docker_compose:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    project: media-stack
    state: up
    file: /boot/config/compose/media-stack/docker-compose.yml

- name: Stop a Compose stack
  stevefulme1.unraid.docker_compose:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    project: media-stack
    state: down

- name: Deploy monitoring stack
  stevefulme1.unraid.docker_compose:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    project: monitoring
    state: up
    file: /mnt/user/appdata/monitoring/docker-compose.yml
"""

RETURN = r"""
compose:
    description: Details about the Compose operation performed.
    type: dict
    returned: success
    contains:
        project:
            description: The Compose project name.
            type: str
        state:
            description: The state that was applied (up or down).
            type: str
        file:
            description: The compose file path used, if specified.
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_COMPOSE_UP = """
mutation($project: String!, $file: String) {
    docker {
        composeUp(project: $project, file: $file)
    }
}
"""

MUTATION_COMPOSE_DOWN = """
mutation($project: String!, $file: String) {
    docker {
        composeDown(project: $project, file: $file)
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        project=dict(type="str", required=True),
        state=dict(type="str", required=True, choices=["up", "down"]),
        file=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    project = module.params["project"]
    state = module.params["state"]
    compose_file = module.params["file"]

    result = dict(
        changed=True,
        compose=dict(
            project=project,
            state=state,
            file=compose_file or "",
        ),
    )

    if module.check_mode:
        module.exit_json(**result)

    client = get_client(module)

    variables = {"project": project}
    if compose_file:
        variables["file"] = compose_file

    if state == "up":
        mutation = MUTATION_COMPOSE_UP
    else:
        mutation = MUTATION_COMPOSE_DOWN

    try:
        client.mutate(mutation, variables=variables)
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to run compose %s for project '%s': %s"
            % (state, project, str(exc))
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
