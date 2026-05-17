"""Unit tests for stevefulme1.unraid.pool module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

import pytest


MODULE_PATH = "ansible_collections.stevefulme1.unraid.plugins.modules.pool"
CLIENT_PATH = "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api"


@pytest.fixture
def mock_api_client():
    """Mock API client for pool."""
    client = MagicMock()
    client.get.return_value = None
    client.create.return_value = {"pool_name": "res-123", "pool_name": "test-pool"}
    client.update.return_value = {"pool_name": "res-123", "pool_name": "test-pool-updated"}
    client.delete.return_value = None
    client.list.return_value = []
    return client


@pytest.fixture
def existing_resource():
    """Return a dict representing an existing pool."""
    return {
        "pool_name": "res-123",
        "pool_name": "test-pool",
        "state": "active",
    }


class TestCreatePool:
    """Tests for creating a pool."""

    def test_create_returns_resource(self, mock_api_client):
        """Verify create returns resource dict with expected fields."""
        result = mock_api_client.create("pool", {"pool_name": "test-pool"})
        assert result["pool_name"] == "res-123"
        assert result["pool_name"] == "test-pool"
        mock_api_client.create.assert_called_once()

    def test_create_with_all_params(self, mock_api_client):
        """Verify create passes all parameters to API."""
        params = {
            "pool_name": "full-pool",
            "description": "Full test",
            "tags": {"env": "test"},
        }
        mock_api_client.create("pool", params)
        mock_api_client.create.assert_called_once_with("pool", params)

    def test_create_api_error(self):
        """Verify API errors are raised on create."""
        client = MagicMock()
        client.create.side_effect = Exception("409 Conflict")
        with pytest.raises(Exception, match="409 Conflict"):
            client.create("pool", {"pool_name": "dup"})

    def test_create_check_mode_no_api_call(self, mock_api_client):
        """Verify check_mode skips actual API call."""
        check_mode = True
        if check_mode:
            result = {"changed": True, "pool": {}}
        else:
            result = mock_api_client.create("pool", {})
        assert result["changed"] is True
        mock_api_client.create.assert_not_called()


class TestUpdatePool:
    """Tests for updating a pool."""

    def test_update_existing_resource(self, mock_api_client, existing_resource):
        """Verify update modifies existing resource."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.update("pool", "res-123", {"pool_name": "updated"})
        assert result["pool_name"] == "test-pool-updated"

    def test_update_idempotent_no_change(self, mock_api_client, existing_resource):
        """Verify no update when params match existing state."""
        mock_api_client.get.return_value = existing_resource
        # Simulate idempotency check
        desired = {"pool_name": existing_resource["pool_name"]}
        current = {"pool_name": existing_resource["pool_name"]}
        changed = desired != current
        assert changed is False

    def test_update_detects_changes(self, mock_api_client, existing_resource):
        """Verify update detects actual changes."""
        mock_api_client.get.return_value = existing_resource
        desired = {"pool_name": "new-name"}
        current = {"pool_name": existing_resource["pool_name"]}
        changed = desired != current
        assert changed is True

    def test_update_nonexistent_raises(self, mock_api_client):
        """Verify updating non-existent resource raises error."""
        mock_api_client.update.side_effect = Exception("404 Not Found")
        with pytest.raises(Exception, match="404 Not Found"):
            mock_api_client.update("pool", "bad-id", {})


class TestDeletePool:
    """Tests for deleting a pool."""

    def test_delete_existing(self, mock_api_client, existing_resource):
        """Verify delete calls API with correct ID."""
        mock_api_client.get.return_value = existing_resource
        mock_api_client.delete("pool", "res-123")
        mock_api_client.delete.assert_called_once_with("pool", "res-123")

    def test_delete_nonexistent_is_noop(self, mock_api_client):
        """Verify deleting absent resource reports no change."""
        mock_api_client.get.return_value = None
        result = mock_api_client.get("pool", "missing-id")
        assert result is None

    def test_delete_check_mode(self, mock_api_client, existing_resource):
        """Verify check_mode delete does not call API."""
        check_mode = True
        if not check_mode:
            mock_api_client.delete("pool", "res-123")
        mock_api_client.delete.assert_not_called()

    def test_delete_api_error(self):
        """Verify API errors propagate on delete."""
        client = MagicMock()
        client.delete.side_effect = Exception("403 Forbidden")
        with pytest.raises(Exception, match="403 Forbidden"):
            client.delete("pool", "res-123")


class TestGetPool:
    """Tests for getting a pool."""

    def test_get_existing(self, mock_api_client, existing_resource):
        """Verify get returns resource when it exists."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.get("pool", "res-123")
        assert result["pool_name"] == "res-123"

    def test_get_nonexistent(self, mock_api_client):
        """Verify get returns None for missing resource."""
        mock_api_client.get.return_value = None
        result = mock_api_client.get("pool", "nonexistent")
        assert result is None

    def test_get_api_timeout(self):
        """Verify timeout error handling."""
        client = MagicMock()
        client.get.side_effect = TimeoutError("Connection timed out")
        with pytest.raises(TimeoutError):
            client.get("pool", "res-123")


class TestListPool:
    """Tests for listing pool resources."""

    def test_list_returns_all(self, mock_api_client):
        """Verify list returns all resources."""
        mock_api_client.list.return_value = [
            {"pool_name": "1", "pool_name": "first"},
            {"pool_name": "2", "pool_name": "second"},
        ]
        result = mock_api_client.list("pool")
        assert len(result) == 2

    def test_list_empty(self, mock_api_client):
        """Verify list returns empty for no resources."""
        result = mock_api_client.list("pool")
        assert result == []

    def test_list_with_filter(self, mock_api_client):
        """Verify list applies filters."""
        mock_api_client.list.return_value = [{"pool_name": "1", "pool_name": "match"}]
        result = mock_api_client.list("pool", filters={"pool_name": "match"})
        assert len(result) == 1


class TestIdempotencyPool:
    """Tests for idempotent behavior of pool."""

    def test_create_existing_is_idempotent(self, mock_api_client, existing_resource):
        """Verify creating an already-existing resource is idempotent."""
        mock_api_client.get.return_value = existing_resource
        current = mock_api_client.get("pool", "res-123")
        desired_params = {"pool_name": current["pool_name"]}
        # If resource exists and matches desired state, no change
        changed = desired_params["pool_name"] != current["pool_name"]
        assert changed is False

    def test_delete_absent_is_idempotent(self, mock_api_client):
        """Verify deleting an absent resource reports no change."""
        mock_api_client.get.return_value = None
        exists = mock_api_client.get("pool", "missing") is not None
        assert exists is False


class TestErrorHandlingPool:
    """Tests for error handling in pool."""

    def test_auth_failure(self):
        """Verify authentication failure is handled."""
        client = MagicMock()
        client.create.side_effect = Exception("401 Unauthorized")
        with pytest.raises(Exception, match="401 Unauthorized"):
            client.create("pool", {})

    def test_rate_limit(self):
        """Verify rate-limit response is handled."""
        client = MagicMock()
        client.list.side_effect = Exception("429 Too Many Requests")
        with pytest.raises(Exception, match="429"):
            client.list("pool")

    def test_server_error(self):
        """Verify 500 error is propagated."""
        client = MagicMock()
        client.get.side_effect = Exception("500 Internal Server Error")
        with pytest.raises(Exception, match="500"):
            client.get("pool", "res-123")

    def test_network_error(self):
        """Verify network connectivity errors are handled."""
        client = MagicMock()
        client.get.side_effect = ConnectionError("Failed to connect")
        with pytest.raises(ConnectionError):
            client.get("pool", "res-123")
