from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import MagicMock


class AnsibleExitJson(Exception):
    """Exception raised by mocked exit_json to halt module execution."""
    def __init__(self, kwargs):
        super().__init__()
        self.kwargs = kwargs


class AnsibleFailJson(Exception):
    """Exception raised by mocked fail_json to halt module execution."""
    def __init__(self, kwargs):
        super().__init__()
        self.kwargs = kwargs


@pytest.fixture
def mock_module():
    """Create a mock AnsibleModule with standard Unraid params."""
    module = MagicMock()
    module.params = {
        "api_url": "https://tower.local",
        "api_key": "test-api-key-12345",
        "validate_certs": True,
        "api_timeout": 30,
    }
    module.check_mode = False

    module.exit_json = MagicMock(side_effect=lambda **kw: (_ for _ in ()).throw(AnsibleExitJson(kw)))
    module.fail_json = MagicMock(side_effect=lambda **kw: (_ for _ in ()).throw(AnsibleFailJson(kw)))

    return module


@pytest.fixture
def mock_client():
    """Create a mock UnraidClient with query/mutate stubs."""
    client = MagicMock()
    client.api_url = "https://tower.local/graphql"
    client.api_key = "test-api-key-12345"
    client.validate_certs = True
    client.timeout = 30
    client.query = MagicMock(return_value={})
    client.mutate = MagicMock(return_value={})
    return client
