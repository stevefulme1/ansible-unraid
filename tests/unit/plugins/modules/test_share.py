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


SHARES_RESPONSE = {
    "shares": [
        {"name": "appdata", "free": 100000, "used": 50000, "size": 150000},
        {"name": "media", "free": 5000000, "used": 3000000, "size": 8000000},
    ]
}


def _make_module(name, state="present", allocation_method=None,
                 cache=None, smb_export=None, nfs_export=None,
                 check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "name": name,
        "state": state,
        "allocation_method": allocation_method,
        "cache": cache,
        "include_disks": None,
        "exclude_disks": None,
        "smb_export": smb_export,
        "nfs_export": nfs_export,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestShareModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_share_found_present(self, MockModule, mock_get_client):
        module = _make_module("appdata")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = SHARES_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        assert result["exists"] is True
        assert result["share"]["name"] == "appdata"

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_share_not_found_present(self, MockModule, mock_get_client):
        module = _make_module("nonexistent")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = SHARES_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["exists"] is False
        assert "cannot be created via the API" in result["msg"]

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_share_absent_not_exists(self, MockModule, mock_get_client):
        module = _make_module("ghost", state="absent")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = SHARES_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is False
        assert result["exists"] is False

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_share_absent_exists(self, MockModule, mock_get_client):
        module = _make_module("appdata", state="absent")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = SHARES_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["exists"] is True
        assert "cannot be deleted via the API" in result["msg"]

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_share_with_desired_config(self, MockModule, mock_get_client):
        module = _make_module("media", allocation_method="highwater",
                              cache="yes", smb_export=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = SHARES_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        result = exc_info.value.kwargs
        assert result["changed"] is True
        assert result["exists"] is True
        assert result["desired_config"]["allocation_method"] == "highwater"
        assert result["desired_config"]["cache"] == "yes"
        assert result["desired_config"]["smb_export"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_api_failure_calls_fail_json(self, MockModule, mock_get_client):
        module = _make_module("appdata")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = UnraidError("Connection timeout")
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleFailJson):
            main()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.share.AnsibleModule")
    def test_share_returns_size_info(self, MockModule, mock_get_client):
        module = _make_module("media")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = SHARES_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.share import main
        with pytest.raises(AnsibleExitJson) as exc_info:
            main()

        share = exc_info.value.kwargs["share"]
        assert share["free"] == 5000000
        assert share["used"] == 3000000
        assert share["size"] == 8000000
