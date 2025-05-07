import pytest
from unittest.mock import MagicMock, patch
from turinium.database.db_router import DBRouter


@pytest.fixture
def mock_db_router():
    with patch("turinium.database.db_connection.DBConnection") as MockDBConnection:
        db_router = DBRouter()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = (True, [(1, "data")])
        MockDBConnection.return_value = mock_connection
        db_router._connections["db1"] = mock_connection  # Ensure mock is added to the router
        return db_router


def test_db_router_load_databases(mock_db_router):
    db_configs = {"db1": {"db_type": "postgres", "server": "localhost", "database": "db1", "username": "user", "password": "pass"}}
    mock_db_router.load_databases(db_configs)
    assert "db1" in mock_db_router._connections


def test_db_router_execute_query(mock_db_router):
    success, result = mock_db_router.execute_query("db1", "sp", "usp_Test", (1,))
    assert success is True
    assert result == [(1, "data")]


def test_db_router_close_connection(mock_db_router):
    mock_db_router.close_connection("db1")
    assert "db1" not in mock_db_router._connections
