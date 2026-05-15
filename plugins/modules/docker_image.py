#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_image
short_description: Manage Docker images on Unraid
version_added: "1.0.0"
description:
    - Pull or remove Docker images on an Unraid server.
    - For C(state=present), the module checks whether the image already exists
      and pulls it via the Unraid GraphQL API if it does not.
    - For C(state=absent), the module removes the image via the GraphQL API.
    - Requires Unraid 7.2 or later.
options:
    name:
        description:
            - Full image name including tag (e.g. C(nginx:latest), C(linuxserver/plex:latest)).
            - If no tag is specified, C(latest) is assumed.
        type: str
        required: true
    state:
        description:
            - Desired state of the image.
            - C(present) ensures the image is available locally.
            - C(absent) removes the image.
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
- name: Pull an image
  stevefulme1.unraid.docker_image:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: nginx:latest
    state: present

- name: Remove an image
  stevefulme1.unraid.docker_image:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: nginx:latest
    state: absent

- name: Ensure linuxserver/plex is pulled
  stevefulme1.unraid.docker_image:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: linuxserver/plex:latest
"""

RETURN = r"""
image:
    description: Details about the image operation performed.
    type: dict
    returned: success
    contains:
        name:
            description: The full image name with tag.
            type: str
        action:
            description: The action performed (pulled, removed, none).
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_IMAGES = """
{
    docker {
        images {
            id
            repository
            tag
            size
        }
    }
}
"""

MUTATION_PULL = """
mutation($repository: String!, $tag: String!) {
    docker {
        pullImage(repository: $repository, tag: $tag)
    }
}
"""

MUTATION_REMOVE = """
mutation($id: String!) {
    docker {
        removeImage(id: $id)
    }
}
"""


def parse_image_name(name):
    """Split an image name into repository and tag."""
    if ":" in name:
        repo, tag = name.rsplit(":", 1)
    else:
        repo = name
        tag = "latest"
    return repo, tag


def find_image(images, repository, tag):
    """Find an image by repository and tag from the API response."""
    for image in images:
        img_repo = image.get("repository", "")
        img_tag = image.get("tag", "")
        if img_repo == repository and img_tag == tag:
            return image
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
    repository, tag = parse_image_name(name)

    client = get_client(module)

    try:
        data = client.query(QUERY_IMAGES)
        images = data.get("docker", {}).get("images", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query images: %s" % str(exc))

    existing = find_image(images, repository, tag)

    if state == "present":
        if existing:
            module.exit_json(
                changed=False,
                image=dict(name=name, action="none"),
            )

        if module.check_mode:
            module.exit_json(
                changed=True,
                image=dict(name=name, action="pulled"),
            )

        try:
            client.mutate(
                MUTATION_PULL,
                variables={"repository": repository, "tag": tag},
            )
        except UnraidError as exc:
            module.fail_json(msg="Failed to pull image '%s': %s" % (name, str(exc)))

        module.exit_json(
            changed=True,
            image=dict(name=name, action="pulled"),
        )

    # state == absent
    if not existing:
        module.exit_json(
            changed=False,
            image=dict(name=name, action="none"),
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            image=dict(name=name, action="removed"),
        )

    try:
        client.mutate(
            MUTATION_REMOVE,
            variables={"id": existing["id"]},
        )
    except UnraidError as exc:
        module.fail_json(msg="Failed to remove image '%s': %s" % (name, str(exc)))

    module.exit_json(
        changed=True,
        image=dict(name=name, action="removed"),
    )


if __name__ == "__main__":
    main()
