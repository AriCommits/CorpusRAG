from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from db.collections_cli import collections_cmd


@pytest.fixture
def runner():
    return CliRunner()


def test_list_collections(runner):
    with patch("db.collections_cli.load_cli_db") as mock_load:
        mock_db = MagicMock()
        mock_col = MagicMock()
        mock_col.name = "test_col"
        mock_db.list_collections.return_value = [mock_col]
        mock_db.get_collection_stats.return_value = {
            "doc_count": 5,
            "size_estimate": 100,
        }
        mock_load.return_value = (MagicMock(), mock_db)

        result = runner.invoke(collections_cmd, ["list"])
        assert result.exit_code == 0
        assert "test_col" in result.output


def test_list_collections_empty(runner):
    with patch("db.collections_cli.load_cli_db") as mock_load:
        mock_db = MagicMock()
        mock_db.list_collections.return_value = []
        mock_load.return_value = (MagicMock(), mock_db)

        result = runner.invoke(collections_cmd, ["list"])
        assert result.exit_code == 0
        assert "No collections found" in result.output


def test_delete_collection(runner):
    with patch("db.collections_cli.load_cli_db") as mock_load:
        mock_db = MagicMock()
        mock_load.return_value = (MagicMock(), mock_db)

        result = runner.invoke(collections_cmd, ["delete", "test_col"])
        assert result.exit_code == 0
        mock_db.delete_collection.assert_called_once_with("test_col")
