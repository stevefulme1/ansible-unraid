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


CONTAINERS_RESPONSE = {
    "docker": {
        "containers": [
            {"id": "abc123def456", "names": ["/plex"], "state": "running", "autoStart": True},
            {"id": "789xyz000111", "names": ["/nginx"], "state": "exited", "autoStart": False},
            {"id": "paused999888", "names": ["/grafana"], "state": "paused", "autoStart": True},
        ]
    }
}


def _make_module(state, name=None, container_id=None, remove_image=False, check_mode=False):
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "key",
        "validate_certs": True,
        "api_timeout": 30,
        "name": name,
        "id": container_id,
        "state": state,
        "remove_image": remove_image,
    }
    module.check_mode = check_mode
    module.exit_json = MagicMock(side_effect=_exit_json)
    module.fail_json = MagicMock(side_effect=_fail_json)
    return module


class TestDockerContainerModule:

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_start_stopped_container(self, MockModule, mock_get_client):
        """Starting a stopped container should trigger a mutation."""
        module = _make_module("started", name="nginx")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            CONTAINERS_RESPONSE,
            {"docker": {"containers": [
                {"id": "789xyz000111", "names": ["/nginx"], "state": "running", "autoStart": False},
            ]}},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_called_once()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_start_already_running_no_change(self, MockModule, mock_get_client):
        """Starting an already-running container should report no change."""
        module = _make_module("started", name="plex")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = CONTAINERS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False
        client.mutate.assert_not_called()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_stop_running_container(self, MockModule, mock_get_client):
        """Stopping a running container should trigger a mutation."""
        module = _make_module("stopped", name="plex")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            CONTAINERS_RESPONSE,
            {"docker": {"containers": [
                {"id": "abc123def456", "names": ["/plex"], "state": "exited", "autoStart": True},
            ]}},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_container_not_found_fails(self, MockModule, mock_get_client):
        """Requesting a non-existent container should call fail_json."""
        module = _make_module("started", name="nonexistent")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = CONTAINERS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleFailJson) as exc_info:
            run_module()

        assert "not found" in exc_info.value.kwargs["msg"]

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_remove_with_image(self, MockModule, mock_get_client):
        """Removing a container with remove_image=True should pass withImage."""
        module = _make_module("absent", name="plex", remove_image=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = CONTAINERS_RESPONSE
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
        mutate_call = client.mutate.call_args
        assert mutate_call[1]["variables"]["withImage"] is True

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_remove_already_absent(self, MockModule, mock_get_client):
        """Removing a container that does not exist should report no change."""
        module = _make_module("absent", name="ghost")
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = CONTAINERS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is False
        client.mutate.assert_not_called()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_check_mode_does_not_mutate(self, MockModule, mock_get_client):
        """Check mode should report changed but not call mutate."""
        module = _make_module("stopped", name="plex", check_mode=True)
        MockModule.return_value = module

        client = MagicMock()
        client.query.return_value = CONTAINERS_RESPONSE
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
        client.mutate.assert_not_called()

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_find_by_id(self, MockModule, mock_get_client):
        """Finding a container by ID prefix should work."""
        module = _make_module("stopped", container_id="abc123")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            CONTAINERS_RESPONSE,
            {"docker": {"containers": [
                {"id": "abc123def456", "names": ["/plex"], "state": "exited", "autoStart": True},
            ]}},
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.get_client"
    )
    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.modules.docker_container.AnsibleModule"
    )
    def test_restart_always_changes(self, MockModule, mock_get_client):
        """Restart should always report changed, even if running."""
        module = _make_module("restarted", name="plex")
        MockModule.return_value = module

        client = MagicMock()
        client.query.side_effect = [
            CONTAINERS_RESPONSE,
            CONTAINERS_RESPONSE,
        ]
        client.mutate.return_value = {}
        mock_get_client.return_value = client

        from ansible_collections.stevefulme1.unraid.plugins.modules.docker_container import run_module
        with pytest.raises(AnsibleExitJson) as exc_info:
            run_module()

        assert exc_info.value.kwargs["changed"] is True
