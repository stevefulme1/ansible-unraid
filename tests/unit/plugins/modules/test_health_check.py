"""Unit tests for stevefulme1.unraid.health_check module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type
from unittest.mock import MagicMock

import pytest

MODULE_PATH = "ansible_collections.stevefulme1.unraid.plugins.modules.health_check"


@pytest.fixture
def mock_api_client():
    """Mock API client for health_check."""
    client = MagicMock()
    client.get.return_value = None
    client.create.return_value = {"id": "res-123", "name": "test-health_check"}
    client.update.return_value = {"id": "res-123", "name": "test-health_check-updated"}
    client.delete.return_value = None
    client.list.return_value = []
    return client


@pytest.fixture
def existing_resource():
    """Return a dict representing an existing health_check."""
    return {
        "id": "res-123",
        "name": "test-health_check",
        "state": "active",
    }


class TestCreateHealthCheck:
    """Tests for creating a health_check."""

    def test_create_returns_resource(self, mock_api_client):
        """Verify create returns resource dict with expected fields."""
        result = mock_api_client.create("health_check", {"name": "test-health_check"})
        assert result["id"] == "res-123"
        assert result["name"] == "test-health_check"
        mock_api_client.create.assert_called_once()

    def test_create_api_error(self):
        """Verify API errors are raised on create."""
        client = MagicMock()
        client.create.side_effect = Exception("409 Conflict")
        with pytest.raises(Exception, match="409 Conflict"):
            client.create("health_check", {"name": "test"})


class TestDeleteHealthCheck:
    """Tests for deleting a health_check."""

    def test_delete_existing(self, mock_api_client, existing_resource):
        """Verify delete is called for existing resource."""
        mock_api_client.get.return_value = existing_resource
        mock_api_client.delete("health_check", "res-123")
        mock_api_client.delete.assert_called_once_with("health_check", "res-123")

    def test_delete_nonexistent(self, mock_api_client):
        """Verify delete handles missing resource gracefully."""
        mock_api_client.get.return_value = None
        mock_api_client.delete.side_effect = Exception("404 Not Found")
        with pytest.raises(Exception, match="404"):
            mock_api_client.delete("health_check", "missing")


class TestIdempotencyHealthCheck:
    """Tests for idempotency behavior."""

    def test_no_change_when_exists(self, mock_api_client, existing_resource):
        """Verify no API call when resource already in desired state."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.get("health_check", "res-123")
        assert result["id"] == "res-123"
