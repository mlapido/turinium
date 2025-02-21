import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .db_credentials import DBCredentials
from turinium.logging import TLogging

class DBConnection:
    """
    Manages a connection to a database using connection pooling.
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

    def execute(self, query_type: str, query: str, params: tuple = (), ret_type="default"):
        """
        Executes a stored procedure or function safely using parameterized queries.

        :param query_type: "sp" (stored procedure) or "fn" (function).
        :param query: The name of the stored procedure or function.
        :param params: Parameters to pass (tuple).
        :param ret_type: "pandas" for DataFrame, otherwise default.
        :return: (success, result)
        """
        try:
            with self.engine.connect() as connection:
                sql_query, param_dict = self._build_query(query_type, query, params)  # Unpacking tuple
                self.logger.info(f"Executing {query_type.upper()}: {sql_query}")

                if ret_type == "pandas":
                    return True, pd.read_sql(sql_query, connection, params=param_dict)  # Use safe parameters
                else:
                    result = connection.execute(sql_query, param_dict)  # Pass params separately
                    if result.returns_rows:
                        return True, result.fetchall()
                    return True, None
        except Exception as e:
            self.logger.error(f"Error executing {query_type}: {query} -> {e}", exc_info=True)
            return False, None

    def _build_query(self, query_type: str, query: str, params: tuple) -> tuple:
        """
        Builds a SQL query using parameterized queries for security.

        :param query_type: "sp" (stored procedure) or "fn" (function).
        :param query: Stored procedure or function name.
        :param params: Tuple of parameters.
        :return: (SQLAlchemy text query, dictionary of parameters)
        """
        placeholders = ", ".join([f":param{i}" for i in range(len(params))])
        param_dict = {f"param{i}": v for i, v in enumerate(params)}  # Map placeholders to values

        if query_type == "sp":
            return text(f"EXEC {query} {placeholders}"), param_dict
        elif query_type == "fn":
            return text(f"SELECT * FROM {query}({placeholders})"), param_dict
        else:
            raise ValueError(f"Invalid query type: {query_type}")

    def close(self):
        """
        Closes the database connection.
        """
        self.logger.info(f"Closing connection pool for {self.credentials.name}")
        self.engine.dispose()
        self.engine = None