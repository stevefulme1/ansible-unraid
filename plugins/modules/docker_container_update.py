#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: docker_container_update
short_description: Update all Docker containers to latest images on Unraid
version_added: "1.0.0"
description:
    - Pull the latest images for all Docker containers on an Unraid server
      and recreate them.
    - This is a bulk operation that updates every container at once.
    - Requires Unraid 7.2 or later.
    - This module always reports C(changed=true) because there is no
      efficient way to determine whether new images are available
      without pulling them.
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Update all Docker containers to latest images
  stevefulme1.unraid.docker_container_update:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"

- name: Update containers with a longer timeout
  stevefulme1.unraid.docker_container_update:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    api_timeout: 300
"""

RETURN = r"""
msg:
    description: Status message describing the result.
    type: str
    returned: always
    sample: "All containers updated successfully."
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

MUTATION_UPDATE_ALL = """
mutation {
    docker {
        updateAllContainers
    }
}
"""


def run_module():
    argument_spec = unraid_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    result = dict(changed=True, msg="")

    if module.check_mode:
        result["msg"] = "Would update all Docker containers (check mode)."
        module.exit_json(**result)

    client = get_client(module)

    try:
        client.mutate(MUTATION_UPDATE_ALL)
    except UnraidError as exc:
        module.fail_json(msg="Failed to update containers: %s" % str(exc))

    result["msg"] = "All containers updated successfully."
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
