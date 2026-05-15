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


def _make_module(name, password="secret123", description=None,
                 state="present", check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "name": name,
        "password": password,
        "description": description,
        "state": state,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestUserModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.AnsibleModule")
    def test_create_new_user(self, MockModule, mock_get_client):
        module = _make_module("mediauser", description="Media access")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"users": ["root", "admin"]}
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.user import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["user"] == "mediauser"
        assert result["created"] is True
        client.mutate.assert_called_once()
        mutate_args = client.mutate.call_args[0][1]
        assert mutate_args["name"] == "mediauser"
        assert mutate_args["description"] == "Media access"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.AnsibleModule")
    def test_user_already_exists_no_change(self, MockModule, mock_get_client):
        module = _make_module("admin")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"users": ["root", "admin"]}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.user import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        assert result["user"] == "admin"
        assert result["created"] is False
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.AnsibleModule")
    def test_check_mode_create(self, MockModule, mock_get_client):
        module = _make_module("newuser", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"users": ["root"]}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.user import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["created"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.AnsibleModule")
    def test_create_without_description(self, MockModule, mock_get_client):
        module = _make_module("simpleuser", description=None)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"users": []}
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.user import main
        with pytest.raises(AnsibleExitJson):
            main()

        mutate_args = client.mutate.call_args[0][1]
        assert "description" not in mutate_args

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.user.AnsibleModule")
    def test_create_failure_calls_fail_json(self, MockModule, mock_get_client):
        module = _make_module("baduser")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = {"users": []}
        client.mutate.side_effect = UnraidError("Permission denied")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.user import main
        with pytest.raises(AnsibleFailJson) as exc_info:
            main()

        assert "Failed to create user" in exc_info.value.kwargs["msg"]
