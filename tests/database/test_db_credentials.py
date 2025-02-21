import pytest
from turinium.database.db_credentials import DBCredentials


def test_db_credentials_sqlserver():
    creds = DBCredentials(
        name="test_db",
        db_type="sqlserver",
        server="localhost",
        database="testdb",
        username="user",
        password="pass",
        driver="ODBC Driver 17 for SQL Server"
    )
    url = creds.get_connection_url()
    assert "mssql+pyodbc" in url
    assert "driver=ODBC+Driver+17+for+SQL+Server" in url


def test_db_credentials_postgres():
    creds = DBCredentials(
        name="test_db",
        db_type="postgres",
        server="localhost",
        database="testdb",
        username="user",
        password="pass"
    )
    url = creds.get_connection_url()
    assert url.startswith("postgresql://")
