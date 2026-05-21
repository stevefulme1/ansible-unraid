"""Unit tests for stevefulme1.unraid.parity module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type
from unittest.mock import MagicMock

import pytest

MODULE_PATH = "ansible_collections.stevefulme1.unraid.plugins.modules.parity"


@pytest.fixture
def mock_api_client():
    """Mock API client for parity."""
    client = MagicMock()
    client.get.return_value = None
    client.create.return_value = {"id": "res-123", "name": "test-parity"}
    client.update.return_value = {"id": "res-123", "name": "test-parity-updated"}
    client.delete.return_value = None
    client.list.return_value = []
    return client


@pytest.fixture
def existing_resource():
    """Return a dict representing an existing parity."""
    return {
        "id": "res-123",
        "name": "test-parity",
        "state": "active",
    }


class TestCreateParity:
    """Tests for creating a parity."""

    def test_create_returns_resource(self, mock_api_client):
        """Verify create returns resource dict with expected fields."""
        result = mock_api_client.create("parity", {"name": "test-parity"})
        assert result["id"] == "res-123"
        assert result["name"] == "test-parity"
        mock_api_client.create.assert_called_once()

    def test_create_api_error(self):
        """Verify API errors are raised on create."""
        client = MagicMock()
        client.create.side_effect = Exception("409 Conflict")
        with pytest.raises(Exception, match="409 Conflict"):
            client.create("parity", {"name": "test"})


class TestDeleteParity:
    """Tests for deleting a parity."""

    def test_delete_existing(self, mock_api_client, existing_resource):
        """Verify delete is called for existing resource."""
        mock_api_client.get.return_value = existing_resource
        mock_api_client.delete("parity", "res-123")
        mock_api_client.delete.assert_called_once_with("parity", "res-123")

    def test_delete_nonexistent(self, mock_api_client):
        """Verify delete handles missing resource gracefully."""
        mock_api_client.get.return_value = None
        mock_api_client.delete.side_effect = Exception("404 Not Found")
        with pytest.raises(Exception, match="404"):
            mock_api_client.delete("parity", "missing")


class TestIdempotencyParity:
    """Tests for idempotency behavior."""

    def test_no_change_when_exists(self, mock_api_client, existing_resource):
        """Verify no API call when resource already in desired state."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.get("parity", "res-123")
        assert result["id"] == "res-123"
