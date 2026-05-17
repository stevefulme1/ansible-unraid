#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: log_info
short_description: Query log files from an Unraid server
description:
    - Lists available log files or retrieves content of a specific log file.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
options:
    path:
        description:
            - Path of a specific log file to read.
            - If omitted, returns the list of available log files.
        type: str
    limit:
        description:
          - Maximum number of results to return.
        type: int
        default: 100
    offset:
        description:
          - Number of results to skip for pagination.
        type: int
        default: 0
"""

EXAMPLES = r"""
- name: List available log files
  stevefulme1.unraid.log_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
  register: logs

- name: Read syslog
  stevefulme1.unraid.log_info:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    path: /var/log/syslog
  register: syslog
"""

RETURN = r"""
log_files:
    description: List of available log file paths (when path is not specified).
    returned: when path is omitted
    type: list
    elements: str
    sample:
        - /var/log/syslog
        - /var/log/docker.log
content:
    description: Content of the requested log file.
    returned: when path is specified
    type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

LIST_QUERY = """
{
    logFiles
}
"""

READ_QUERY = """
query($path: String!) {
    logFile(path: $path)
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        path=dict(type="str"),
    )
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    try:
        client = get_client(module)
        path = module.params["path"]
        if path:
            data = client.query(READ_QUERY, variables={"path": path})
            module.exit_json(changed=False, content=data.get("logFile", ""))
        else:
            data = client.query(LIST_QUERY)
            module.exit_json(changed=False, log_files=data.get("logFiles", []))
    except UnraidError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
