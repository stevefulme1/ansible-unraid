#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing global NFS configuration on Unraid."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: nfs_config
short_description: Manage global NFS configuration on Unraid
version_added: "1.0.0"
description:
  - Query and configure global NFS (Network File System) settings on an
    Unraid server.
  - This module queries the current NFS configuration via the GraphQL API
    and attempts to apply changes through GraphQL mutations when available.
  - If mutations are not supported in the current API version, the module
    provides guidance on configuring NFS via the Unraid WebGUI or by
    editing configuration files directly.
  - NFS exports for individual shares are configured per-share; this
    module manages global NFS daemon settings.
  - Requires Unraid 7.2 or later.
options:
  enabled:
    description:
      - Enable or disable the NFS service globally.
      - When V(false), all NFS exports are stopped and the NFS daemon
        is shut down.
    type: bool
  tuning:
    description:
      - NFS tuning parameters as a dictionary.
      - Available tuning options depend on the Unraid version and NFS
        server configuration.
      - Common tuning keys include C(nfs_threads) (number of NFS server
        threads), C(nfs_version) (NFS protocol version to serve), and
        C(nfs_fuse) (enable FUSE-based NFS for user shares).
    type: dict
    suboptions:
      nfs_threads:
        description:
          - Number of NFS server threads.
          - More threads improve concurrent client performance.
          - Typical values range from 8 to 64.
        type: int
      nfs_version:
        description:
          - NFS protocol version to serve.
          - V(3) serves NFSv3 only.
          - V(4) serves NFSv4 (also supports v3 clients).
        type: str
        choices: ["3", "4"]
      nfs_fuse:
        description:
          - Enable FUSE-based NFS for user shares.
          - Required for proper NFS export of user shares that span
            multiple disks.
        type: bool
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - At least one of I(enabled) or I(tuning) must be provided.
  - The Unraid GraphQL API may not support all NFS configuration mutations
    in every version. When mutations are unavailable, configure settings
    through the Unraid WebGUI at C(Settings > NFS) or edit configuration
    files directly via SSH.
  - NFS exports for individual shares are managed through the share
    configuration, not this module. Use M(stevefulme1.unraid.share) for
    per-share NFS export settings.
  - The NFS configuration file on Unraid is located at
    C(/boot/config/nfs.cfg). Additional NFS exports can be configured
    in C(/etc/exports) but Unraid regenerates this file from its settings.
  - Changes may require an NFS service restart. The module does not
    automatically restart the NFS service.
"""

EXAMPLES = r"""
- name: Enable NFS
  stevefulme1.unraid.nfs_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    enabled: true

- name: Disable NFS
  stevefulme1.unraid.nfs_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    enabled: false

- name: Configure NFS tuning parameters
  stevefulme1.unraid.nfs_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    tuning:
      nfs_threads: 16
      nfs_version: "4"

- name: Enable NFS with tuning
  stevefulme1.unraid.nfs_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    enabled: true
    tuning:
      nfs_threads: 32
      nfs_fuse: true

- name: Set NFS to v3 only
  stevefulme1.unraid.nfs_config:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    tuning:
      nfs_version: "3"
"""

RETURN = r"""
config:
  description: Current NFS configuration after any changes.
  returned: success
  type: dict
  contains:
    enabled:
      description: Whether the NFS service is enabled.
      type: bool
    nfsThreads:
      description: Number of NFS server threads.
      type: int
    nfsVersion:
      description: NFS protocol version.
      type: str
    nfsFuse:
      description: Whether FUSE-based NFS is enabled.
      type: bool
  sample:
    enabled: true
    nfsThreads: 16
    nfsVersion: "4"
    nfsFuse: true
msg:
  description: Human-readable result message.
  returned: always
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_NFS_CONFIG = """
{
    nfsConfig {
        enabled
        nfsThreads
        nfsVersion
        nfsFuse
    }
}
"""

MUTATION_NFS_CONFIG = """
mutation($input: NfsConfigInput!) {
    setNfsConfig(input: $input) {
        enabled
        nfsThreads
        nfsVersion
        nfsFuse
    }
}
"""

# Mapping from tuning dict keys to GraphQL field names
TUNING_TO_FIELD = {
    "nfs_threads": "nfsThreads",
    "nfs_version": "nfsVersion",
    "nfs_fuse": "nfsFuse",
}


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        enabled=dict(type="bool"),
        tuning=dict(
            type="dict",
            options=dict(
                nfs_threads=dict(type="int"),
                nfs_version=dict(type="str", choices=["3", "4"]),
                nfs_fuse=dict(type="bool"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["enabled", "tuning"]],
        supports_check_mode=True,
    )

    enabled = module.params.get("enabled")
    tuning = module.params.get("tuning") or {}

    client = get_client(module)
    result = dict(changed=False)

    # Query current config
    current_config = {}
    try:
        data = client.query(QUERY_NFS_CONFIG)
        current_config = data.get("nfsConfig", {})
    except UnraidError:
        # API may not support this query; proceed with empty config
        pass

    # Build mutation input
    mutation_input = {}

    if enabled is not None:
        if current_config.get("enabled") != enabled:
            mutation_input["enabled"] = enabled

    for tuning_key, field_name in TUNING_TO_FIELD.items():
        value = tuning.get(tuning_key)
        if value is not None:
            current_value = current_config.get(field_name)
            if current_value != value:
                mutation_input[field_name] = value

    if not mutation_input:
        result["config"] = current_config
        result["msg"] = "NFS configuration is already in the desired state."
        module.exit_json(**result)

    result["changed"] = True
    if module.check_mode:
        result["config"] = current_config
        result["msg"] = "Would update NFS settings: %s." % ", ".join(
            mutation_input.keys()
        )
        module.exit_json(**result)

    # Apply changes via mutation
    try:
        data = client.mutate(MUTATION_NFS_CONFIG, variables={"input": mutation_input})
        updated_config = data.get("setNfsConfig", {})
        result["config"] = updated_config if updated_config else current_config
        result["msg"] = "NFS configuration updated: %s." % ", ".join(
            mutation_input.keys()
        )
    except UnraidError as exc:
        error_msg = str(exc)
        result["config"] = current_config
        result["msg"] = (
            "NFS configuration mutation is not available in this Unraid API "
            "version (%s). Configure NFS settings through the Unraid WebGUI "
            "at Settings > NFS, or edit /boot/config/nfs.cfg via SSH."
            % error_msg
        )
        # Still report changed=True since we could not verify
        result["changed"] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
