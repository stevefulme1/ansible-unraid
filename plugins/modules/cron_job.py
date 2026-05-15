#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cron_job
short_description: Manage scheduled tasks on Unraid
description:
    - Create, update, or remove scheduled tasks (cron jobs) on an Unraid
      server via the GraphQL API.
    - This module manages User Scripts plugin scripts or standard crontab
      entries accessible through the Unraid API.
    - The User Scripts plugin (C(user.scripts)) should be installed for
      full functionality.
    - In check mode, reports what changes would be made without applying them.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
options:
    name:
        description:
            - Unique name identifying the scheduled task.
            - Used as the script name in the User Scripts plugin.
        type: str
        required: true
    schedule:
        description:
            - Cron expression defining when the task runs
              (e.g., C(0 2 * * *) for daily at 2am).
            - Uses standard 5-field cron syntax
              (minute hour day-of-month month day-of-week).
            - Required when I(state=present).
        type: str
    command:
        description:
            - The command or script content to execute.
            - Required when I(state=present).
        type: str
    state:
        description:
            - Whether the cron job should exist or be removed.
        type: str
        choices:
            - present
            - absent
        default: present
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
"""

EXAMPLES = r"""
- name: Create a daily backup script
  stevefulme1.unraid.cron_job:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: daily-backup
    schedule: "0 2 * * *"
    command: "/usr/local/bin/backup.sh"
    state: present

- name: Create a weekly cleanup task
  stevefulme1.unraid.cron_job:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: weekly-cleanup
    schedule: "0 3 * * 0"
    command: |
      #!/bin/bash
      find /mnt/user/appdata/logs -mtime +30 -delete

- name: Remove a scheduled task
  stevefulme1.unraid.cron_job:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    name: daily-backup
    state: absent
"""

RETURN = r"""
cron_job:
    description: The cron job configuration after changes.
    returned: success
    type: dict
    contains:
        name:
            description: Task name.
            type: str
        schedule:
            description: Cron schedule expression.
            type: str
        command:
            description: Command to execute.
            type: str
    sample:
        name: daily-backup
        schedule: "0 2 * * *"
        command: "/usr/local/bin/backup.sh"
diff:
    description: Configuration differences that were applied.
    returned: changed
    type: dict
    contains:
        before:
            description: Previous configuration values.
            type: dict
        after:
            description: New configuration values.
            type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_CRON_JOBS = """
{
    cronJobs {
        name
        schedule
        command
    }
}
"""

MUTATION_CREATE_CRON = """
mutation($input: CronJobInput!) {
    createCronJob(input: $input)
}
"""

MUTATION_UPDATE_CRON = """
mutation($input: CronJobInput!) {
    updateCronJob(input: $input)
}
"""

MUTATION_DELETE_CRON = """
mutation($name: String!) {
    deleteCronJob(name: $name)
}
"""


def find_job(jobs, name):
    """Find an existing cron job by name."""
    for job in jobs:
        if job.get("name") == name:
            return job
    return None


def main():
    argument_spec = unraid_argument_spec()
    argument_spec.update(
        name=dict(type="str", required=True),
        schedule=dict(type="str"),
        command=dict(type="str"),
        state=dict(type="str", choices=["present", "absent"], default="present"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["schedule", "command"]),
        ],
    )

    name = module.params["name"]
    schedule = module.params.get("schedule")
    command = module.params.get("command")
    state = module.params["state"]

    try:
        client = get_client(module)
        data = client.query(QUERY_CRON_JOBS)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query cron jobs: {exc}")

    jobs = data.get("cronJobs", [])
    existing = find_job(jobs, name)

    if state == "absent":
        if not existing:
            module.exit_json(changed=False, cron_job={})
            return

        diff = {
            "before": {
                "name": name,
                "schedule": existing.get("schedule"),
                "command": existing.get("command"),
            },
            "after": {},
        }

        if module.check_mode:
            module.exit_json(changed=True, cron_job={}, diff=diff)
            return

        try:
            client.mutate(MUTATION_DELETE_CRON, variables={"name": name})
        except UnraidError as exc:
            module.fail_json(msg=f"Failed to delete cron job {name}: {exc}")

        module.exit_json(changed=True, cron_job={}, diff=diff)
        return

    # state == present
    desired = dict(name=name, schedule=schedule, command=command)

    if existing:
        current = dict(
            name=existing.get("name"),
            schedule=existing.get("schedule"),
            command=existing.get("command"),
        )
        if current == desired:
            module.exit_json(changed=False, cron_job=current)
            return
        diff = {"before": current, "after": desired}
        mutation = MUTATION_UPDATE_CRON
    else:
        diff = {"before": {}, "after": desired}
        mutation = MUTATION_CREATE_CRON

    if module.check_mode:
        module.exit_json(changed=True, cron_job=desired, diff=diff)
        return

    try:
        client.mutate(
            mutation,
            variables={
                "input": {
                    "name": name,
                    "schedule": schedule,
                    "command": command,
                }
            },
        )
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to configure cron job {name}: {exc}")

    module.exit_json(changed=True, cron_job=desired, diff=diff)


if __name__ == "__main__":
    main()
