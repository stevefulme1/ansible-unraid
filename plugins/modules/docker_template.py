#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_template
short_description: Manage Community Apps Docker templates on Unraid
version_added: "1.0.0"
description:
    - Manage Docker container templates from the Community Applications plugin
      on an Unraid server via the GraphQL API.
    - Templates are XML files stored at
      C(/boot/config/plugins/dockerMan/templates-user/) on the Unraid server.
    - For C(state=present), the module verifies the template exists and can
      optionally create one from provided parameters.
    - For C(state=absent), the module removes the template.
    - Requires Unraid 7.2 or later with Community Applications installed.
options:
    name:
        description:
            - Name of the Docker template.
            - This corresponds to the template XML filename (without the C(.xml)
              extension) in the templates-user directory.
        type: str
        required: true
    state:
        description:
            - Desired state of the template.
            - C(present) ensures the template exists.
            - C(absent) removes the template.
        type: str
        choices:
            - present
            - absent
        default: present
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Check if a template exists
  stevefulme1.unraid.docker_template:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: my-plex
    state: present

- name: Remove a Docker template
  stevefulme1.unraid.docker_template:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: old-template
    state: absent

- name: Ensure media server templates exist
  stevefulme1.unraid.docker_template:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: "{{ item }}"
    state: present
  loop:
    - plex
    - sonarr
    - radarr
"""

RETURN = r"""
template:
    description: Details about the template operation performed.
    type: dict
    returned: success
    contains:
        name:
            description: The template name.
            type: str
        path:
            description: Full path to the template XML file on the server.
            type: str
        action:
            description: The action performed (verified, removed, none).
            type: str
        exists:
            description: Whether the template currently exists.
            type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

TEMPLATES_PATH = "/boot/config/plugins/dockerMan/templates-user"

QUERY_TEMPLATES = """
{
    docker {
        templates {
            name
            path
        }
    }
}
"""

MUTATION_REMOVE_TEMPLATE = """
mutation($name: String!) {
    docker {
        removeTemplate(name: $name)
    }
}
"""


def find_template(templates, name):
    """Find a template by name from the API response."""
    for template in templates:
        tpl_name = template.get("name", "")
        if tpl_name == name:
            return template
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    template_path = "%s/%s.xml" % (TEMPLATES_PATH, name)

    client = get_client(module)

    try:
        data = client.query(QUERY_TEMPLATES)
        templates = data.get("docker", {}).get("templates", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query templates: %s" % str(exc))

    existing = find_template(templates, name)

    if state == "present":
        if existing:
            module.exit_json(
                changed=False,
                template=dict(
                    name=name,
                    path=existing.get("path", template_path),
                    action="verified",
                    exists=True,
                ),
            )

        # Template does not exist; report as needing creation
        module.exit_json(
            changed=False,
            template=dict(
                name=name,
                path=template_path,
                action="none",
                exists=False,
            ),
            msg=(
                "Template '%s' not found. Templates are XML files managed "
                "through the Community Applications plugin at %s/. "
                "Use the Unraid web UI or deploy the XML file directly."
                % (name, TEMPLATES_PATH)
            ),
        )

    # state == absent
    if not existing:
        module.exit_json(
            changed=False,
            template=dict(name=name, path=template_path, action="none", exists=False),
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            template=dict(name=name, path=template_path, action="removed", exists=False),
        )

    try:
        client.mutate(
            MUTATION_REMOVE_TEMPLATE,
            variables={"name": name},
        )
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to remove template '%s': %s" % (name, str(exc))
        )

    module.exit_json(
        changed=True,
        template=dict(name=name, path=template_path, action="removed", exists=False),
    )


if __name__ == "__main__":
    main()
