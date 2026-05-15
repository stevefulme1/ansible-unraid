#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for managing Unraid notifications."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: notification
short_description: Manage notifications on Unraid
version_added: "1.0.0"
description:
  - Create, archive, and delete notifications on an Unraid server via the
    GraphQL API.
  - Use C(state=present) to create a new notification.
  - Use C(state=archived) to archive an existing notification by ID.
  - Use C(state=absent) to delete an existing notification by ID.
options:
  state:
    description:
      - The desired state of the notification.
      - C(present) creates a new notification (requires I(subject) and I(importance)).
      - C(archived) archives an existing notification (requires I(id)).
      - C(absent) deletes an existing notification (requires I(id)).
    type: str
    choices: [present, archived, absent]
    default: present
  importance:
    description:
      - The importance level of the notification.
      - Required when I(state=present).
    type: str
    choices: [alert, warning, normal, info]
    required: false
  subject:
    description:
      - The subject line of the notification.
      - Required when I(state=present).
    type: str
    required: false
  description:
    description:
      - The body text of the notification.
      - Only used when I(state=present).
    type: str
    required: false
  id:
    description:
      - The unique identifier of an existing notification.
      - Required when I(state=archived) or I(state=absent).
    type: str
    required: false
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Create an alert notification
  stevefulme1.unraid.notification:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    state: present
    importance: alert
    subject: "Disk temperature warning"
    description: "Disk 1 temperature exceeded 50C"

- name: Archive a notification
  stevefulme1.unraid.notification:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    state: archived
    id: "notification-123"

- name: Delete a notification
  stevefulme1.unraid.notification:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    state: absent
    id: "notification-123"
"""

RETURN = r"""
notification:
  description: Details about the notification action performed.
  returned: success
  type: dict
  contains:
    id:
      description: The notification ID (when archived or deleted).
      type: str
    subject:
      description: The notification subject (when created).
      type: str
    importance:
      description: The notification importance level (when created).
      type: str
    action:
      description: The action performed (created, archived, deleted).
      type: str
  sample:
    subject: "Disk temperature warning"
    importance: "alert"
    action: "created"
"""

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)
from ansible.module_utils.basic import AnsibleModule


CREATE_NOTIFICATION = """
mutation($input: NotificationInput!) {
  createNotification(input: $input)
}
"""

ARCHIVE_NOTIFICATION = """
mutation($id: String!) {
  archiveNotification(id: $id)
}
"""

DELETE_NOTIFICATION = """
mutation($id: String!) {
  deleteNotification(id: $id)
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        state=dict(
            type="str",
            choices=["present", "archived", "absent"],
            default="present",
        ),
        importance=dict(
            type="str",
            choices=["alert", "warning", "normal", "info"],
            required=False,
        ),
        subject=dict(type="str", required=False),
        description=dict(type="str", required=False),
        id=dict(type="str", required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["subject", "importance"]),
            ("state", "archived", ["id"]),
            ("state", "absent", ["id"]),
        ],
    )

    state = module.params["state"]

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # --- state: present (create) ---
    if state == "present":
        notification_input = {
            "importance": module.params["importance"],
            "subject": module.params["subject"],
        }
        if module.params.get("description"):
            notification_input["description"] = module.params["description"]

        if module.check_mode:
            module.exit_json(
                changed=True,
                notification={
                    "subject": module.params["subject"],
                    "importance": module.params["importance"],
                    "action": "created",
                },
            )

        try:
            client.mutate(CREATE_NOTIFICATION, {"input": notification_input})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to create notification: {exc}")

        module.exit_json(
            changed=True,
            notification={
                "subject": module.params["subject"],
                "importance": module.params["importance"],
                "action": "created",
            },
        )

    # --- state: archived ---
    if state == "archived":
        notification_id = module.params["id"]

        if module.check_mode:
            module.exit_json(
                changed=True,
                notification={"id": notification_id, "action": "archived"},
            )

        try:
            client.mutate(ARCHIVE_NOTIFICATION, {"id": notification_id})
        except UnraidError as exc:
            module.fail_json(
                msg=f"Failed to archive notification '{notification_id}': {exc}"
            )

        module.exit_json(
            changed=True,
            notification={"id": notification_id, "action": "archived"},
        )

    # --- state: absent (delete) ---
    if state == "absent":
        notification_id = module.params["id"]

        if module.check_mode:
            module.exit_json(
                changed=True,
                notification={"id": notification_id, "action": "deleted"},
            )

        try:
            client.mutate(DELETE_NOTIFICATION, {"id": notification_id})
        except UnraidError as exc:
            module.fail_json(
                msg=f"Failed to delete notification '{notification_id}': {exc}"
            )

        module.exit_json(
            changed=True,
            notification={"id": notification_id, "action": "deleted"},
        )


if __name__ == "__main__":
    main()
