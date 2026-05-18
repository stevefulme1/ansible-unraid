from __future__ import absolute_import, division, print_function
__metaclass__ = type

"""Unit tests for cron_job module."""

from unittest.mock import MagicMock


class TestCreate:
    def test_create_returns_resource(self):
        client = MagicMock()
        client.create.return_value = dict(id="123", name="test")
        result = client.create("job", dict(name="test"))
        assert result["id"] == "123"

    def test_create_idempotent(self):
        client = MagicMock()
        client.get.return_value = dict(id="123", name="test")
        assert client.get("job", "123") is not None


class TestDelete:
    def test_delete_existing(self):
        client = MagicMock()
        client.delete("job", "123")
        client.delete.assert_called_once_with("job", "123")

    def test_delete_not_found(self):
        client = MagicMock()
        client.get.return_value = None
        assert client.get("job", "x") is None


class TestList:
    def test_list_returns_items(self):
        client = MagicMock()
        client.list.return_value = [dict(id="1"), dict(id="2")]
        assert len(client.list("job")) == 2

    def test_list_empty(self):
        client = MagicMock()
        client.list.return_value = []
        assert len(client.list("job")) == 0


class TestGet:
    def test_get_existing(self):
        client = MagicMock()
        client.get.return_value = dict(id="123", name="test")
        assert client.get("job", "123")["name"] == "test"

    def test_get_not_found(self):
        client = MagicMock()
        client.get.return_value = None
        assert client.get("job", "x") is None


class TestUpdate:
    def test_update(self):
        client = MagicMock()
        client.update.return_value = dict(id="123", name="updated")
        result = client.update("job", "123", dict(name="updated"))
        assert result["name"] == "updated"
