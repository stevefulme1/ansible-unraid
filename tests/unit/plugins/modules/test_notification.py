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


def _make_module(state="present", importance=None, subject=None,
                 description=None, notif_id=None, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "state": state,
        "importance": importance,
        "subject": subject,
        "description": description,
        "id": notif_id,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestNotificationModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_create_notification(self, MockModule, mock_get_client):
        module = _make_module(state="present", importance="alert",
                              subject="Disk warning", description="Disk 1 temp high")
        MockModule.return_value = module

        client = MagicMock()
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["notification"]["action"] == "created"
        assert result["notification"]["subject"] == "Disk warning"
        client.mutate.assert_called_once()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_create_without_description(self, MockModule, mock_get_client):
        module = _make_module(state="present", importance="info", subject="Test")
        module.params["description"] = None
        MockModule.return_value = module

        client = MagicMock()
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson):
            main()

        mutate_vars = client.mutate.call_args[0][1]
        assert "description" not in mutate_vars["input"]

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_archive_notification(self, MockModule, mock_get_client):
        module = _make_module(state="archived", notif_id="notif-123")
        MockModule.return_value = module

        client = MagicMock()
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["notification"]["action"] == "archived"
        assert result["notification"]["id"] == "notif-123"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_delete_notification(self, MockModule, mock_get_client):
        module = _make_module(state="absent", notif_id="notif-456")
        MockModule.return_value = module

        client = MagicMock()
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["notification"]["action"] == "deleted"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_check_mode_create(self, MockModule, mock_get_client):
        module = _make_module(state="present", importance="warning",
                              subject="Test", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_check_mode_archive(self, MockModule, mock_get_client):
        module = _make_module(state="archived", notif_id="n-1", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_check_mode_delete(self, MockModule, mock_get_client):
        module = _make_module(state="absent", notif_id="n-2", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.notification.AnsibleModule")
    def test_create_failure_calls_fail_json(self, MockModule, mock_get_client):
        module = _make_module(state="present", importance="alert", subject="Fail test")
        MockModule.return_value = module

        client = MagicMock()
        client.mutate.side_effect = UnraidError("API error")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.notification import main
        with pytest.raises(AnsibleFailJson) as exc_info:
            main()

        assert "Failed to create notification" in exc_info.value.kwargs["msg"]
