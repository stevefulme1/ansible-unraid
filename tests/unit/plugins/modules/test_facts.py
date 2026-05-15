from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    UnraidError,
)


class AnsibleExitJson(Exception):
    def __init__(self, kwargs):
        self.kwargs = kwargs


class AnsibleFailJson(Exception):
    def __init__(self, kwargs):
        self.kwargs = kwargs


def _exit_json(**kwargs):
    raise AnsibleExitJson(kwargs)


def _fail_json(**kwargs):
    raise AnsibleFailJson(kwargs)


# Sample GraphQL responses -----------------------------------------------

SAMPLE_SYSTEM = {
    "info": {
        "os": {"hostname": "tower", "version": "7.2.0", "uptime": 123456},
        "cpu": {"model": "AMD Ryzen 9 5950X", "cores": 16},
        "memory": {"total": 68719476736, "used": 34359738368, "free": 34359738368},
        "versions": {"unraid": "7.2.0", "kernel": "6.1.0"},
    }
}

SAMPLE_ARRAY = {
    "array": {
        "state": "STARTED",
        "capacity": {"total": 10000000000, "used": 5000000000, "free": 5000000000},
        "parity": {"status": "IDLE", "progress": 0, "lastCheck": "2026-01-01"},
    }
}

SAMPLE_DISKS = {
    "disks": [
        {"id": "disk1", "name": "Disk 1", "device": "sdb", "size": 4000000000000,
         "status": "DISK_OK", "temperature": 35, "type": "Data",
         "fsType": "xfs", "mounted": True},
    ]
}

SAMPLE_DOCKER = {
    "docker": {
        "containers": [
            {"id": "abc123", "name": "plex", "state": "running",
             "status": "Up 3 days", "image": "plexinc/pms-docker", "autoStart": True},
        ]
    }
}

SAMPLE_VMS = {
    "vms": {
        "domain": [
            {"name": "Windows11", "uuid": "uuid-123", "state": "running",
             "autoStart": False, "vcpus": 4, "memory": 8192},
        ]
    }
}

SAMPLE_SHARES = {
    "shares": [
        {"name": "appdata", "comment": "Application data", "free": 100000,
         "used": 50000, "size": 150000, "useCache": "yes"},
    ]
}

SAMPLE_UPS = {
    "ups": {
        "status": "OL", "model": "APC 1500",
        "battery": {"charge": 100, "runtime": 1800},
        "nominal": {"power": 900},
    }
}

SAMPLE_NOTIFICATIONS = {
    "notifications": {
        "overview": {"unread": 2, "total": 10, "alert": 0,
                     "warning": 1, "notice": 1, "info": 8},
    }
}


def _build_query_side_effect(responses_map):
    """Return a side_effect callable that maps query substrings to responses.

    Keys are matched longest-first to avoid substring collisions (e.g.
    "notifications" matching before "info").
    """
    sorted_keys = sorted(responses_map.keys(), key=len, reverse=True)

    def side_effect(query):
        for key in sorted_keys:
            if key in query:
                return responses_map[key]
        return {}
    return side_effect


def _make_module(check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


# -------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------

class TestFactsModule:
    """Tests for the facts module."""

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.AnsibleModule"
    )
    def test_successful_fact_gathering(self, MockModule, mock_get_client):
        """All queries succeed and facts are populated."""
        module = _make_module()
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = _build_query_side_effect({
            "info": SAMPLE_SYSTEM,
            "array": SAMPLE_ARRAY,
            "disks": SAMPLE_DISKS,
            "docker": SAMPLE_DOCKER,
            "vms": SAMPLE_VMS,
            "shares": SAMPLE_SHARES,
            "ups": SAMPLE_UPS,
            "notifications": SAMPLE_NOTIFICATIONS,
        })
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.facts import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        facts = result["ansible_facts"]["unraid"]
        assert facts["system"] == SAMPLE_SYSTEM["info"]
        assert facts["array"] == SAMPLE_ARRAY["array"]
        assert facts["disks"] == SAMPLE_DISKS["disks"]
        assert facts["docker_containers"] == SAMPLE_DOCKER["docker"]["containers"]
        assert facts["vms"] == SAMPLE_VMS["vms"]["domain"]
        assert facts["shares"] == SAMPLE_SHARES["shares"]
        assert facts["ups"] == SAMPLE_UPS["ups"]
        assert facts["notifications"] == SAMPLE_NOTIFICATIONS["notifications"]["overview"]

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.AnsibleModule"
    )
    def test_individual_query_failure_does_not_block_others(self, MockModule, mock_get_client):
        """A single failing domain query should not prevent other facts."""
        module = _make_module()
        MockModule.return_value = module

        def selective_failure(query):
            if "docker" in query:
                raise UnraidError("Docker service not available")
            if "info" in query:
                return SAMPLE_SYSTEM
            if "array" in query:
                return SAMPLE_ARRAY
            return {}

        client = MagicMock()
        client.query.side_effect = selective_failure
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.facts import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        facts = exc_info.value.kwargs["ansible_facts"]["unraid"]
        assert facts["system"] == SAMPLE_SYSTEM["info"]
        assert facts["array"] == SAMPLE_ARRAY["array"]
        assert facts["docker_containers"] == []

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.AnsibleModule"
    )
    def test_check_mode_support(self, MockModule, mock_get_client):
        """Module should work identically in check mode (read-only)."""
        module = _make_module(check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.facts import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.facts.AnsibleModule"
    )
    def test_all_queries_fail_returns_empty_facts(self, MockModule, mock_get_client):
        """If every query fails, facts should be empty dicts/lists."""
        module = _make_module()
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = UnraidError("API unreachable")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.facts import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        facts = exc_info.value.kwargs["ansible_facts"]["unraid"]
        assert facts["system"] == {}
        assert facts["array"] == {}
        assert facts["disks"] == []
        assert facts["docker_containers"] == []
        assert facts["vms"] == []
        assert facts["shares"] == []
        assert facts["ups"] == {}
        assert facts["notifications"] == {}
