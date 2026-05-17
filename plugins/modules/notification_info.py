#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible module for querying Unraid notifications."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: notification_info
short_description: Query notifications on Unraid
version_added: "1.0.0"
description:
  - Retrieve notification overview counts and notification lists from an
    Unraid server via the GraphQL API.
  - Returns both an overview with counts by importance level and an optional
    filtered list of individual notifications.
options:
  importance:
    description:
      - Filter notifications by importance level.
      - When set, only notifications of this importance are returned in the list.
    type: str
    choices: [alert, warning, normal, info]
    required: false
  type:
    description:
      - Filter notifications by type.
      - C(unread) returns only unread notifications.
      - C(archive) returns only archived notifications.
      - When not set, returns all notifications.
    type: str
    choices: [unread, archive]
    required: false

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
extends_documentation_fragment:
  - stevefulme1.unraid.unraid
author:
  - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Get notification overview
  stevefulme1.unraid.notification_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
  register: notif_overview

- name: Show unread alert count
  ansible.builtin.debug:
    msg: "Unread alerts: {{ notif_overview.overview.unread.alert }}"

- name: List all alert notifications
  stevefulme1.unraid.notification_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    importance: alert

- name: List archived notifications
  stevefulme1.unraid.notification_info:
    api_url: https://unraid.local
    api_key: "{{ unraid_api_key }}"
    type: archive
"""

RETURN = r"""
overview:
  description: Notification counts grouped by type and importance level.
  returned: always
  type: dict
  contains:
    unread:
      description: Counts of unread notifications by importance.
      type: dict
      sample:
        info: 2
        normal: 1
        warning: 0
        alert: 0
    archive:
      description: Counts of archived notifications by importance.
      type: dict
      sample:
        info: 5
        normal: 3
        warning: 1
        alert: 0
notifications:
  description: List of notifications matching the filter criteria.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The unique notification identifier.
      type: str
    importance:
      description: The importance level.
      type: str
    subject:
      description: The notification subject.
      type: str
    description:
      description: The notification body text.
      type: str
  sample:
    - id: "notif-001"
      importance: "alert"
      subject: "Disk failure"
      description: "Disk 3 has failed"
"""

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)
from ansible.module_utils.basic import AnsibleModule


QUERY_OVERVIEW = """
{
  notifications {
    overview {
      unread {
        info
        normal
        warning
        alert
      }
      archive {
        info
        normal
        warning
        alert
      }
    }
  }
}
"""

QUERY_NOTIFICATIONS_FILTERED = """
query($filter: NotificationFilter) {
  notifications {
    list(filter: $filter) {
      id
      importance
      subject
      description
    }
  }
}
"""

QUERY_NOTIFICATIONS_ALL = """
{
  notifications {
    list {
      id
      importance
      subject
      description
    }
  }
}
"""


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        importance=dict(
            type="str",
            choices=["alert", "warning", "normal", "info"],
            required=False,
        ),
        type=dict(
            type="str",
            choices=["unread", "archive"],
            required=False,
        ),
    )
    argument_spec.update(
        limit=dict(type='int', default=100),
        offset=dict(type='int', default=0),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    try:
        client = get_client(module)
    except UnraidError as exc:
        module.fail_json(msg=str(exc))

    # Fetch overview
    try:
        overview_result = client.query(QUERY_OVERVIEW)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query notification overview: {exc}")

    overview = overview_result.get("notifications", {}).get("overview", {})

    # Build filter for notification list
    importance = module.params.get("importance")
    notif_type = module.params.get("type")

    has_filter = importance is not None or notif_type is not None

    if has_filter:
        filter_obj = {}
        if importance is not None:
            filter_obj["importance"] = importance
        if notif_type is not None:
            filter_obj["type"] = notif_type
        try:
            list_result = client.query(
                QUERY_NOTIFICATIONS_FILTERED, {"filter": filter_obj}
            )
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to query notifications: {exc}")
    else:
        try:
            list_result = client.query(QUERY_NOTIFICATIONS_ALL)
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to query notifications: {exc}")

    notifications = list_result.get("notifications", {}).get("list", [])

    module.exit_json(
        changed=False,
        overview=overview,
        notifications=notifications,
    )


if __name__ == "__main__":
    main()
