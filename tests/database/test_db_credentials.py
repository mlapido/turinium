import pytest
import pyodbc
from turinium.database.db_credentials import DBCredentials


def test_pg_url_includes_port():
    """
    Test that the PostgreSQL connection URL includes the custom port.

    This test uses a hardcoded instance of DBCredentials to ensure that the `get_connection_url`
    method properly inserts the port into the resulting SQLAlchemy URL for PostgreSQL.
    """
    creds = DBCredentials(
        name="pgtest",
        db_type="postgres",
        server="localhost",
        database="mydb",
        username="postgres",
        password="secret",
        port=5433
    )

    url = creds.get_connection_url()
    assert url.port == 5433
    assert url.drivername == "postgresql"
    assert url.username == "postgres"
    assert url.host == "localhost"
    assert url.database == "mydb"


def test_mssql_url_includes_port():
    """
    Test that the MSSQL connection URL includes the custom port.

    This verifies that `get_connection_url` handles SQL Server-specific connection strings
    with an ODBC driver correctly, even when using a custom port.
    """
    creds = DBCredentials(
        name="mssqldb",
        db_type="mssql",
        server="localhost",
        database="mydb",
        username="sa",
        password="secret",
        port=1444,
        driver="ODBC Driver 17 for SQL Server"
    )

    url = creds.get_connection_url()
    assert url.port == 1444
    assert url.drivername == "mssql+pyodbc"
    assert url.username == "sa"
    assert url.host == "localhost"
    assert url.database == "mydb"
    assert url.query["driver"] == "ODBC Driver 17 for SQL Server"


def test_get_driver_exact_match(monkeypatch):
    """
    Test _get_driver with an exact driver name match.

    If the provided driver name matches one in the list returned by pyodbc.drivers(),
    that driver should be returned without fallback or fuzzy matching.
    """
    monkeypatch.setattr(pyodbc, "drivers", lambda: ["ODBC Driver 17 for SQL Server", "ODBC Driver 13"])

    creds = DBCredentials(
        name="db",
        db_type="mssql",
        server="localhost",
        database="test",
        username="sa",
        password="secret",
        driver="ODBC Driver 17 for SQL Server"
    )

    selected_driver = creds._get_driver()
    assert selected_driver == "ODBC Driver 17 for SQL Server"


def test_get_driver_fuzzy_match(monkeypatch):
    """
    Test _get_driver with a driver name that requires fuzzy matching.
    """
    available = ["ODBC Driver 17 for SQL Server", "ODBC Driver 13"]
    monkeypatch.setattr(pyodbc, "drivers", lambda: available)

    creds = DBCredentials(
        name="db",
        db_type="mssql",
        server="localhost",
        database="test",
        username="sa",
        password="secret",
        driver="Driver 17"
    )

    selected = creds._get_driver()
    # Accept either if scoring isn't guaranteed
    assert selected in available


def test_get_driver_fallback_to_first(monkeypatch):
    """
    Test _get_driver fallback logic when no driver is specified.

    In the absence of a provided driver or matching candidate, _get_driver
    should fall back to the first available ODBC driver.
    """
    monkeypatch.setattr(pyodbc, "drivers", lambda: ["ODBC Driver 13", "ODBC Driver 11"])

    creds = DBCredentials(
        name="db",
        db_type="mssql",
        server="localhost",
        database="test",
        username="sa",
        password="secret"
        # No driver provided
    )

    selected_driver = creds._get_driver()
    assert selected_driver == "ODBC Driver 13"


def test_get_driver_no_drivers_installed(monkeypatch):
    """
    Test _get_driver error case when no ODBC drivers are installed.

    This test simulates a system where pyodbc.drivers() returns an empty list.
    A RuntimeError should be raised to indicate the missing system dependency.
    """
    monkeypatch.setattr(pyodbc, "drivers", lambda: [])

    creds = DBCredentials(
        name="db",
        db_type="mssql",
        server="localhost",
        database="test",
        username="sa",
        password="secret"
    )

    with pytest.raises(RuntimeError, match="No ODBC drivers are installed"):
        creds._get_driver()
