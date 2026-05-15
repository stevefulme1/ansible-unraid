# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared utilities for Unraid Ansible modules.

Provides the GraphQL client, authentication helpers, and common
argument spec used by all modules in the collection.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils.urls import open_url
from ansible.module_utils.basic import env_fallback


class UnraidError(Exception):
    """Exception raised by UnraidClient on API failures."""

    def __init__(self, message, status_code=None, errors=None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class UnraidClient:
    """GraphQL client for the Unraid API (7.2+)."""

    def __init__(self, api_url, api_key, validate_certs=True, timeout=30):
        self.api_url = api_url.rstrip("/")
        if not self.api_url.endswith("/graphql"):
            self.api_url += "/graphql"
        self.api_key = api_key
        self.validate_certs = validate_certs
        self.timeout = timeout

    def _request(self, payload):
        """Send a GraphQL request and return the parsed response."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        data = json.dumps(payload).encode("utf-8")

        try:
            response = open_url(
                self.api_url,
                data=data,
                headers=headers,
                method="POST",
                validate_certs=self.validate_certs,
                timeout=self.timeout,
            )
            body = json.loads(response.read())
        except Exception as exc:
            raise UnraidError(
                f"Failed to connect to Unraid API at {self.api_url}: {exc}"
            ) from exc

        if "errors" in body and body["errors"]:
            messages = "; ".join(
                e.get("message", str(e)) for e in body["errors"]
            )
            raise UnraidError(
                f"GraphQL error: {messages}",
                errors=body["errors"],
            )

        return body.get("data", {})

    def query(self, query, variables=None):
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        return self._request(payload)

    def mutate(self, mutation, variables=None):
        """Execute a GraphQL mutation."""
        return self.query(mutation, variables)


def unraid_argument_spec():
    """Return the common argument spec shared by all Unraid modules."""
    return dict(
        api_url=dict(
            type="str",
            required=True,
            fallback=(env_fallback, ["UNRAID_API_URL"]),
        ),
        api_key=dict(
            type="str",
            required=True,
            no_log=True,
            fallback=(env_fallback, ["UNRAID_API_KEY"]),
        ),
        validate_certs=dict(
            type="bool",
            default=True,
            fallback=(env_fallback, ["UNRAID_VALIDATE_CERTS"]),
        ),
        api_timeout=dict(
            type="int",
            default=30,
            fallback=(env_fallback, ["UNRAID_API_TIMEOUT"]),
        ),
    )


def get_client(module):
    """Instantiate an UnraidClient from module params."""
    return UnraidClient(
        api_url=module.params["api_url"],
        api_key=module.params["api_key"],
        validate_certs=module.params["validate_certs"],
        timeout=module.params["api_timeout"],
    )
