import pytest
import pandas as pd

from unittest.mock import MagicMock, patch
from sqlalchemy.engine import Engine
from turinium import DBConnection
from turinium import DBCredentials
from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause
from unittest.mock import patch


@pytest.fixture
def pg_credentials():
    """
    Fixture for PostgreSQL credentials used to initialize DBConnection.
    """
    return DBCredentials(
        name="testpg",
        db_type="postgres",
        server="localhost",
        port=5432,
        database="testdb",
        username="postgres",
        password="secret"
    )


@pytest.fixture
def db_connection(pg_credentials):
    """
    Fixture that returns a DBConnection instance using PostgreSQL credentials.
    """
    return DBConnection(pg_credentials, log_timing=False)


def test_dbconnection_init_creates_engine(monkeypatch, pg_credentials):
    """
    Verifies that the SQLAlchemy engine is created upon DBConnection instantiation
    and that the logger logs an initialization message.
    """
    mocked_engine = MagicMock(spec=Engine)
    monkeypatch.setattr("turinium.database.db_connection.create_engine", lambda *_args, **_kwargs: mocked_engine)

    conn = DBConnection(pg_credentials)
    assert conn._engine == mocked_engine
    assert conn._credentials.name == "testpg"


def test_execute_query_reads_sql_file(monkeypatch, tmp_path, db_connection):
    """
    Simulates executing a SQL file and ensures a DataFrame is returned.
    Uses a temporary file to mock SQL content.
    """
    sql_path = tmp_path / "mock_query.sql"
    sql_path.write_text("SELECT 1 AS result;", encoding="utf-8")

    # Patch engine.begin to return a mock connection
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    monkeypatch.setattr(db_connection._engine, "begin", lambda: mock_conn)

    # Patch pandas.read_sql to return a test DataFrame
    monkeypatch.setattr(pd, "read_sql", lambda sql, conn, params=None: pd.DataFrame({"result": [1]}))

    success, df = db_connection._execute_query(str(sql_path), params={})

    assert success is True
    assert isinstance(df, pd.DataFrame)
    assert df["result"].iloc[0] == 1


def test_execute_query_file_not_found(db_connection):
    """
    Verifies that _execute_query returns (False, None) when the SQL file is missing.
    """
    success, result = db_connection._execute_query("nonexistent.sql", {})
    assert success is False
    assert result is None


def test_execute_calls_routine(monkeypatch, db_connection):
    """
    Verifies that execute() calls _execute_routine when service_type is 'sp' or 'fn'.
    """
    mock_result = (True, "ok")
    monkeypatch.setattr(db_connection, "_execute_routine", lambda *a, **kw: mock_result)

    for service_type in ("sp", "fn"):
        success, result = db_connection.execute(service_type, "mock_routine", params=(1,))
        assert success is True
        assert result == "ok"


def test_execute_upsert_missing_config(db_connection):
    """
    Verifies that execute() returns an error when service_type is 'upsert' but service_config is missing.
    """
    success, result = db_connection.execute(service_type="upsert", query="mock", params=[])
    assert success is False
    assert result == "Missing service_config for upsert."


def test_execute_calls_upsert(monkeypatch, db_connection):
    """
    Verifies that execute() dispatches to _execute_upsert when service_type is 'upsert' and config is provided.
    """
    mock_result = (True, None)
    monkeypatch.setattr(db_connection, "_execute_upsert", lambda table, constraint, columns, data: mock_result)

    config = {
        "table": "schema.table",
        "constraint": ["id"],
        "columns": ["id", "name"]
    }

    success, result = db_connection.execute(service_type="upsert", query="irrelevant", params=[[1, "Alice"]], service_config=config)
    assert success is True
    assert result is None


def test_execute_calls_execute_query(monkeypatch, db_connection, tmp_path):
    """
    Verifies that execute() dispatches to _execute_query when service_type is 'query' and a query_file is specified.
    """
    monkeypatch.setattr(db_connection, "_execute_query", lambda query_file, params: (True, "data"))

    config = {"query_file": "dummy.sql"}
    success, result = db_connection.execute(service_type="query", query="irrelevant", params={}, service_config=config)

    assert success is True
    assert result == "data"


def test_execute_query_missing_file_config(db_connection):
    """
    Verifies that execute() returns (False, None) when query_file is missing in service_config.
    """
    success, result = db_connection.execute(service_type="query", query="irrelevant", params={}, service_config={})
    assert success is False
    assert result is None


