#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: notification_agent
short_description: Configure notification delivery agents on Unraid
version_added: "1.0.0"
description:
    - Configure notification delivery agents (email, Slack, Discord, Pushover,
      Telegram) on an Unraid server via the GraphQL API.
    - Each agent type has its own set of configuration parameters.
    - The module reads the current agent configuration, compares it to the
      desired state, and only applies changes when needed.
    - Requires Unraid 7.2 or later.
options:
    agent:
        description:
            - The notification agent type to configure.
        type: str
        required: true
        choices:
            - email
            - slack
            - discord
            - pushover
            - telegram
    enabled:
        description:
            - Whether the notification agent is enabled.
        type: bool
        default: true
    smtp_server:
        description:
            - SMTP server hostname or IP address.
            - Required when O(agent=email).
        type: str
    smtp_port:
        description:
            - SMTP server port.
            - Only used when O(agent=email).
        type: int
        default: 587
    smtp_ssl:
        description:
            - Whether to use SSL/TLS for SMTP.
            - Only used when O(agent=email).
        type: bool
        default: true
    smtp_auth:
        description:
            - Whether SMTP authentication is required.
            - Only used when O(agent=email).
        type: bool
        default: true
    smtp_user:
        description:
            - SMTP authentication username.
            - Only used when O(agent=email) and O(smtp_auth=true).
        type: str
    smtp_password:
        description:
            - SMTP authentication password.
            - Only used when O(agent=email) and O(smtp_auth=true).
        type: str
    email_from:
        description:
            - Sender email address.
            - Only used when O(agent=email).
        type: str
    email_to:
        description:
            - Recipient email address(es), comma-separated.
            - Only used when O(agent=email).
        type: str
    webhook_url:
        description:
            - Webhook URL for the notification service.
            - Required when O(agent=slack) or O(agent=discord).
        type: str
    api_token:
        description:
            - API token for the notification service.
            - Required when O(agent=pushover) (app token) or O(agent=telegram) (bot token).
        type: str
    user_key:
        description:
            - User key for Pushover notifications.
            - Required when O(agent=pushover).
        type: str
    chat_id:
        description:
            - Chat ID for Telegram notifications.
            - Required when O(agent=telegram).
        type: str
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
author:
    - Steve Fulmer (@stevefulme1)
"""

EXAMPLES = r"""
- name: Configure email notifications
  stevefulme1.unraid.notification_agent:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    agent: email
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    smtp_ssl: true
    smtp_auth: true
    smtp_user: user@gmail.com
    smtp_password: "{{ smtp_app_password }}"
    email_from: unraid@mydomain.com
    email_to: admin@mydomain.com

- name: Configure Slack notifications
  stevefulme1.unraid.notification_agent:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    agent: slack
    enabled: true
    webhook_url: "{{ slack_webhook_url }}"

- name: Configure Discord notifications
  stevefulme1.unraid.notification_agent:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    agent: discord
    enabled: true
    webhook_url: "{{ discord_webhook_url }}"

- name: Configure Pushover notifications
  stevefulme1.unraid.notification_agent:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    agent: pushover
    enabled: true
    api_token: "{{ pushover_app_token }}"
    user_key: "{{ pushover_user_key }}"

- name: Configure Telegram notifications
  stevefulme1.unraid.notification_agent:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    agent: telegram
    enabled: true
    api_token: "{{ telegram_bot_token }}"
    chat_id: "{{ telegram_chat_id }}"

- name: Disable Slack notifications
  stevefulme1.unraid.notification_agent:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    agent: slack
    enabled: false
"""

RETURN = r"""
agent_config:
    description: The notification agent configuration that was applied.
    type: dict
    returned: success
    contains:
        agent:
            description: The notification agent type.
            type: str
        enabled:
            description: Whether the agent is enabled.
            type: bool
        action:
            description: The action performed (configured, disabled, unchanged).
            type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_NOTIFICATION_SETTINGS = """
{
    settings {
        notifications {
            agents {
                name
                enabled
                config
            }
        }
    }
}
"""

MUTATION_UPDATE_AGENT = """
mutation($input: NotificationAgentInput!) {
    settings {
        updateNotificationAgent(input: $input)
    }
}
"""

# Map agent types to their required config parameters
AGENT_CONFIG_KEYS = {
    "email": [
        "smtp_server", "smtp_port", "smtp_ssl", "smtp_auth",
        "smtp_user", "smtp_password", "email_from", "email_to",
    ],
    "slack": ["webhook_url"],
    "discord": ["webhook_url"],
    "pushover": ["api_token", "user_key"],
    "telegram": ["api_token", "chat_id"],
}


def build_agent_config(module, agent_type):
    """Build the agent configuration dictionary from module params."""
    config = {}
    for key in AGENT_CONFIG_KEYS.get(agent_type, []):
        value = module.params.get(key)
        if value is not None:
            config[key] = value
    return config


def find_agent(agents, agent_name):
    """Find an agent configuration by name."""
    for agent in agents:
        if agent.get("name") == agent_name:
            return agent
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        agent=dict(
            type="str",
            required=True,
            choices=["email", "slack", "discord", "pushover", "telegram"],
        ),
        enabled=dict(type="bool", default=True),
        # Email parameters
        smtp_server=dict(type="str"),
        smtp_port=dict(type="int", default=587),
        smtp_ssl=dict(type="bool", default=True),
        smtp_auth=dict(type="bool", default=True),
        smtp_user=dict(type="str"),
        smtp_password=dict(type="str", no_log=True),
        email_from=dict(type="str"),
        email_to=dict(type="str"),
        # Slack / Discord parameters
        webhook_url=dict(type="str", no_log=True),
        # Pushover parameters
        api_token=dict(type="str", no_log=True),
        user_key=dict(type="str", no_log=True),
        # Telegram parameters
        chat_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("agent", "email", ["smtp_server", "email_from", "email_to"], False),
            ("agent", "slack", ["webhook_url"], False),
            ("agent", "discord", ["webhook_url"], False),
            ("agent", "pushover", ["api_token", "user_key"], False),
            ("agent", "telegram", ["api_token", "chat_id"], False),
        ],
    )

    agent_type = module.params["agent"]
    enabled = module.params["enabled"]

    client = get_client(module)

    # Query current configuration
    try:
        data = client.query(QUERY_NOTIFICATION_SETTINGS)
        agents = (
            data.get("settings", {})
            .get("notifications", {})
            .get("agents", [])
        )
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to query notification settings: %s" % str(exc)
        )

    current = find_agent(agents, agent_type)
    agent_config = build_agent_config(module, agent_type)

    # Determine if change is needed
    changed = False
    if current is None:
        changed = True
    else:
        if current.get("enabled") != enabled:
            changed = True
        current_config = current.get("config", {}) or {}
        for key, value in agent_config.items():
            if current_config.get(key) != value:
                changed = True
                break

    action = "unchanged"
    if changed:
        action = "disabled" if not enabled else "configured"

    result = dict(
        changed=changed,
        agent_config=dict(
            agent=agent_type,
            enabled=enabled,
            action=action,
        ),
    )

    if not changed:
        module.exit_json(**result)

    if module.check_mode:
        module.exit_json(**result)

    # Apply the configuration
    mutation_input = {
        "name": agent_type,
        "enabled": enabled,
        "config": agent_config,
    }

    try:
        client.mutate(
            MUTATION_UPDATE_AGENT,
            variables={"input": mutation_input},
        )
    except UnraidError as exc:
        module.fail_json(
            msg="Failed to configure %s notification agent: %s"
            % (agent_type, str(exc))
        )

    module.exit_json(**result)


if __name__ == "__main__":
    main()
