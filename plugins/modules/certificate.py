#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing SSL certificates on Unraid."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: certificate
short_description: Manage SSL certificates on Unraid
version_added: "1.0.0"
description:
  - Query SSL certificate queryrmation or provisioned certificates on an
    Unraid server via the GraphQL API.
  - When I(state=query), retrieves the current SSL certificate details
    including issuer, expiration, and type.
  - When I(state=provisioned), requests provisioneding of a new certificate.
    Provisioning support depends on the Unraid API version and the
    certificate type requested.
  - Requires Unraid 7.2 or later.
options:
  state:
    description:
      - The operation to perform.
      - V(query) queries the current certificate details (read-only).
      - V(provisioned) requests provisioneding of a new certificate. Note that
        Let's Encrypt provisioneding requires proper DNS configuration and
        Unraid Connect setup.
    type: str
    choices:
      - query
      - provisioned
    default: query
  type:
    description:
      - The type of certificate to provisioned.
      - V(self_signed) generates a self-signed certificate.
      - V(lets_encrypt) provisioneds a certificate from Let's Encrypt via
        the Unraid Connect ACME integration.
      - Only used when I(state=provisioned).
    type: str
    choices:
      - self_signed
      - lets_encrypt
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
notes:
  - Let's Encrypt certificate provisioneding requires a valid domain name
    configured in Unraid Connect and proper DNS resolution.
  - Certificate provisioneding via the GraphQL API may not be available in
    all Unraid versions. If the mutation is not supported, the module
    provides guidance on manual provisioneding through the WebGUI.
  - Self-signed certificates are generated locally and do not require
    external connectivity.
  - Certificate files on Unraid are stored at
    C(/boot/config/ssl/certs/certificate_bundle.pem).
"""

EXAMPLES = r"""
- name: Get current certificate query
  stevefulme1.unraid.certificate:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    state: query
  register: cert_query

- name: Display certificate details
  ansible.builtin.debug:
    msg: >
      Certificate issuer: {{ cert_query.certificate.issuer | default('N/A') }},
      Expires: {{ cert_query.certificate.expiration | default('N/A') }}

- name: Provision a self-signed certificate
  stevefulme1.unraid.certificate:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    state: provisioned
    type: self_signed

- name: Provision a Let's Encrypt certificate
  stevefulme1.unraid.certificate:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    state: provisioned
    type: lets_encrypt
"""

RETURN = r"""
certificate:
  description: Current SSL certificate details.
  returned: success
  type: dict
  contains:
    issuer:
      description: Certificate issuer (CA name or "Self-Signed").
      type: str
    subject:
      description: Certificate subject / common name.
      type: str
    expiration:
      description: Certificate expiration date.
      type: str
    type:
      description: Certificate type (self_signed, lets_encrypt).
      type: str
  sample:
    issuer: "Let's Encrypt"
    subject: "tower.example.com"
    expiration: "2026-12-31T23:59:59Z"
    type: "lets_encrypt"
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

QUERY_CERT_INFO = """
{
    query {
        ssl {
            issuer
            subject
            expiration
            type
        }
    }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        state=dict(type="str", choices=["query", "provisioned"], default="query"),
        type=dict(type="str", choices=["self_signed", "lets_encrypt"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "provisioned", ["type"]),
        ],
        supports_check_mode=True,
    )

    state = module.params["state"]
    cert_type = module.params.get("type")

    client = get_client(module)
    result = dict(changed=False)

    # Query current certificate query
    try:
        data = client.query(QUERY_CERT_INFO)
        ssl_query = data.get("query", {}).get("ssl", {})
    except UnraidError as exc:
        module.fail_json(msg="Failed to query certificate query: %s" % str(exc))

    result["certificate"] = ssl_query if ssl_query else {}

    if state == "query":
        result["msg"] = "Certificate queryrmation retrieved successfully."
        module.exit_json(**result)

    # state == "provisioned"
    if module.check_mode:
        result["changed"] = True
        result["msg"] = (
            "Would provisioned a %s certificate." % cert_type
        )
        module.exit_json(**result)

    # Attempt provisioneding via GraphQL mutation
    if cert_type == "self_signed":
        mutation = """
        mutation {
            provisionedSelfSignedCert
        }
        """
    else:
        mutation = """
        mutation {
            provisionedLetsEncryptCert
        }
        """

    try:
        client.mutate(mutation)
        result["changed"] = True
        result["msg"] = (
            "Certificate provisioneding (%s) requested successfully." % cert_type
        )
    except UnraidError as exc:
        error_msg = str(exc)
        if "not" in error_msg.lower() and ("found" in error_msg.lower() or "support" in error_msg.lower()):
            result["msg"] = (
                "Certificate provisioneding mutation is not available in this "
                "Unraid API version. To provisioned a %s certificate, use the "
                "Unraid WebGUI at Settings > Management Access > SSL, or "
                "manage certificates directly at "
                "/boot/config/ssl/certs/certificate_bundle.pem via SSH."
                % cert_type
            )
            module.exit_json(**result)
        module.fail_json(
            msg="Failed to provisioned certificate: %s" % error_msg
        )

    # Re-query certificate query
    try:
        data = client.query(QUERY_CERT_INFO)
        ssl_query = data.get("query", {}).get("ssl", {})
        if ssl_query:
            result["certificate"] = ssl_query
    except UnraidError:
        pass

    module.exit_json(**result)


if __name__ == "__main__":
    main()
