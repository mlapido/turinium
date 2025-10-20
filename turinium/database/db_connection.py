import time
import pandas as pd
from typing import Any, List, Tuple, Dict, Optional, Union

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .db_credentials import DBCredentials
from turinium.logging import TLogging


class DBConnection:
    """
    A unified database access layer for executing queries, stored routines, and batch operations.

    This class encapsulates the creation and management of a connection pool to a SQL Server or
    PostgreSQL database using SQLAlchemy. It supports multiple types of interactions including:

    - Executing stored procedures and functions.
    - Batch UPSERTs (insert/update on conflict).
    - Parameterized execution of raw SQL queries from `.sql` files.
    - Optional logging of execution time for performance tracking.

    It abstracts differences between PostgreSQL and SQL Server while enforcing safe parameter
    binding and offering a consistent interface for service-based query execution. It is intended
    to be used by higher-level service managers (e.g., DBServices) that define and register
    service configurations centrally.

    Conventions:
    - All SQL scripts used by this class should reside in a dedicated "sql" folder within your
      project or module structure.
    - File-based queries must be passed with the correct path relative to that folder.

    Logging and error handling are integrated using the TLogging class.
    """

    def __init__(self, credentials: DBCredentials, log_timing: bool = False):
        """
        Initialize a database connection and setup logging and connection pooling.

        :param credentials: Instance of DBCredentials containing database connection info.
        :param log_timing: Whether to log execution time for each query.
        """
        self._credentials = credentials
        self._log_timing_enabled = log_timing

        self._engine: Engine = create_engine(
            self._credentials.get_connection_url(),
            pool_size=5,        # Keep 5 open connections for reuse
            max_overflow=10,    # Allow temporary up to 10 more connections
            pool_recycle=300,   # Close idle connections after 5 minutes
            pool_pre_ping=True  # Ensure connections are alive before using
        )

        self._logger = TLogging(f"DBConnection-{self._credentials.name}",
                                log_filename="db_connection", log_to=("console", "file"))
        self._logger.info(f"Initialized connection pool for {self._credentials.name}")

    def execute(self, service_type: str, query: str, params: Union[Tuple[Any, ...], pd.DataFrame, List[List[Any]]] = (),
                param_types: Optional[Tuple[str, ...]] = None, ret_type: str = "default",
                service_config: Optional[Dict[str, Any]] = None) -> Tuple[bool, Union[pd.DataFrame, Any, None]]:
        """
        Executes a database service operation such as a stored procedure, function, upsert, or SQL query file.

        :param service_type: One of: 'sp', 'fn', 'upsert' or 'query'.
        :param query: Name of the routine or path identifier to a .sql file.
        :param params: Parameters for the execution (tuple for routines or data for upsert).
        :param param_types: PostgreSQL types used for casting.
        :param ret_type: How to interpret results. 'default'=scalar/rows. 'pandas'=DataFrame. 'out'=routine return value
        :param service_config: Additional service metadata (e.g., columns, file path, constraint).
        :return: (True, result) on success, or (False, error message or None).
        """
        if service_type in ("sp", "fn"):
            return self._execute_routine(service_type, query, params, param_types, ret_type)

        if service_type == "upsert":
            if not service_config:
                self._logger.error("Upsert requires service configuration.")
                return False, "Missing service_config for upsert."

            return self._execute_upsert(service_config["table"], service_config["constraint"],
                                        service_config["columns"], params)

        if service_type == "query":
            if not service_config or "query_file" not in service_config:
                self._logger.error("Missing query_file in service_config for query execution.")
                return False, None
            return self._execute_query(service_config["query_file"],
                                       params if isinstance(params, dict) else {})

        self._logger.error(f"Unsupported service_type: {service_type}")
        return False, f"Unsupported service_type: {service_type}"

    def _execute_routine(self, service_type: str, routine: str, params: Tuple[Any, ...] = (),
                         param_types: Optional[Tuple[str, ...]] = None,
                         ret_type: str = "default") -> Tuple[bool, Union[pd.DataFrame, Any, None]]:
        """
        Executes a stored procedure or function using safe parameter binding.

        Supports both SQL Server and PostgreSQL and returns either a scalar result,
        a full result set, or no result depending on the return mode.

        :param service_type: Either "sp" for stored procedure or "fn" for function.
        :param query: Fully qualified name of the routine (e.g., schema.proc_name).
        :param params: Parameters to bind in positional order.
        :param param_types:  Type hints for casting (mainly used in PostgreSQL - optional).
        :param ret_type: Either "out" for scalar value, "pandas" for DataFrame, or "default".

        :return: (success: bool, result or None)  - If success is True, result contains the return value.
                                                  - If False, result is None.
        """
        start_time = time.time()

        try:
            with self._engine.begin() as conn:
                sql, bindings = self._build_query(service_type, routine, params, param_types)

                if ret_type == "pandas":
                    result = pd.read_sql(sql, conn, params=bindings)
                else:
                    result_proxy = conn.execute(sql, bindings)
                    if result_proxy.returns_rows:
                        rows = result_proxy.fetchall()
                        result = rows[0][0] if ret_type == "out" and rows else rows
                    else:
                        result = None

            if self._log_timing_enabled:
                self._log_timing(routine, start_time)

            return True, result

        except Exception as e:
            self._handle_exception(e, service_type, routine)
            return False, None

    def _build_query(self, service_type: str, routine: str, params: Tuple[Any, ...],
                     param_types: Optional[Tuple[str, ...]] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Builds the appropriate SQLAlchemy query and param dictionary.

        :param service_type: One of 'sp' (stored procedure) or 'fn' (function).
        :param routine: Fully qualified name of the routine (e.g., 'schema.routine_name').
        :param params: Tuple of parameters to bind to the routine.
        :param param_types: Optional tuple of type hints for casting each parameter.
        :return: A tuple containing the SQLAlchemy text query and the parameter dictionary.
        """
        params = params or ()  # Ensure params is an empty tuple if None

        if param_types and len(param_types) != len(params):
            raise ValueError("param_types length does not match number of params.")

        db_type = self._credentials.db_type.lower()
        placeholders = ", ".join(f":param{i}" for i in range(len(params)))

        if param_types:
            param_dict = self._cast_params(params, param_types)
        else:
            param_dict = {f"param{i}": val for i, val in enumerate(params)}

        if db_type == "sqlserver":
            if service_type == "sp":
                query = f"EXEC {routine}" + (f" {placeholders}" if placeholders else "")
            else:
                query = f"SELECT {routine}({placeholders})"
        else:  # postgres or other
            if service_type == "sp":
                query = f"CALL {routine}({placeholders})"
            else:
                query = f"SELECT * FROM {routine}({placeholders})"

        return text(query), param_dict

    @staticmethod
    def _cast_params(params: Tuple[Any, ...], param_types: Tuple[str, ...]) -> Dict[str, Any]:
        """
        Safely casts input values based on provided PostgreSQL type hints.

        :param params: Tuple of values
        :param param_types: PostgreSQL-compatible types
        :return: Bound parameter dict
        """
        casted = {}
        for i, (value, type) in enumerate(zip(params, param_types)):
            key = f"param{i}"
            try:
                if type in ("integer", "int", "int4"):
                    casted[key] = int(value)
                elif type in ("text", "varchar", "char", "character"):
                    casted[key] = str(value)
                elif type in ("numeric", "decimal", "float8", "float"):
                    casted[key] = float(value)
                elif type in ("bool", "boolean"):
                    casted[key] = bool(value)
                else:
                    casted[key] = value
            except Exception:
                casted[key] = value
        return casted

    def _execute_query(self, query_file: str, params: Dict[str, Any]) -> Tuple[bool, Union[pd.DataFrame, None]]:
        """
        Executes a `.sql` file using provided named parameters.

        :param query_file: Path to the `.sql` file.
        :param params: Dictionary of named parameters to be safely bound to the query.
        :return: (success: bool, DataFrame or None) - (True, Query Result) if successful (False, None) otherwise.
        """
        try:
            with open(query_file, "r", encoding="utf-8") as f:
                sql = f.read()

            with self._engine.begin() as conn:
                result = pd.read_sql(text(sql), conn, params=params)

            return True, result

        except Exception as e:
            self._logger.error(f"Error executing SQL file {query_file}: {e}", exc_info=True)
            return False, None

    def _execute_upsert(self, table: str, constraint: List[str], columns: List[str],
                        data: Union[pd.DataFrame, List[List[Any]]]) -> Tuple[bool, Optional[str]]:
        """
        Dispatches to the correct upsert method based on DB type.

        :param table: Fully-qualified target table name (e.g., schema.table).
        :param constraint: List of column names forming the conflict constraint.
        :param columns: All columns to insert/update.
        :param data: (DataFrame or list of lists): Row data aligned with columns.
        """
        db_type = self._credentials.db_type.lower()

        if db_type == "postgresql":
            return self._execute_upsert_pg(table, constraint, columns, data)
        elif db_type in ("mssql", "sqlserver"):
            return self._execute_upsert_mssql(table, constraint, columns, data)
        else:
            raise NotImplementedError(f"Unsupported DB type for upsert: {db_type}")

    def _execute_upsert_pg(self, table: str, constraint: list, columns: Dict[str, str],
                           data: Union[pd.DataFrame, list[list[Any]]]) -> Tuple[bool, Optional[str]]:
        """
        PostgreSQL UPSERT using ON CONFLICT. Uses execute_values for bulk insertion when psycopg2 is available.

        :param table: Fully-qualified table name (schema.table).
        :param constraint: List of columns that form the conflict target.
        :param columns: Dict of column name to SQL type.
        :param data: Rows to insert (aligned with column order).
        :return: Tuple[success:bool, error:str or None]
        """
        try:
            if isinstance(data, pd.DataFrame):
                data = data[list(columns)].values.tolist()

            if not data:
                return True, None

            col_names = list(columns)
            assignments = ", ".join([f"{col}=EXCLUDED.{col}" for col in col_names if col not in constraint])
            insert_stmt = f"""
                INSERT INTO {table} ({", ".join(col_names)})
                VALUES %s
                ON CONFLICT ({', '.join(constraint)})
                DO UPDATE SET {assignments};
            """
            raw_conn = self._engine.raw_connection()

            try:
                from psycopg2.extras import execute_values

                cursor = raw_conn.cursor()
                execute_values(cursor, insert_stmt, data)
                raw_conn.commit()
            finally:
                raw_conn.close()

            return True, None

        except Exception as e:
            self._logger.error(f"PostgreSQL upsert failed: {e}", exc_info=True)
            return False, str(e)

    def _execute_upsert_mssql(self, table: str, constraint: list, columns: Dict[str, str],
                              data: Union[pd.DataFrame, list[list[Any]]]) -> Tuple[bool, Optional[str]]:
        """
        SQL Server UPSERT using temporary table and MERGE, with executemany for performance.

        :param table: Fully-qualified table name (schema.table).
        :param constraint: List of columns that form the conflict target.
        :param columns: Dict of column name to SQL type.
        :param data: Rows to insert (aligned with column order).
        :return: Tuple[success:bool, error:str or None]
        """
        try:
            if isinstance(data, pd.DataFrame):
                data = data[list(columns)].values.tolist()

            if not data:
                return True, None

            temp_table = f"#Temp_{table.split('.')[-1]}"
            col_names = list(columns)
            col_defs = ", ".join([f"{col} {columns[col]}" for col in col_names])
            updates = ", ".join([f"target.{col} = source.{col}" for col in col_names if col not in constraint])
            col_source = ", ".join([f"source.{col}" for col in col_names])
            col_list = ", ".join(col_names)

            with self._engine.raw_connection() as raw_conn:
                cursor = raw_conn.cursor()
                cursor.fast_executemany = True

                # 1. Create temp table
                cursor.execute(f"CREATE TABLE {temp_table} ({col_defs})")

                # 2. Insert data into temp table
                insert_stmt = f"INSERT INTO {temp_table} ({col_list}) VALUES ({', '.join(['?' for _ in col_names])})"
                cursor.executemany(insert_stmt, data)

                # 3. Merge
                merge_stmt = f"""
                MERGE INTO {table} AS target
                USING {temp_table} AS source
                ON {" AND ".join([f"target.{col} = source.{col}" for col in constraint])}
                WHEN MATCHED THEN UPDATE SET {updates}
                WHEN NOT MATCHED THEN INSERT ({col_list}) VALUES ({col_source});
                """
                cursor.execute(merge_stmt)

                cursor.close()
                raw_conn.commit()

            return True, None

        except Exception as e:
            self._logger.error(f"SQL Server upsert failed: {e}", exc_info=True)
            return False, str(e)

    def _handle_exception(self, exception: Exception, service_type: str, query: str) -> None:
        """
        Handles and logs DB-specific error messages for better debugging.

        This method conditionally imports database-specific exception classes to avoid
        requiring both psycopg2 and pyodbc as dependencies in all cases.

        :param exception: The raised exception.
        :param service_type: Type of routine being executed (e.g., 'sp', 'fn').
        :param query: The SQL query or routine being executed.
        """
        orig = getattr(exception, 'orig', None)
        args = orig.args if orig else ()

        try:
            from psycopg2.errors import ForeignKeyViolation
            if isinstance(orig, ForeignKeyViolation):
                msg = self._extract_pg_error_message(args)
                self._logger.error(f"Foreign key violation executing {service_type}: {query} -> {msg}", exc_info=False)
                return
        except ImportError:
            pass

        if isinstance(orig, IntegrityError):
            msg = self._extract_pg_error_message(args)
            self._logger.error(f"Integrity error executing {service_type}: {query} -> {msg}", exc_info=False)
            return

        try:
            from pyodbc import Error as ODBCError
            if isinstance(orig, ODBCError):
                msg = self._extract_mssql_error_message(args)
                self._logger.error(f"SQL Server error executing {service_type}: {query} -> {msg}", exc_info=False)
                return
        except ImportError:
            pass

        self._logger.error(f"Error executing {service_type}: {query} -> {exception}", exc_info=False)

    @staticmethod
    def _extract_pg_error_message(e_info: tuple) -> str:
        """
        Parses meaningful PostgreSQL error info from psycopg2.
        """
        if not e_info:
            return "Unknown PostgreSQL error"

        error_text = e_info[0]
        lines = error_text.splitlines()
        main_msg = lines[0]
        detail_msg = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("DETAIL:")), "")
        return f"{main_msg} : {detail_msg}" if detail_msg else main_msg

    @staticmethod
    def _extract_mssql_error_message(e_info: tuple) -> str:
        """
        Extracts useful error message from ODBC errors.
        """
        return e_info[1] if e_info and len(e_info) > 1 else str(e_info[0]) if e_info else "Unknown SQL Server error"

    def _log_timing(self, query: str, start_time: float) -> None:
        """
        Logs query duration for performance tracking.

        :param query: Query name or label
        :param start_time: Start time in seconds
        """
        duration = time.time() - start_time
        self._logger.info(f"Executed '{query}' in {duration:.3f} seconds")

    def close(self) -> None:
        """
        Closes the engine explicitly (not usually necessary with connection pooling).
        """
        self._logger.info(f"Closing connection pool for {self._credentials.name}")
        self._engine.dispose()
        self._engine = None
