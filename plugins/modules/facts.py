#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: facts
short_description: Gather facts about an Unraid server
description:
    - Queries the Unraid GraphQL API and returns system information,
      array status, disks, Docker containers, VMs, shares, UPS status,
      and notification overview as Ansible facts.
    - Facts are returned under C(ansible_facts.unraid).
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Gather all Unraid facts
  stevefulme1.unraid.facts:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false

- name: Display Unraid system info
  ansible.builtin.debug:
    var: ansible_facts.unraid.system

- name: Show array status
  ansible.builtin.debug:
    var: ansible_facts.unraid.array
"""

RETURN = r"""
ansible_facts:
    description: Dictionary of Unraid facts.
    returned: always
    type: dict
    contains:
        unraid:
            description: Top-level Unraid facts namespace.
            type: dict
            contains:
                system:
                    description: System information (hostname, version, uptime, etc.).
                    type: dict
                array:
                    description: Array status and configuration.
                    type: dict
                disks:
                    description: List of disk objects with device, status, size, etc.
                    type: list
                    elements: dict
                docker_containers:
                    description: List of Docker containers and their states.
                    type: list
                    elements: dict
                vms:
                    description: List of virtual machines and their states.
                    type: list
                    elements: dict
                shares:
                    description: List of user shares.
                    type: list
                    elements: dict
                ups:
                    description: UPS status information.
                    type: dict
                notifications:
                    description: Notification overview (counts by level).
                    type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_SYSTEM = """
{
    info {
        os {
            hostname
            version
            uptime
        }
        cpu {
            model
            cores
        }
        memory {
            total
            used
            free
        }
        versions {
            unraid
            kernel
        }
    }
}
"""

QUERY_ARRAY = """
{
    array {
        state
        capacity {
            total
            used
            free
        }
        parity {
            status
            progress
            lastCheck
        }
    }
}
"""

QUERY_DISKS = """
{
    disks {
        id
        name
        device
        size
        status
        temperature
        type
        fsType
        mounted
    }
}
"""

QUERY_DOCKER = """
{
    docker {
        containers {
            id
            name
            state
            status
            image
            autoStart
        }
    }
}
"""

QUERY_VMS = """
{
    vms {
        domain {
            name
            uuid
            state
            autoStart
            vcpus
            memory
        }
    }
}
"""

QUERY_SHARES = """
{
    shares {
        name
        comment
        free
        used
        size
        useCache
    }
}
"""

QUERY_UPS = """
{
    ups {
        status
        model
        battery {
            charge
            runtime
        }
        nominal {
            power
        }
    }
}
"""

QUERY_NOTIFICATIONS = """
{
    notifications {
        overview {
            unread
            total
            alert
            warning
            notice
            info
        }
    }
}
"""


def _safe_query(client, query, label):
    """Run a query and return data or empty dict on error."""
    try:
        return client.query(query)
    except UnraidError:
        return {}


def run_module():
    argument_spec = unraid_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    facts = {}

    # System info
    data = _safe_query(client, QUERY_SYSTEM, "system")
    facts["system"] = data.get("info", {})

    # Array
    data = _safe_query(client, QUERY_ARRAY, "array")
    facts["array"] = data.get("array", {})

    # Disks
    data = _safe_query(client, QUERY_DISKS, "disks")
    facts["disks"] = data.get("disks", [])

    # Docker containers
    data = _safe_query(client, QUERY_DOCKER, "docker")
    docker = data.get("docker", {})
    facts["docker_containers"] = docker.get("containers", [])

    # VMs
    data = _safe_query(client, QUERY_VMS, "vms")
    vms = data.get("vms", {})
    facts["vms"] = vms.get("domain", []) if isinstance(vms, dict) else vms

    # Shares
    data = _safe_query(client, QUERY_SHARES, "shares")
    facts["shares"] = data.get("shares", [])

    # UPS
    data = _safe_query(client, QUERY_UPS, "ups")
    facts["ups"] = data.get("ups", {})

    # Notifications
    data = _safe_query(client, QUERY_NOTIFICATIONS, "notifications")
    notif = data.get("notifications", {})
    facts["notifications"] = notif.get("overview", {})

    module.exit_json(
        changed=False,
        ansible_facts=dict(unraid=facts),
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
