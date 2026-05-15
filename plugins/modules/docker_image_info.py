#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_image_info
short_description: List Docker images on Unraid
version_added: "1.0.0"
description:
    - Retrieve information about Docker images available on an Unraid server
      via the GraphQL API.
    - Returns all locally available images with repository, tag, ID, and size.
    - If the GraphQL API does not expose image listing, the module falls back
      to documenting usage of C(docker images --format json) via SSH.
    - Requires Unraid 7.2 or later.
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: List all Docker images
  stevefulme1.unraid.docker_image_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: images

- name: Display image list
  ansible.builtin.debug:
    msg: "{{ item.repository }}:{{ item.tag }} ({{ item.size }})"
  loop: "{{ images.images }}"

- name: Find images by repository
  ansible.builtin.debug:
    msg: "Found {{ item.repository }}:{{ item.tag }}"
  loop: "{{ images.images | selectattr('repository', 'equalto', 'nginx') }}"
"""

RETURN = r"""
images:
    description: List of Docker images on the Unraid server.
    type: list
    elements: dict
    returned: success
    contains:
        id:
            description: Image ID.
            type: str
        repository:
            description: Image repository name.
            type: str
        tag:
            description: Image tag.
            type: str
        size:
            description: Image size in bytes.
            type: int
        created:
            description: Image creation timestamp.
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
            created
        }
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = get_client(module)

    try:
        data = client.query(QUERY_IMAGES)
        images = data.get("docker", {}).get("images", [])
    except UnraidError as exc:
        module.fail_json(msg="Failed to query images: %s" % str(exc))

    module.exit_json(changed=False, images=images)


if __name__ == "__main__":
    main()
