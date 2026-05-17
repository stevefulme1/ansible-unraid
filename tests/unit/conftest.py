"""Shared test fixtures for stevefulme1.unraid collection."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure collection path is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


@pytest.fixture
def mock_module():
    """Create a mock AnsibleModule."""
    module = MagicMock()
    module.params = {
        "state": "present",
        "api_url": "https://unraid.local",
        "api_key": "test-unraid-key",
        "validate_certs": True,
    }
    module.check_mode = False
    module.fail_json = MagicMock(side_effect=SystemExit(1))
    module.exit_json = MagicMock(side_effect=SystemExit(0))
    return module


@pytest.fixture
def mock_module_check_mode(mock_module):
    """Create a mock AnsibleModule in check mode."""
    mock_module.check_mode = True
    return mock_module


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock()
    client.get.return_value = None
    client.create.return_value = {"id": "test-123", "name": "test-resource"}
    client.update.return_value = {"id": "test-123", "name": "test-resource-updated"}
    client.delete.return_value = None
    client.list.return_value = []
    return client


@pytest.fixture
def mock_client_existing(mock_client):
    """Create a mock API client that returns an existing resource."""
    mock_client.get.return_value = {"id": "test-123", "name": "test-resource"}
    return mock_client


@pytest.fixture
def error_client():
    """Create a mock API client that raises errors."""
    client = MagicMock()
    client.get.side_effect = Exception("API connection error")
    client.create.side_effect = Exception("API creation error")
    client.update.side_effect = Exception("API update error")
    client.delete.side_effect = Exception("API deletion error")
    return client
