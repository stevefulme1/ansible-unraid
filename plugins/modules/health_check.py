#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2026 Steve Fulmer
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: health_check
short_description: Composite health check for Unraid systems
description:
    - Performs a comprehensive health check of an Unraid system by
      querying multiple data sources via the GraphQL API.
    - Evaluates array status, disk temperatures, SMART health data,
      parity status, and pool health.
    - Returns an overall health status (C(healthy), C(degraded), or
      C(critical)) along with per-component details.
    - This is a read-only info module and makes no changes.
    - Useful as a monitoring endpoint or pre-flight check before
      maintenance operations.
version_added: "1.0.0"
author:
    - Steve Fulmer (@stevefulme1)
extends_documentation_fragment:
    - stevefulme1.unraid.unraid
notes:
    - Temperature thresholds default to 45C for warning (degraded)
      and 55C for critical. These are conservative values suitable
      for most consumer and NAS-class drives.
    - SMART health is determined by the overall SMART self-assessment
      test result (passed/failed).
    - A single critical component triggers an overall C(critical) status.
      A single degraded component (with no critical) triggers C(degraded).
"""

EXAMPLES = r"""
- name: Run comprehensive health check
  stevefulme1.unraid.health_check:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
    validate_certs: false
  register: health

- name: Fail playbook if system is critical
  ansible.builtin.fail:
    msg: "Unraid system is in CRITICAL state: {{ health.issues | join(', ') }}"
  when: health.overall_status == 'critical'

- name: Display health summary
  ansible.builtin.debug:
    msg: |
      Overall: {{ health.overall_status }}
      Array: {{ health.components.array.status }}
      Disks with issues: {{ health.issues | length }}
"""

RETURN = r"""
overall_status:
    description:
        - Overall system health status.
        - C(healthy) means all components are operating normally.
        - C(degraded) means one or more components have warnings.
        - C(critical) means one or more components have failures.
    returned: always
    type: str
    sample: healthy
components:
    description: Per-component health details.
    returned: always
    type: dict
    contains:
        array:
            description: Array status information.
            type: dict
            contains:
                status:
                    description: Component health status.
                    type: str
                    sample: healthy
                state:
                    description: Current array state.
                    type: str
                    sample: STARTED
                msg:
                    description: Status detail message.
                    type: str
                    sample: "Array is running normally."
        disks:
            description: Disk health summary.
            type: dict
            contains:
                status:
                    description: Component health status.
                    type: str
                    sample: healthy
                total:
                    description: Total number of disks.
                    type: int
                    sample: 6
                issues:
                    description: List of disks with issues.
                    type: list
                    elements: dict
                msg:
                    description: Status detail message.
                    type: str
                    sample: "All 6 disks are healthy."
        temperatures:
            description: Disk temperature summary.
            type: dict
            contains:
                status:
                    description: Component health status.
                    type: str
                    sample: healthy
                max_temp:
                    description: Highest disk temperature in Celsius.
                    type: int
                    sample: 38
                hot_disks:
                    description: List of disks above warning threshold.
                    type: list
                    elements: dict
                msg:
                    description: Status detail message.
                    type: str
                    sample: "All disk temperatures normal (max 38C)."
        smart:
            description: SMART health summary.
            type: dict
            contains:
                status:
                    description: Component health status.
                    type: str
                    sample: healthy
                failed_disks:
                    description: List of disks with SMART failures.
                    type: list
                    elements: dict
                msg:
                    description: Status detail message.
                    type: str
                    sample: "All disks pass SMART self-assessment."
        parity:
            description: Parity status information.
            type: dict
            contains:
                status:
                    description: Component health status.
                    type: str
                    sample: healthy
                last_check:
                    description: Details of the last parity check.
                    type: dict
                msg:
                    description: Status detail message.
                    type: str
                    sample: "Last parity check passed with 0 errors."
        pools:
            description: Cache/storage pool health summary.
            type: dict
            contains:
                status:
                    description: Component health status.
                    type: str
                    sample: healthy
                pools:
                    description: List of pool statuses.
                    type: list
                    elements: dict
                msg:
                    description: Status detail message.
                    type: str
                    sample: "All pools are healthy."
