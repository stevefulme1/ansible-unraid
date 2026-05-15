# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment:
    DOCUMENTATION = r"""
options:
    api_url:
        description:
            - URL of the Unraid server (e.g. C(https://192.168.1.10) or C(https://tower.local)).
            - The C(/graphql) path is appended automatically.
        type: str
        required: true
        env:
            - name: UNRAID_API_URL
    api_key:
        description:
            - API key for authenticating with the Unraid GraphQL API.
            - Create keys in Settings > Management Access > API Keys.
            - Requires Unraid 7.2 or later.
        type: str
        required: true
        env:
            - name: UNRAID_API_KEY
    validate_certs:
        description:
            - Whether to validate SSL/TLS certificates.
            - Set to C(false) when using self-signed certificates.
        type: bool
        default: true
        env:
            - name: UNRAID_VALIDATE_CERTS
    api_timeout:
        description:
            - Timeout in seconds for API requests.
        type: int
        default: 30
        env:
            - name: UNRAID_API_TIMEOUT
"""