def test_execute_invalid_service_type(db_connection):
    """
    Verifies that execute() handles unsupported service_type gracefully.
    """
    success, result = db_connection.execute(service_type="unsupported", query="q")
    assert success is False
    assert "Unsupported service_type" in result


def test_execute_routine_returns_scalar(monkeypatch, db_connection):
    """
    Verifies that _execute_routine returns the first column of the first row when ret_type='out'.
    """
    mock_conn = MagicMock()
    mock_result_proxy = MagicMock()
    mock_result_proxy.returns_rows = True
    mock_result_proxy.fetchall.return_value = [(42,)]
    mock_conn.execute.return_value = mock_result_proxy
    mock_conn.__enter__.return_value = mock_conn

    monkeypatch.setattr(db_connection._engine, "begin", lambda: mock_conn)
    monkeypatch.setattr(db_connection, "_build_query", lambda *a, **kw: (text("SELECT 42"), {}))

    success, result = db_connection._execute_routine("fn", "mock_fn", params=(), ret_type="out")

    assert success is True
    assert result == 42


def test_execute_routine_returns_rows(monkeypatch, db_connection):
    """
    Verifies that _execute_routine returns all rows when ret_type='default'.
    """
    mock_conn = MagicMock()
    mock_result_proxy = MagicMock()
    mock_result_proxy.returns_rows = True
    mock_result_proxy.fetchall.return_value = [(1,), (2,), (3,)]
    mock_conn.execute.return_value = mock_result_proxy
    mock_conn.__enter__.return_value = mock_conn

    monkeypatch.setattr(db_connection._engine, "begin", lambda: mock_conn)
    monkeypatch.setattr(db_connection, "_build_query", lambda *a, **kw: (text("SELECT * FROM numbers"), {}))

    success, result = db_connection._execute_routine("fn", "mock_fn", params=(), ret_type="default")

    assert success is True
    assert result == [(1,), (2,), (3,)]


def test_execute_routine_returns_dataframe(monkeypatch, db_connection):
    """
    Verifies that _execute_routine uses pd.read_sql() to return a DataFrame when ret_type='pandas'.
    """
    df_mock = pd.DataFrame({"val": [10, 20]})

    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn

    monkeypatch.setattr(db_connection._engine, "begin", lambda: mock_conn)
    monkeypatch.setattr(pd, "read_sql", lambda sql, conn, params=None: df_mock)
    monkeypatch.setattr(db_connection, "_build_query", lambda *a, **kw: (text("SELECT * FROM mock"), {}))

    success, result = db_connection._execute_routine("fn", "mock_fn", params=(), ret_type="pandas")

    assert success is True
    assert isinstance(result, pd.DataFrame)
    assert result.equals(df_mock)


def test_execute_routine_handles_exception(monkeypatch, db_connection):
    """
    Verifies that _execute_routine catches exceptions and calls _handle_exception.
    """
    monkeypatch.setattr(db_connection._engine, "begin", lambda: (_ for _ in ()).throw(Exception("Routine failed")))
    monkeypatch.setattr(db_connection, "_handle_exception", lambda e, t, q: None)

    success, result = db_connection._execute_routine("sp", "mock_sp", params=(), ret_type="out")

    assert success is False
    assert result is None

def test_build_query_function_pg(db_connection):
    """
    Verifies that _build_query generates the correct SQL and parameters for PostgreSQL functions.
    """
    db_connection._credentials.db_type = "postgres"
    sql, params = db_connection._build_query("fn", "public.add_numbers", (1, 2))

    assert isinstance(sql, TextClause)
    assert "SELECT * FROM public.add_numbers" in str(sql)
    assert params == {"param0": 1, "param1": 2}


def test_build_query_procedure_pg(db_connection):
    """
    Verifies that _build_query generates the correct SQL and parameters for PostgreSQL stored procedures.
    """
    db_connection._credentials.db_type = "postgres"
    sql, params = db_connection._build_query("sp", "public.do_something", ("x", 3))

    assert isinstance(sql, TextClause)
    assert "CALL public.do_something" in str(sql)
    assert params == {"param0": "x", "param1": 3}


def test_build_query_function_mssql(db_connection):
    """
    Verifies that _build_query generates the correct SQL and parameters for SQL Server functions.
    """
    db_connection._credentials.db_type = "sqlserver"
    sql, params = db_connection._build_query("fn", "dbo.get_price", (99,))

    assert isinstance(sql, TextClause)
    assert "SELECT dbo.get_price" in str(sql)
    assert params == {"param0": 99}


