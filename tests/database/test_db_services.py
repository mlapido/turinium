import pytest
from unittest.mock import MagicMock, patch
from turinium.database.db_router import DBRouter
from turinium.database.db_services import DBServices


@pytest.fixture
def mock_db_services():
    with patch("turinium.database.db_router.DBRouter.load_databases") as mock_load_databases, \
            patch("turinium.database.db_router.DBRouter.execute_query") as mock_execute:
        db_services = DBServices()
        mock_load_databases.return_value = None  # Ensure it doesn’t break
        DBRouter._connections["db1"] = MagicMock()  # Register db1 in DBRouter

        # Ensure it returns a valid tuple
        mock_execute.return_value = (True, [(1, "result")])

        return db_services


def test_db_services_register_services(mock_db_services):
    services = {
        "get_users": {"db": "db1", "type": "sp", "sp": ["usp_GetUsers"], "ret_type": "pandas"}
    }
    mock_db_services.register_services(services)
    assert "get_users" in mock_db_services._services


def test_db_services_exec_service(mock_db_services):
    # Ensure db1 is registered before execution
    DBRouter._connections["db1"] = MagicMock()

    with patch("turinium.database.db_router.DBRouter.execute_query", return_value=(True, [(1, "result")])):
        success, result = mock_db_services.exec_service("get_users", (1,))

    assert success is True
    assert result == [(1, "result")]
