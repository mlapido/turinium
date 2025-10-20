import pytest
from unittest.mock import patch, MagicMock

from turinium import DBServices


def setup_function():
    """Ensure each test starts with a clean DBServices state."""
    DBServices._connections.clear()
    DBServices._services.clear()


def teardown_function():
    """Ensure state is cleared after test (important in class-level storage)."""
    DBServices._connections.clear()
    DBServices._services.clear()


def test_register_databases_success():
    """
    Tests that register_databases correctly creates DBConnection instances
    and stores them in the _connections dict.
    """
    db_config = {
        "testdb": {
            "db_type": "postgresql",
            "host": "localhost",
            "username": "user",
            "password": "pass",
            "database": "mydb"
        }
    }

    with patch("turinium.database.db_services.DBCredentials") as mock_credentials_class, \
            patch("turinium.database.db_services.DBConnection") as mock_connection_class:
        # Mock return values for constructor calls
        mock_credentials = MagicMock()
        mock_credentials_class.return_value = mock_credentials

        mock_connection = MagicMock()
        mock_connection_class.return_value = mock_connection

        DBServices.register_databases(db_config)

        # Assert DBConnection was created
        mock_credentials_class.assert_called_once_with("testdb", **db_config["testdb"])
        mock_connection_class.assert_called_once_with(mock_credentials)

        assert "testdb" in DBServices._connections
        assert DBServices._connections["testdb"] == mock_connection


def test_auto_register_success():
    """
    Ensures that auto_register pulls from SharedAppConfig and calls register_databases and register_services.
    """
    with patch("turinium.database.db_services.SharedAppConfig") as mock_app_config_class, \
         patch.object(DBServices, "register_databases") as mock_register_dbs, \
         patch.object(DBServices, "register_services") as mock_register_svcs:

        mock_app_config = MagicMock()
        mock_app_config.get_config_block.side_effect = [
            {"mockdb": {"db_type": "postgresql"}},    # databases
            {"svc": {"type": "query", "query_file": "queries/q.sql", "db": "mockdb"}}  # services
        ]
        mock_app_config_class.is_initialized.return_value = True
        mock_app_config_class.return_value = mock_app_config

        DBServices.auto_register()

        mock_register_dbs.assert_called_once()
        mock_register_svcs.assert_called_once()


def test_register_services_all_types_success(tmp_path):
    """
    Tests registering services for all supported types: sp, fn, query, upsert.
    Ensures no exception is raised and _services is populated.
    """
    dummy_sql = tmp_path / "dummy_query.sql"
    dummy_sql.write_text("SELECT 1;")

    services = {
        "sp_service": {"type": "sp", "routine": "usp_Test", "ret_type": "default", "db": "mockdb"},
        "fn_service": {"type": "fn", "routine": "fn_Test", "ret_type": "default", "db": "mockdb"},
        "query_service": {"type": "query", "query_file": str(dummy_sql), "db": "mockdb"},
        "upsert_service": {
            "type": "upsert",
            "table": "schema.table",
            "columns": ["col1", "col2"],
            "constraint": ["col1"],
            "db": "mockdb"
        }
    }

    DBServices._connections["mockdb"] = MagicMock()

    DBServices.register_services(services)

    assert set(DBServices._services.keys()) == set(services.keys())

def test_register_services_missing_required_key():
    """
    Ensures ValueError is raised when a required key is missing from a service config.
    """
    incomplete_services = {
        "sp_service": {"type": "sp", "db": "mockdb"}  # Missing 'routine' and 'ret_type'
    }

    DBServices._connections["mockdb"] = MagicMock()

    with pytest.raises(ValueError, match="Invalid config for service: sp_service"):
        DBServices.register_services(incomplete_services)


def test_register_services_query_file_not_found():
    """
    Ensures FileNotFoundError is raised when the specified query file does not exist.
    """
    services = {
        "query_service": {
            "type": "query",
            "query_file": "non_existent.sql",
            "db": "mockdb"
        }
    }

    DBServices._connections["mockdb"] = MagicMock()

    with pytest.raises(FileNotFoundError, match="Missing SQL file for service: query_service"):
        DBServices.register_services(services)


def test_register_services_unknown_type():
    """
    Ensures ValueError is raised for unsupported service types.
    """
    services = {
        "bad_type": {
            "type": "bad",
            "routine": "dummy",
            "ret_type": "default",
            "db": "mockdb"
        }
    }

    DBServices._connections["mockdb"] = MagicMock()

    with pytest.raises(ValueError, match="Invalid service type: bad"):
        DBServices.register_services(services)


def test_register_services_unknown_db():
    """
    Ensures ValueError is raised when a service references a DB not in _connections.
    """
    services = {
        "some_service": {
            "type": "sp",
            "routine": "usp_Test",
            "ret_type": "default",
            "db": "not_registered"
        }
    }

    # Ensure _connections is empty to simulate unregistered DB
    DBServices._connections.clear()

    with pytest.raises(ValueError, match="Unknown DB for service: some_service"):
        DBServices.register_services(services)


def test_execute_calls_dbconnection():
    """
    Ensures that execute() routes a registered service correctly
    and delegates to DBConnection.execute with the expected parameters.
    """
    mock_db = MagicMock()
    DBServices._connections = {"main": mock_db}
    DBServices._services = {
        "my_service": {
            "database": "main",
            "type": "sp",
            "routine": "usp_MyRoutine",
            "ret_type": "default"
        }
    }

    # Prepare expected return
    mock_db.execute.return_value = (True, None)

    result = DBServices.execute("my_service", {"param": 42})

    mock_db.execute.assert_called_once()
    assert result == (True, None)


def test_execute_unknown_service():
    """
    Ensures that execute() raises ValueError for an unknown service name.
    """
    DBServices._services = {}
    DBServices._databases = {}

    with pytest.raises(ValueError, match="Service 'missing_service' is not registered."):
        DBServices.execute("missing_service", {})