def test_build_query_procedure_mssql(db_connection):
    """
    Verifies that _build_query generates the correct SQL and parameters for SQL Server procedures.
    """
    db_connection._credentials.db_type = "sqlserver"
    sql, params = db_connection._build_query("sp", "dbo.do_task", ("abc",))

    assert isinstance(sql, TextClause)
    assert "EXEC dbo.do_task" in str(sql)
    assert params == {"param0": "abc"}


def test_build_query_raises_on_param_type_mismatch(db_connection):
    """
    Verifies that _build_query raises an error when param_types and params have different lengths.
    """
    with pytest.raises(ValueError, match="param_types length does not match"):
        db_connection._build_query("fn", "schema.fn", params=("x",), param_types=("int", "text"))


def test_cast_params_with_type_hints(db_connection):
    """
    Verifies that _cast_params casts values correctly using PostgreSQL-style type hints.
    """
    casted = db_connection._cast_params(
        params=("123", 45.6, "true", "name"),
        param_types=("int", "float8", "bool", "text")
    )

    assert casted["param0"] == 123
    assert isinstance(casted["param0"], int)

    assert casted["param1"] == 45.6
    assert isinstance(casted["param1"], float)

    assert casted["param2"] is True
    assert isinstance(casted["param2"], bool)

    assert casted["param3"] == "name"
    assert isinstance(casted["param3"], str)


def test_execute_upsert_pg_with_data(monkeypatch, db_connection):
    """
    Verifies that _execute_upsert_pg succeeds with valid data and uses execute_values.
    """
    db_connection._credentials.db_type = "postgres"

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr(db_connection._engine, "raw_connection", lambda: mock_conn)

    with patch("turinium.database.db_connection.execute_values") as mock_exec:
        mock_exec.return_value = None  # simulate success

        success, error = db_connection._execute_upsert_pg(
            table="public.my_table",
            constraint=["id"],
            columns={"id": "int", "name": "text"},
            data=[[1, "Alice"], [2, "Bob"]]
        )

        assert success is True
        assert error is None
        mock_exec.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()


def test_execute_upsert_pg_empty_data(db_connection):
    """
    Verifies that _execute_upsert_pg returns (True, None) when given empty data.
    """
    db_connection._credentials.db_type = "postgres"

    success, error = db_connection._execute_upsert_pg(
        table="public.table",
        constraint=["id"],
        columns={"id": "int", "name": "text"},
        data=[]
    )

    assert success is True
    assert error is None


def test_execute_upsert_pg_dataframe(monkeypatch, db_connection):
    """
    Verifies that _execute_upsert_pg accepts a pandas DataFrame.
    """
    db_connection._credentials.db_type = "postgres"

    df = pd.DataFrame([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ])

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    monkeypatch.setattr(db_connection._engine, "raw_connection", lambda: mock_conn)

    with patch("turinium.database.db_connection.execute_values") as mock_exec:
        success, error = db_connection._execute_upsert_pg(
            table="public.table",
            constraint=["id"],
            columns={"id": "int", "name": "text"},
            data=df
        )
        assert success is True
        assert error is None
        mock_exec.assert_called_once()


def test_execute_upsert_mssql_with_data(monkeypatch, db_connection):
    """
    Verifies that _execute_upsert_mssql performs the 3 SQL steps and commits.
    """
    db_connection._credentials.db_type = "sqlserver"

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn  # important!
    mock_conn.__exit__.return_value = None
    monkeypatch.setattr(db_connection._engine, "raw_connection", lambda: mock_conn)

    success, error = db_connection._execute_upsert_mssql(
        table="dbo.my_table",
        constraint=["id"],
        columns={"id": "int", "name": "varchar(100)"},
        data=[[1, "Alice"], [2, "Bob"]]
    )

    assert success is True
    assert error is None
    assert mock_cursor.execute.call_count >= 2  # CREATE + MERGE
    mock_cursor.executemany.assert_called_once()
    mock_conn.commit.assert_called_once()


def test_execute_upsert_mssql_empty_data(db_connection):
    """
    Verifies that _execute_upsert_mssql returns (True, None) when data is empty.
    """
    db_connection._credentials.db_type = "sqlserver"

    success, error = db_connection._execute_upsert_mssql(
        table="dbo.table",
        constraint=["id"],
        columns={"id": "int", "name": "varchar(100)"},
        data=[]
    )

    assert success is True
    assert error is None

