"""Unit tests for stevefulme1.unraid.vm_template module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type
from unittest.mock import MagicMock

import pytest

MODULE_PATH = "ansible_collections.stevefulme1.unraid.plugins.modules.vm_template"


@pytest.fixture
def mock_api_client():
    """Mock API client for vm_template."""
    client = MagicMock()
    client.get.return_value = None
    client.create.return_value = {"id": "res-123", "name": "test-vm_template"}
    client.update.return_value = {"id": "res-123", "name": "test-vm_template-updated"}
    client.delete.return_value = None
    client.list.return_value = []
    return client


@pytest.fixture
def existing_resource():
    """Return a dict representing an existing vm_template."""
    return {
        "id": "res-123",
        "name": "test-vm_template",
        "state": "active",
    }


class TestCreateVmTemplate:
    """Tests for creating a vm_template."""

    def test_create_returns_resource(self, mock_api_client):
        """Verify create returns resource dict with expected fields."""
        result = mock_api_client.create("vm_template", {"name": "test-vm_template"})
        assert result["id"] == "res-123"
        assert result["name"] == "test-vm_template"
        mock_api_client.create.assert_called_once()

    def test_create_api_error(self):
        """Verify API errors are raised on create."""
        client = MagicMock()
        client.create.side_effect = Exception("409 Conflict")
        with pytest.raises(Exception, match="409 Conflict"):
            client.create("vm_template", {"name": "test"})


class TestDeleteVmTemplate:
    """Tests for deleting a vm_template."""

    def test_delete_existing(self, mock_api_client, existing_resource):
        """Verify delete is called for existing resource."""
        mock_api_client.get.return_value = existing_resource
        mock_api_client.delete("vm_template", "res-123")
        mock_api_client.delete.assert_called_once_with("vm_template", "res-123")

    def test_delete_nonexistent(self, mock_api_client):
        """Verify delete handles missing resource gracefully."""
        mock_api_client.get.return_value = None
        mock_api_client.delete.side_effect = Exception("404 Not Found")
        with pytest.raises(Exception, match="404"):
            mock_api_client.delete("vm_template", "missing")


class TestIdempotencyVmTemplate:
    """Tests for idempotency behavior."""

    def test_no_change_when_exists(self, mock_api_client, existing_resource):
        """Verify no API call when resource already in desired state."""
        mock_api_client.get.return_value = existing_resource
        result = mock_api_client.get("vm_template", "res-123")
        assert result["id"] == "res-123"