issues:
    description: Flat list of all issue descriptions across components.
    returned: always
    type: list
    elements: str
    sample: ["disk3 SMART self-assessment FAILED", "disk5 temperature 52C exceeds warning threshold"]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    unraid_argument_spec,
    get_client,
    UnraidError,
)

QUERY_HEALTH = """
{
    array {
        state
        caches {
            id
            name
            status
        }
    }
    disks {
        id
        name
        status
        temperature
        standby
        smart {
            passed
        }
    }
    parityHistory {
        date
        duration
        speed
        errors
    }
}
"""

TEMP_WARN = 45
TEMP_CRIT = 55

HEALTHY_DISK_STATUSES = {"DISK_OK", "DISK_NP", "DISK_NP_DSBL"}
DEGRADED_DISK_STATUSES = {"DISK_DSBL", "DISK_NP_MISSING"}
# Everything else is considered critical


def evaluate_array(array_data):
    """Evaluate array health."""
    state = array_data.get("state", "UNKNOWN")
    if state in ("STARTED", "STARTING"):
        return {
            "status": "healthy",
            "state": state,
            "msg": "Array is running normally.",
        }
    elif state in ("STOPPED", "STOPPING"):
        return {
            "status": "degraded",
            "state": state,
            "msg": f"Array is {state.lower()}.",
        }
    else:
        return {
            "status": "critical",
            "state": state,
            "msg": f"Array is in unexpected state: {state}.",
        }


def evaluate_disks(disks):
    """Evaluate overall disk health."""
    issues = []
    worst = "healthy"

    for disk in disks:
        disk_id = disk.get("id", "unknown")
        disk_name = disk.get("name", disk_id)
        status = disk.get("status", "UNKNOWN")

        if status in HEALTHY_DISK_STATUSES:
            continue
        elif status in DEGRADED_DISK_STATUSES:
            issues.append({
                "id": disk_id,
                "name": disk_name,
                "status": status,
                "severity": "degraded",
            })
            if worst == "healthy":
                worst = "degraded"
        else:
            issues.append({
                "id": disk_id,
                "name": disk_name,
                "status": status,
                "severity": "critical",
            })
            worst = "critical"

    total = len(disks)
    if not issues:
        msg = f"All {total} disks are healthy."
    else:
        msg = f"{len(issues)} of {total} disks have issues."

    return {
        "status": worst,
        "total": total,
        "issues": issues,
        "msg": msg,
    }


def evaluate_temperatures(disks):
    """Evaluate disk temperatures."""
    hot_disks = []
    worst = "healthy"
    max_temp = 0

    for disk in disks:
        temp = disk.get("temperature")
        if temp is None:
            continue

        if temp > max_temp:
            max_temp = temp

        if temp >= TEMP_CRIT:
            hot_disks.append({
                "id": disk.get("id"),
                "name": disk.get("name"),
                "temperature": temp,
                "severity": "critical",
            })
            worst = "critical"
        elif temp >= TEMP_WARN:
            hot_disks.append({
                "id": disk.get("id"),
                "name": disk.get("name"),
                "temperature": temp,
                "severity": "degraded",
            })
            if worst == "healthy":
                worst = "degraded"

    if not hot_disks:
        msg = f"All disk temperatures normal (max {max_temp}C)."
    else:
        msg = f"{len(hot_disks)} disk(s) above temperature threshold (max {max_temp}C)."

    return {
        "status": worst,
        "max_temp": max_temp,
        "hot_disks": hot_disks,
        "msg": msg,
    }


