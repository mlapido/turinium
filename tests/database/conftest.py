import pytest
from turinium import DBCredentials


@pytest.fixture
def pg_credentials():
    return DBCredentials(
        server="localhost",
        port=1444,
        database="testdb",
        username="postgres",
        password="secret",
        db_type="postgres"
    )


@pytest.fixture
def mssql_credentials():
    return DBCredentials(
        server="localhost",
        port=5433,
        database="testdb",
        username="sa",
        password="secret",
        db_type="mssql"
    )
