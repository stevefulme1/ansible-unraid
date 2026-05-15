from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch



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


def _make_module(state, correct=True, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "state": state,
        "correct": correct,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


def _parity_response(status="IDLE", progress=0):
    return {"array": {"parity": {"status": status, "progress": progress}}}


class TestParityModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_start_parity_check_from_idle(self, MockModule, mock_get_client):
        module = _make_module("running")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("IDLE")
        client.mutate.return_value = {
            "parityCheck": {"start": {"status": "RUNNING", "progress": 0}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["previous_status"] == "IDLE"
        assert result["parity"]["status"] == "RUNNING"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_start_already_running_no_change(self, MockModule, mock_get_client):
        module = _make_module("running")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("RUNNING", 45.2)
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_pause_running_check(self, MockModule, mock_get_client):
        module = _make_module("paused")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("RUNNING", 50.0)
        client.mutate.return_value = {
            "parityCheck": {"pause": {"status": "PAUSED", "progress": 50.0}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["parity"]["status"] == "PAUSED"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_pause_when_not_running_fails(self, MockModule, mock_get_client):
        module = _make_module("paused")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("IDLE")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleFailJson) as exc_info:
            run_module()

        assert "Cannot pause" in exc_info.value.kwargs["msg"]

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_resume_paused_check(self, MockModule, mock_get_client):
        module = _make_module("running")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("PAUSED", 50.0)
        client.mutate.return_value = {
            "parityCheck": {"resume": {"status": "RUNNING", "progress": 50.0}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["parity"]["status"] == "RUNNING"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_cancel_running_check(self, MockModule, mock_get_client):
        module = _make_module("cancelled")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("RUNNING", 30.0)
        client.mutate.return_value = {
            "parityCheck": {"cancel": {"status": "IDLE", "progress": 0}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_cancel_idle_no_change(self, MockModule, mock_get_client):
        module = _make_module("cancelled")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("IDLE")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_check_mode(self, MockModule, mock_get_client):
        module = _make_module("running", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("IDLE")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert "Would change" in result.get("msg", "")
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.parity.AnsibleModule")
    def test_cancel_paused_check(self, MockModule, mock_get_client):
        module = _make_module("cancelled")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = _parity_response("PAUSED", 60.0)
        client.mutate.return_value = {
            "parityCheck": {"cancel": {"status": "IDLE", "progress": 0}}
        }
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.parity import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
