from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api import (
    UnraidClient,
    UnraidError,
    unraid_argument_spec,
    get_client,
)


# ---------------------------------------------------------------------------
# UnraidClient.__init__
# ---------------------------------------------------------------------------

class TestUnraidClientInit:
    """Test URL normalisation in the constructor."""

    def test_appends_graphql_when_missing(self):
        client = UnraidClient("https://tower.local", "key123")
        assert client.api_url == "https://tower.local/graphql"

    def test_preserves_graphql_when_present(self):
        client = UnraidClient("https://tower.local/graphql", "key123")
        assert client.api_url == "https://tower.local/graphql"

    def test_strips_trailing_slash_then_appends(self):
        client = UnraidClient("https://tower.local/", "key123")
        assert client.api_url == "https://tower.local/graphql"

    def test_does_not_double_append(self):
        client = UnraidClient("https://tower.local/graphql/", "key123")
        # trailing slash is stripped, path already ends with /graphql
        assert client.api_url == "https://tower.local/graphql"

    def test_stores_api_key(self):
        client = UnraidClient("https://tower.local", "secret")
        assert client.api_key == "secret"

    def test_default_validate_certs(self):
        client = UnraidClient("https://tower.local", "key")
        assert client.validate_certs is True

    def test_custom_validate_certs(self):
        client = UnraidClient("https://tower.local", "key", validate_certs=False)
        assert client.validate_certs is False

    def test_default_timeout(self):
        client = UnraidClient("https://tower.local", "key")
        assert client.timeout == 30

    def test_custom_timeout(self):
        client = UnraidClient("https://tower.local", "key", timeout=60)
        assert client.timeout == 60


# ---------------------------------------------------------------------------
# UnraidClient.query
# ---------------------------------------------------------------------------

class TestUnraidClientQuery:
    """Test that query() builds the correct payload and returns data."""

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_query_builds_correct_payload(self, mock_open_url):
        response_body = json.dumps({"data": {"info": {"hostname": "tower"}}})
        mock_response = MagicMock()
        mock_response.read.return_value = response_body.encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "mykey")
        result = client.query("{ info { hostname } }")

        assert result == {"info": {"hostname": "tower"}}

        # Verify the call to open_url
        call_args = mock_open_url.call_args
        assert call_args[0][0] == "https://tower.local/graphql"
        sent_data = json.loads(call_args[1]["data"])
        assert sent_data == {"query": "{ info { hostname } }"}
        assert call_args[1]["headers"]["x-api-key"] == "mykey"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["method"] == "POST"

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_query_with_variables(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": {}}).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        client.query("query($id: String!) { disk(id: $id) { name } }", variables={"id": "disk1"})

        sent_data = json.loads(mock_open_url.call_args[1]["data"])
        assert sent_data["variables"] == {"id": "disk1"}

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_query_without_variables_omits_key(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": {}}).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        client.query("{ info { hostname } }")

        sent_data = json.loads(mock_open_url.call_args[1]["data"])
        assert "variables" not in sent_data

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_query_returns_empty_data_when_missing(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({}).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        result = client.query("{ info { hostname } }")
        assert result == {}


# ---------------------------------------------------------------------------
# UnraidClient.mutate
# ---------------------------------------------------------------------------

class TestUnraidClientMutate:
    """Test that mutate() delegates to query()."""

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_mutate_delegates_to_query(self, mock_open_url):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"data": {"array": {"setState": {"state": "STARTED"}}}}
        ).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        result = client.mutate(
            "mutation { array { start } }",
            variables={"desiredState": "START"},
        )
        assert result == {"array": {"setState": {"state": "STARTED"}}}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestUnraidClientErrors:
    """Test error paths in _request."""

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_graphql_errors_raise_unraid_error(self, mock_open_url):
        body = {
            "data": None,
            "errors": [{"message": "Field 'xyz' not found"}],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(body).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        with pytest.raises(UnraidError, match="Field 'xyz' not found"):
            client.query("{ xyz }")

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_graphql_multiple_errors_joined(self, mock_open_url):
        body = {
            "errors": [
                {"message": "Error one"},
                {"message": "Error two"},
            ],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(body).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        with pytest.raises(UnraidError, match="Error one; Error two"):
            client.query("{ broken }")

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_graphql_error_stores_errors_list(self, mock_open_url):
        errors_list = [{"message": "bad query"}]
        body = {"errors": errors_list}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(body).encode("utf-8")
        mock_open_url.return_value = mock_response

        client = UnraidClient("https://tower.local", "key")
        with pytest.raises(UnraidError) as exc_info:
            client.query("{ broken }")
        assert exc_info.value.errors == errors_list

    @patch(
        "ansible_collections.stevefulme1.unraid.plugins.module_utils.unraid_api.open_url"
    )
    def test_connection_error_raises_unraid_error(self, mock_open_url):
        mock_open_url.side_effect = Exception("Connection refused")

        client = UnraidClient("https://tower.local", "key")
        with pytest.raises(UnraidError, match="Failed to connect.*Connection refused"):
            client.query("{ info { hostname } }")

    def test_unraid_error_default_attributes(self):
        err = UnraidError("test error")
        assert str(err) == "test error"
        assert err.status_code is None
        assert err.errors == []

    def test_unraid_error_with_attributes(self):
        err = UnraidError("test", status_code=500, errors=[{"message": "fail"}])
        assert err.status_code == 500
        assert err.errors == [{"message": "fail"}]


# ---------------------------------------------------------------------------
# unraid_argument_spec
# ---------------------------------------------------------------------------

class TestUnraidArgumentSpec:
    """Test the shared argument spec helper."""

    def test_returns_expected_keys(self):
        spec = unraid_argument_spec()
        assert "api_url" in spec
        assert "api_key" in spec
        assert "validate_certs" in spec
        assert "api_timeout" in spec

    def test_api_url_is_required(self):
        spec = unraid_argument_spec()
        assert spec["api_url"]["required"] is True

    def test_api_key_is_no_log(self):
        spec = unraid_argument_spec()
        assert spec["api_key"]["no_log"] is True

    def test_validate_certs_default(self):
        spec = unraid_argument_spec()
        assert spec["validate_certs"]["default"] is True

    def test_api_timeout_default(self):
        spec = unraid_argument_spec()
        assert spec["api_timeout"]["default"] == 30


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------

class TestGetClient:
    """Test the factory function."""

    def test_creates_client_from_module_params(self, mock_module):
        client = get_client(mock_module)
        assert isinstance(client, UnraidClient)
        assert client.api_url == "https://tower.local/graphql"
        assert client.api_key == "test-api-key-12345"
        assert client.validate_certs is True
        assert client.timeout == 30

    def test_creates_client_with_custom_params(self, mock_module):
        mock_module.params["api_url"] = "https://nas.home:8443/graphql"
        mock_module.params["validate_certs"] = False
        mock_module.params["api_timeout"] = 60
        client = get_client(mock_module)
        assert client.api_url == "https://nas.home:8443/graphql"
        assert client.validate_certs is False
        assert client.timeout == 60
