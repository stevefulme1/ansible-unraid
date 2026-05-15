# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
name: unraid_inventory
short_description: Dynamic inventory from Unraid VMs and Docker containers
description:
    - Builds an Ansible inventory from VMs and Docker containers running on Unraid.
    - Creates groups for VMs (running, stopped) and Docker containers (running, stopped).
    - Requires Unraid 7.2+ with the GraphQL API.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    api_url:
        description: URL of the Unraid server.
        type: str
        required: true
        env:
            - name: UNRAID_API_URL
    api_key:
        description: API key for authentication.
        type: str
        required: true
        env:
            - name: UNRAID_API_KEY
    validate_certs:
        description: Whether to validate SSL certificates.
        type: bool
        default: true
        env:
            - name: UNRAID_VALIDATE_CERTS
    include_vms:
        description: Whether to include VMs in the inventory.
        type: bool
        default: true
    include_docker:
        description: Whether to include Docker containers in the inventory.
        type: bool
        default: true
"""

EXAMPLES = r"""
# unraid.yml
plugin: stevefulme1.unraid.unraid_inventory
api_url: https://tower.local
api_key: !vault |
    $ANSIBLE_VAULT;1.1;AES256
    ...
include_vms: true
include_docker: true
"""

import json

from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.module_utils.urls import open_url


class InventoryModule(BaseInventoryPlugin):
    NAME = "stevefulme1.unraid.unraid_inventory"

    VM_QUERY = "{ vms { id name state } }"
    DOCKER_QUERY = (
        "{ docker { containers { id names state autoStart } } }"
    )

    def verify_file(self, path):
        if super().verify_file(path):
            return path.endswith(("unraid.yml", "unraid.yaml"))
        return False

    def parse(self, inventory, loader, path, cache=True):
        super().parse(inventory, loader, path, cache)
        self._read_config_data(path)

        api_url = self.get_option("api_url").rstrip("/")
        if not api_url.endswith("/graphql"):
            api_url += "/graphql"
        api_key = self.get_option("api_key")
        validate_certs = self.get_option("validate_certs")

        if self.get_option("include_vms"):
            self._add_vms(api_url, api_key, validate_certs)

        if self.get_option("include_docker"):
            self._add_docker(api_url, api_key, validate_certs)

    def _graphql(self, api_url, api_key, validate_certs, query):
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        payload = json.dumps({"query": query}).encode("utf-8")
        response = open_url(
            api_url,
            data=payload,
            headers=headers,
            method="POST",
            validate_certs=validate_certs,
        )
        return json.loads(response.read()).get("data", {})

    def _add_vms(self, api_url, api_key, validate_certs):
        data = self._graphql(api_url, api_key, validate_certs, self.VM_QUERY)
        vms = data.get("vms", [])

        self.inventory.add_group("unraid_vms")
        self.inventory.add_group("unraid_vms_running")
        self.inventory.add_group("unraid_vms_stopped")

        for vm in vms:
            name = vm.get("name", vm.get("id", "unknown"))
            self.inventory.add_host(name, group="unraid_vms")
            self.inventory.set_variable(name, "vm_id", vm.get("id"))
            self.inventory.set_variable(name, "vm_state", vm.get("state"))

            state = (vm.get("state") or "").lower()
            if state in ("running", "started"):
                self.inventory.add_host(name, group="unraid_vms_running")
            else:
                self.inventory.add_host(name, group="unraid_vms_stopped")

    def _add_docker(self, api_url, api_key, validate_certs):
        data = self._graphql(
            api_url, api_key, validate_certs, self.DOCKER_QUERY
        )
        containers = data.get("docker", {}).get("containers", [])

        self.inventory.add_group("unraid_docker")
        self.inventory.add_group("unraid_docker_running")
        self.inventory.add_group("unraid_docker_stopped")

        for ctr in containers:
            names = ctr.get("names", [])
            name = names[0].lstrip("/") if names else ctr.get("id", "unknown")
            self.inventory.add_host(name, group="unraid_docker")
            self.inventory.set_variable(name, "container_id", ctr.get("id"))
            self.inventory.set_variable(name, "container_state", ctr.get("state"))
            self.inventory.set_variable(name, "container_autostart", ctr.get("autoStart"))

            state = (ctr.get("state") or "").lower()
            if state == "running":
                self.inventory.add_host(name, group="unraid_docker_running")
            else:
                self.inventory.add_host(name, group="unraid_docker_stopped")
