from unittest.mock import MagicMock, patch

from tools.rag.tui_collections import CollectionManagerScreen


def test_collections_screen_mount():
    with patch("tools.rag.tui_collections.load_cli_db") as mock_load:
        mock_db = MagicMock()
        mock_load.return_value = (MagicMock(), mock_db)
        screen = CollectionManagerScreen()
        assert screen.db == mock_db