def evaluate_smart(disks):
    """Evaluate SMART health across all disks."""
    failed_disks = []

    for disk in disks:
        smart = disk.get("smart")
        if smart is None:
            continue
        if not smart.get("passed", True):
            failed_disks.append({
                "id": disk.get("id"),
                "name": disk.get("name"),
            })

    if not failed_disks:
        return {
            "status": "healthy",
            "failed_disks": [],
            "msg": "All disks pass SMART self-assessment.",
        }
    else:
        return {
            "status": "critical",
            "failed_disks": failed_disks,
            "msg": f"{len(failed_disks)} disk(s) have SMART failures.",
        }


def evaluate_parity(parity_history):
    """Evaluate parity health from history."""
    if not parity_history:
        return {
            "status": "degraded",
            "last_check": None,
            "msg": "No parity check history available.",
        }

    last = parity_history[0]
    errors = last.get("errors", 0)

    result = {
        "last_check": last,
    }

    if errors and int(errors) > 0:
        result["status"] = "critical"
        result["msg"] = f"Last parity check had {errors} errors."
    else:
        result["status"] = "healthy"
        result["msg"] = "Last parity check passed with 0 errors."

    return result


def evaluate_pools(caches):
    """Evaluate cache/storage pool health."""
    pool_results = []
    worst = "healthy"

    for pool in caches:
        pool_status = pool.get("status", "UNKNOWN")
        pool_info = {
            "id": pool.get("id"),
            "name": pool.get("name"),
            "status": pool_status,
        }

        if pool_status in HEALTHY_DISK_STATUSES:
            pool_info["health"] = "healthy"
        elif pool_status in DEGRADED_DISK_STATUSES:
            pool_info["health"] = "degraded"
            if worst == "healthy":
                worst = "degraded"
        else:
            pool_info["health"] = "critical"
            worst = "critical"

        pool_results.append(pool_info)

    if not caches:
        msg = "No pools configured."
    elif worst == "healthy":
        msg = "All pools are healthy."
    else:
        msg = f"{len([p for p in pool_results if p['health'] != 'healthy'])} pool(s) have issues."

    return {
        "status": worst,
        "pools": pool_results,
        "msg": msg,
    }


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

    try:
        data = client.query(QUERY_HEALTH)
    except UnraidError as exc:
        module.fail_json(msg=f"Failed to query health data: {exc}")

    array_data = data.get("array", {})
    disks = data.get("disks", [])
    parity_history = data.get("parityHistory", [])
    caches = array_data.get("caches", [])

    # Evaluate each component
    components = {
        "array": evaluate_array(array_data),
        "disks": evaluate_disks(disks),
        "temperatures": evaluate_temperatures(disks),
        "smart": evaluate_smart(disks),
        "parity": evaluate_parity(parity_history),
        "pools": evaluate_pools(caches),
    }

    # Determine overall status
    statuses = [c["status"] for c in components.values()]
    if "critical" in statuses:
        overall = "critical"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    # Collect all issues into a flat list
    issues = []
    for disk_issue in components["disks"].get("issues", []):
        issues.append(
            f"{disk_issue['name']} ({disk_issue['id']}) status: {disk_issue['status']}"
        )
    for hot_disk in components["temperatures"].get("hot_disks", []):
        issues.append(
            f"{hot_disk['name']} ({hot_disk['id']}) temperature {hot_disk['temperature']}C "
            f"exceeds {'critical' if hot_disk['severity'] == 'critical' else 'warning'} threshold"
        )
    for failed_disk in components["smart"].get("failed_disks", []):
        issues.append(
            f"{failed_disk['name']} ({failed_disk['id']}) SMART self-assessment FAILED"
        )
    if components["parity"]["status"] == "critical":
        issues.append(components["parity"]["msg"])
    if components["array"]["status"] != "healthy":
        issues.append(components["array"]["msg"])
    for pool in components["pools"].get("pools", []):
        if pool.get("health") != "healthy":
            issues.append(f"Pool '{pool['name']}' status: {pool['status']}")

    module.exit_json(
        changed=False,
        overall_status=overall,
        components=components,
        issues=issues,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
