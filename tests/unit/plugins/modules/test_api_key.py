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


API_KEYS_RESPONSE = {
    "apiKeys": [
        {"id": "key-001", "name": "existing-key", "roles": [{"role": "ADMIN"}]},
        {"id": "key-002", "name": "guest-key", "roles": [{"role": "GUEST"}]},
    ]
}

API_KEYS_EMPTY = {"apiKeys": []}


def _make_module(name, state="present", description=None,
                 roles=None, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "name": name,
        "state": state,
        "description": description,
        "roles": roles or [],
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestApiKeyModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_create_new_key(self, MockModule, mock_get_client):
        module = _make_module("automation-key", roles=["ADMIN"])
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            API_KEYS_EMPTY,
            {"apiKeys": [{"id": "key-new", "name": "automation-key",
                          "roles": [{"role": "ADMIN"}]}]},
        ]
        client.mutate.return_value = {"apiKey": {"create": "unraid_abc123secret"}}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["key_value"] == "unraid_abc123secret"
        assert result["api_key"]["name"] == "automation-key"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_delete_existing_key(self, MockModule, mock_get_client):
        module = _make_module("existing-key", state="absent")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = API_KEYS_RESPONSE
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_called_once()
        mutate_vars = client.mutate.call_args[0][1]
        assert mutate_vars["id"] == "key-001"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_delete_nonexistent_key(self, MockModule, mock_get_client):
        module = _make_module("phantom-key", state="absent")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = API_KEYS_EMPTY
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is False
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_existing_key_no_change_needed(self, MockModule, mock_get_client):
        module = _make_module("existing-key", roles=["ADMIN"])
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = API_KEYS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        assert result["api_key"]["name"] == "existing-key"
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_check_mode_create(self, MockModule, mock_get_client):
        module = _make_module("new-key", roles=["ADMIN"], check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = API_KEYS_EMPTY
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["key_value"] == "(check mode - no key generated)"
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_check_mode_delete(self, MockModule, mock_get_client):
        module = _make_module("existing-key", state="absent", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = API_KEYS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.api_key.AnsibleModule")
    def test_update_existing_key_different_roles(self, MockModule, mock_get_client):
        module = _make_module("guest-key", roles=["ADMIN", "CONNECT"])
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            API_KEYS_RESPONSE,
            {"apiKeys": [{"id": "key-002", "name": "guest-key",
                          "roles": [{"role": "ADMIN"}, {"role": "CONNECT"}]}]},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.api_key import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_called_once()
