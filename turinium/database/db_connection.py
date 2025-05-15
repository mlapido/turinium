import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Any, List, Tuple, Dict, Optional, Union
import time

from .db_credentials import DBCredentials
from turinium.logging import TLogging


class DBConnection:
    """
    Manages a connection to a PostgreSQL-compatible database using connection pooling.

    Supports execution of stored procedures and functions, including:
    - Scalar output via OUT parameters
    - Table results from functions
    - Optional type casting based on param_types
    - Logging and safe error handling
    """

    def __init__(self, credentials: DBCredentials):
        """
        Initialize a database connection.

        :param credentials: DBCredentials object with database configuration.
        """
        self.credentials = credentials
        self.engine: Engine = create_engine(
            self.credentials.get_connection_url(),
            pool_size=5,        # Keep 5 open connections for reuse
            max_overflow=10,    # Allow temporary up to 10 more connections
            pool_recycle=300,   # Close idle connections after 5 minutes
            pool_pre_ping=True  # Ensure connections are alive before using
        )
        self.logger = TLogging(f"DBConnection-{self.credentials.name}", log_filename="db_connection", log_to=("console", "file"))
        self.logger.info(f"Initialized connection pool for {self.credentials.name}")

    def execute(self, query_type: str,  query: str, params: Tuple[Any, ...] = (),
                param_types: Optional[Tuple[str, ...]] = None, ret_type: str = "default") -> Tuple[bool, Union[pd.DataFrame, Any]]:
        """
        Executes a stored procedure or function safely using parameterized queries.

        :param query_type: "sp" (stored procedure) or "fn" (function).
        :param query: The name of the stored procedure or function.
        :param params: Tuple of parameters to pass.
        :param param_types: PostgreSQL types for each parameter (e.g., ("integer", "text"))
        :param ret_type: "pandas" for DataFrame, "out" for scalar OUT param, or "default"
        :return: Tuple of (success, result)
        """
        start_time = time.time()
        try:
            with self.engine.connect() as connection:
                sql_query, param_dict = self._build_query(query_type, query, params, param_types, ret_type)

                self.logger.info(f"Executing {query_type.upper()}: {sql_query}")
                self.logger.debug(f"With parameters: {param_dict}")

                if ret_type == "pandas":
                    result = pd.read_sql(sql_query, connection, params=param_dict)
                    self._log_timing(query, start_time)
                    return True, result

                result = connection.execute(sql_query, param_dict)
                if result.returns_rows:
                    fetched = result.fetchall()
                    if ret_type == "out":
                        # Return first column of first row
                        self._log_timing(query, start_time)
                        return True, fetched[0][0] if fetched else None
                    self._log_timing(query, start_time)
                    return True, fetched

                self._log_timing(query, start_time)
                return True, None

        except Exception as e:
            self.logger.error(f"Error executing {query_type}: {query} -> {e}", exc_info=True)
            return False, None

    def _build_query(self, query_type: str, query: str, params: Tuple[Any, ...],
                     param_types: Optional[Tuple[str, ...]] = None, ret_type: str = "default") -> Tuple[Any, Dict[str, Any]]:
        """
        Constructs the SQL query and binds typed parameters.

        :param query_type: "sp" or "fn"
        :param query: Routine name (schema.routine_name)
        :param params: Parameters to bind
        :param param_types: Type hints for each parameter
        :param ret_type: Used to choose structure for return type
        :return: Tuple of (SQLAlchemy text query, parameter dict)
        """
        if param_types and len(param_types) != len(params):
            raise ValueError("param_types length does not match number of params.")

        # Build SQL placeholders with optional casting
        placeholders = ", ".join(f":param{i}" for i in range(len(params)))
        param_dict = self._cast_params(params, param_types) if param_types else {
            f"param{i}": v for i, v in enumerate(params)
        }

        if query_type == "sp":
            return text(f"CALL {query}({placeholders})"), param_dict
        elif query_type == "fn":
            return text(f"SELECT * FROM {query}({placeholders})"), param_dict
        else:
            raise ValueError(f"Invalid query type: {query_type}")

    @staticmethod
    def _cast_params(params: Tuple[Any, ...], param_types: Tuple[str, ...]) -> Dict[str, Any]:
        """
        Casts input values to appropriate Python types for PostgreSQL.

        :param params: Tuple of values
        :param param_types: PostgreSQL-compatible type strings
        :return: Dictionary of bound parameters with safe Python types
        """
        casted = {}
        for i, (value, pg_type) in enumerate(zip(params, param_types)):
            key = f"param{i}"
            if pg_type in ("integer", "int", "int4"):
                casted[key] = int(value)
            elif pg_type in ("text", "varchar", "character varying", "char", "character"):
                casted[key] = str(value)
            elif pg_type in ("numeric", "decimal", "float8", "double precision"):
                casted[key] = float(value)
            elif pg_type in ("boolean", "bool"):
                casted[key] = bool(value)
            else:
                casted[key] = value  # Pass through as-is
        return casted

    def _log_timing(self, query: str, start_time: float) -> None:
        """
        Logs how long the execution took.
        """
        duration = time.time() - start_time
        self.logger.info(f"Executed '{query}' in {duration:.3f} seconds")

    def close(self):
        """
        Closes the database engine and releases connection pool.
        """
        self.logger.info(f"Closing connection pool for {self.credentials.name}")
        self.engine.dispose()
        self.engine = None
