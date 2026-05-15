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


def _make_module(disk_id, state, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "id": disk_id,
        "state": state,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


def _disk_response(disk_id="disk1", status="DISK_OK", standby=False):
    return {"disks": [{"id": disk_id, "name": "Disk 1", "status": status,
                       "spindownDelay": 0, "standby": standby}]}


class TestDiskModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_spin_up_standby_disk(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_up")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=True)
        client.mutate.return_value = {
            "disk": {"spinUp": {"id": "disk1", "status": "DISK_OK", "standby": False}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["previous_spun_down"] is True
        assert result["disk"]["spun_down"] is False

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_spin_up_already_active_no_change(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_up")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=False)
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        assert result["disk"]["spun_down"] is False
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_spin_down_active_disk(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_down")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=False)
        client.mutate.return_value = {
            "disk": {"spinDown": {"id": "disk1", "status": "DISK_OK", "standby": True}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["previous_spun_down"] is False
        assert result["disk"]["spun_down"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_spin_down_already_standby_no_change(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_down")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=True)
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_disk_not_found_fails(self, MockModule, mock_get_client):
        module = _make_module("nonexistent", "spun_up")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"disks": []}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleFailJson) as exc_info:
            run_module()

        assert "not found" in exc_info.value.kwargs["msg"]

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_check_mode_spin_up(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_up", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=True)
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert "Would" in result.get("msg", "")
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_check_mode_spin_down(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_down", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=False)
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.disk.AnsibleModule")
    def test_mutation_failure_calls_fail_json(self, MockModule, mock_get_client):
        module = _make_module("disk1", "spun_up")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _disk_response(standby=True)
        client.mutate.side_effect = UnraidError("Disk error")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.disk import run_module
        with pytest.raises(AnsibleFailJson) as exc_info:
            run_module()

        assert "Failed to" in exc_info.value.kwargs["msg"]
