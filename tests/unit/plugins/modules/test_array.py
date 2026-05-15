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


def _make_module(state, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "state": state,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestArrayModule:
    """Tests for the array start/stop module."""

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_start_when_already_started(self, MockModule, mock_get_client):
        """Starting an already-running array should report no change."""
        module = _make_module("started")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STARTED"}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        assert result["state"] == "STARTED"
        assert result["previous_state"] == "STARTED"
        client.mutate.assert_not_called()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_start_when_stopped(self, MockModule, mock_get_client):
        """Starting a stopped array should trigger a mutation."""
        module = _make_module("started")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STOPPED"}}
        client.mutate.return_value = {"array": {"setState": {"state": "STARTED"}}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["state"] == "STARTED"
        assert result["previous_state"] == "STOPPED"
        client.mutate.assert_called_once()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_stop_when_already_stopped(self, MockModule, mock_get_client):
        """Stopping an already-stopped array should report no change."""
        module = _make_module("stopped")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STOPPED"}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False
        client.mutate.assert_not_called()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_stop_when_started(self, MockModule, mock_get_client):
        """Stopping a running array should trigger a mutation."""
        module = _make_module("stopped")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STARTED"}}
        client.mutate.return_value = {"array": {"setState": {"state": "STOPPED"}}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["state"] == "STOPPED"
        assert result["previous_state"] == "STARTED"

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_check_mode_does_not_mutate(self, MockModule, mock_get_client):
        """In check mode, no mutation should be called."""
        module = _make_module("started", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STOPPED"}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert "Would change" in result.get("msg", "")
        client.mutate.assert_not_called()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_starting_state_treated_as_started(self, MockModule, mock_get_client):
        """STARTING state should be treated like STARTED (no change needed)."""
        module = _make_module("started")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STARTING"}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.array.AnsibleModule"
    )
    def test_mutation_failure_calls_fail_json(self, MockModule, mock_get_client):
        """If the mutation fails, fail_json should be called."""
        module = _make_module("started")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"array": {"state": "STOPPED"}}
        client.mutate.side_effect = UnraidError("Timeout")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.array import run_module
        with pytest.raises(AnsibleFailJson) as exc_info:
            run_module()

        assert "Failed to set array state" in exc_info.value.kwargs["msg"]
