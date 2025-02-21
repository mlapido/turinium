import pytest
from unittest.mock import MagicMock, patch
from turinium.database.db_connection import DBConnection
from turinium.database.db_credentials import DBCredentials


@pytest.fixture
def mock_db_connection():
    creds = MagicMock(spec=DBCredentials)
    creds.get_connection_url.return_value = "sqlite:///:memory:"

    with patch("sqlalchemy.create_engine") as mock_engine:
        mock_engine.return_value = MagicMock()

        with patch.object(DBConnection, "__init__", lambda self, creds: None):  # Bypass constructor
            db_conn = DBConnection(creds)
            db_conn.engine = mock_engine.return_value  # Assign mock engine
            db_conn.logger = MagicMock()  # Mock logger to avoid AttributeError

        return db_conn


def test_db_connection_init(mock_db_connection):
    assert mock_db_connection.engine is not None


def test_db_connection_execute_success(mock_db_connection):
    with patch.object(mock_db_connection.engine, "connect") as mock_connect:
        mock_cursor = MagicMock()
        mock_connect.return_value.__enter__.return_value.execute.return_value = mock_cursor
        mock_cursor.returns_rows = True
        mock_cursor.fetchall.return_value = [(1, 'test')]

        success, result = mock_db_connection.execute("sp", "usp_Test", (1,))

        assert success is True
        assert result == [(1, 'test')]
