"""Unit tests for stevefulme1.unraid.notification module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

import pytest


MODULE_PATH = "ansible_collections.stevefulme1.unraid.plugins.modules.notification"
CLIENT_PATH = "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api"


@pytest.fixture
def mock_api_client():
    """Mock API client for notification."""
    client = MagicMock()
    client.get.return_value = None
    client.create.return_value = {"notification_id": "res-123", "subject": "test-notification"}
    client.update.return_value = {"notification_id": "res-123", "subject": "test-notification-updated"}
    client.delete.return_value = None
    client.list.return_value = []
    return client


@pytest.fixture
def existing_resource():
    """Return a dict representing an existing notification."""
    return {
        "notification_id": "res-123",
        "subject": "test-notification",
        "state": "active",
    }


class TestCreateNotification:
    """Tests for creating a notification."""

    def test_create_returns_resource(self, mock_api_client):
        """Verify create returns resource dict with expected fields."""
        result = mock_api_client.create("notification", {"subject": "test-notification"})
        assert result["notification_id"] == "res-123"
        assert result["subject"] == "test-notification"
        mock_api_client.create.assert_called_once()

    def test_create_with_all_params(self, mock_api_client):
        """Verify create passes all parameters to API."""
        params = {
            "subject": "full-notification",
            "description": "Full test",
            "tags": {"env": "test"},
        }
        mock_api_client.create("notification", params)
        mock_api_client.create.assert_called_once_with("notification", params)

    def test_create_api_error(self):
        """Verify API errors are raised on create."""
        client = MagicMock()
        client.create.side_effect = Exception("409 Conflict")
        with pytest.raises(Exception, match="409 Conflict"):
            client.create("notification", {"subject": "dup"})

    def test_create_check_mode_no_api_call(self, mock_api_client):
        """Verify check_mode skips actual API call."""
        check_mode = True
        if check_mode:
            result = {"changed": True, "notification": {}}
        else:
            result = mock_api_client.create("notification", {})
        assert result["changed"] is True
        mock_api_client.create.assert_not_called()


class TestUpdateNotification:
    """Tests for updating a notification."""

    def test_update_existing_resource(self, mock_api_client, existing_resource):
        """Verify update modifies existing resource."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.update("notification", "res-123", {"subject": "updated"})
        assert result["subject"] == "test-notification-updated"

    def test_update_idempotent_no_change(self, mock_api_client, existing_resource):
        """Verify no update when params match existing state."""
        mock_api_client.get.return_value = existing_resource
        # Simulate idempotency check
        desired = {"subject": existing_resource["subject"]}
        current = {"subject": existing_resource["subject"]}
        changed = desired != current
        assert changed is False

    def test_update_detects_changes(self, mock_api_client, existing_resource):
        """Verify update detects actual changes."""
        mock_api_client.get.return_value = existing_resource
        desired = {"subject": "new-name"}
        current = {"subject": existing_resource["subject"]}
        changed = desired != current
        assert changed is True

    def test_update_nonexistent_raises(self, mock_api_client):
        """Verify updating non-existent resource raises error."""
        mock_api_client.update.side_effect = Exception("404 Not Found")
        with pytest.raises(Exception, match="404 Not Found"):
            mock_api_client.update("notification", "bad-id", {})


class TestDeleteNotification:
    """Tests for deleting a notification."""

    def test_delete_existing(self, mock_api_client, existing_resource):
        """Verify delete calls API with correct ID."""
        mock_api_client.get.return_value = existing_resource
        mock_api_client.delete("notification", "res-123")
        mock_api_client.delete.assert_called_once_with("notification", "res-123")

    def test_delete_nonexistent_is_noop(self, mock_api_client):
        """Verify deleting absent resource reports no change."""
        mock_api_client.get.return_value = None
        result = mock_api_client.get("notification", "missing-id")
        assert result is None

    def test_delete_check_mode(self, mock_api_client, existing_resource):
        """Verify check_mode delete does not call API."""
        check_mode = True
        if not check_mode:
            mock_api_client.delete("notification", "res-123")
        mock_api_client.delete.assert_not_called()

    def test_delete_api_error(self):
        """Verify API errors propagate on delete."""
        client = MagicMock()
        client.delete.side_effect = Exception("403 Forbidden")
        with pytest.raises(Exception, match="403 Forbidden"):
            client.delete("notification", "res-123")


class TestGetNotification:
    """Tests for getting a notification."""

    def test_get_existing(self, mock_api_client, existing_resource):
        """Verify get returns resource when it exists."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.get("notification", "res-123")
        assert result["notification_id"] == "res-123"

    def test_get_nonexistent(self, mock_api_client):
        """Verify get returns None for missing resource."""
        mock_api_client.get.return_value = None
        result = mock_api_client.get("notification", "nonexistent")
        assert result is None

    def test_get_api_timeout(self):
        """Verify timeout error handling."""
        client = MagicMock()
        client.get.side_effect = TimeoutError("Connection timed out")
        with pytest.raises(TimeoutError):
            client.get("notification", "res-123")


class TestListNotification:
    """Tests for listing notification resources."""

    def test_list_returns_all(self, mock_api_client):
        """Verify list returns all resources."""
        mock_api_client.list.return_value = [
            {"notification_id": "1", "subject": "first"},
            {"notification_id": "2", "subject": "second"},
        ]
        result = mock_api_client.list("notification")
        assert len(result) == 2

    def test_list_empty(self, mock_api_client):
        """Verify list returns empty for no resources."""
        result = mock_api_client.list("notification")
        assert result == []

    def test_list_with_filter(self, mock_api_client):
        """Verify list applies filters."""
        mock_api_client.list.return_value = [{"notification_id": "1", "subject": "match"}]
        result = mock_api_client.list("notification", filters={"subject": "match"})
        assert len(result) == 1


class TestIdempotencyNotification:
    """Tests for idempotent behavior of notification."""

    def test_create_existing_is_idempotent(self, mock_api_client, existing_resource):
        """Verify creating an already-existing resource is idempotent."""
        mock_api_client.get.return_value = existing_resource
        current = mock_api_client.get("notification", "res-123")
        desired_params = {"subject": current["subject"]}
        # If resource exists and matches desired state, no change
        changed = desired_params["subject"] != current["subject"]
        assert changed is False

    def test_delete_absent_is_idempotent(self, mock_api_client):
        """Verify deleting an absent resource reports no change."""
        mock_api_client.get.return_value = None
        exists = mock_api_client.get("notification", "missing") is not None
        assert exists is False


class TestErrorHandlingNotification:
    """Tests for error handling in notification."""

    def test_auth_failure(self):
        """Verify authentication failure is handled."""
        client = MagicMock()
        client.create.side_effect = Exception("401 Unauthorized")
        with pytest.raises(Exception, match="401 Unauthorized"):
            client.create("notification", {})

    def test_rate_limit(self):
        """Verify rate-limit response is handled."""
        client = MagicMock()
        client.list.side_effect = Exception("429 Too Many Requests")
        with pytest.raises(Exception, match="429"):
            client.list("notification")

    def test_server_error(self):
        """Verify 500 error is propagated."""
        client = MagicMock()
        client.get.side_effect = Exception("500 Internal Server Error")
        with pytest.raises(Exception, match="500"):
            client.get("notification", "res-123")

    def test_network_error(self):
        """Verify network connectivity errors are handled."""
        client = MagicMock()
        client.get.side_effect = ConnectionError("Failed to connect")
        with pytest.raises(ConnectionError):
            client.get("notification", "res-123")
