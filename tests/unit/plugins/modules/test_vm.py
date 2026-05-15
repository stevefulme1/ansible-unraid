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


VMS_RESPONSE = {
    "vms": [
        {"id": "uuid-win11", "name": "Windows11", "state": "running"},
        {"id": "uuid-ubuntu", "name": "Ubuntu", "state": "shutoff"},
        {"id": "uuid-devbox", "name": "DevBox", "state": "paused"},
    ]
}


def _make_module(state, name=None, vm_id=None, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "name": name,
        "id": vm_id,
        "state": state,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestVmModule:

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_start_stopped_vm(self, MockModule, mock_get_client):
        module = _make_module("started", name="Ubuntu")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            VMS_RESPONSE,
            {"vms": [{"id": "uuid-ubuntu", "name": "Ubuntu", "state": "running"}]},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_called_once()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_start_already_running_no_change(self, MockModule, mock_get_client):
        module = _make_module("started", name="Windows11")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = VMS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_stop_running_vm(self, MockModule, mock_get_client):
        module = _make_module("stopped", name="Windows11")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            VMS_RESPONSE,
            {"vms": [{"id": "uuid-win11", "name": "Windows11", "state": "shutoff"}]},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_stop_already_stopped_no_change(self, MockModule, mock_get_client):
        module = _make_module("stopped", name="Ubuntu")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = VMS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_vm_not_found_fails(self, MockModule, mock_get_client):
        module = _make_module("started", name="NonexistentVM")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = VMS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleFailJson) as exc_info:
            run_module()

        assert "not found" in exc_info.value.kwargs["msg"]

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_check_mode_does_not_mutate(self, MockModule, mock_get_client):
        module = _make_module("started", name="Ubuntu", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = VMS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_pause_running_vm(self, MockModule, mock_get_client):
        module = _make_module("paused", name="Windows11")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            VMS_RESPONSE,
            {"vms": [{"id": "uuid-win11", "name": "Windows11", "state": "paused"}]},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_resume_paused_vm(self, MockModule, mock_get_client):
        module = _make_module("resumed", name="DevBox")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            VMS_RESPONSE,
            {"vms": [{"id": "uuid-devbox", "name": "DevBox", "state": "running"}]},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_reboot_always_changes(self, MockModule, mock_get_client):
        module = _make_module("rebooted", name="Windows11")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [VMS_RESPONSE, VMS_RESPONSE]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.get_client")
    @patch("ansible_collections.stevefulme1.unraid.plugins.modules.vm.AnsibleModule")
    def test_find_by_id(self, MockModule, mock_get_client):
        module = _make_module("stopped", vm_id="uuid-win11")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            VMS_RESPONSE,
            {"vms": [{"id": "uuid-win11", "name": "Windows11", "state": "shutoff"}]},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.vm import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
