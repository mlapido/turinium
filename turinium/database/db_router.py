from typing import Optional
from .db_connection import DBConnection
from .db_credentials import DBCredentials
from turinium.logging import TLogging


class MissingDatabaseConnectionError(Exception):
    pass


class DBRouter:
    """
    Manages multiple database connections and routes queries.
    """

    _connections = {}
    _logger = TLogging("DBRouter", log_filename="db_router", log_to=("console", "file"))

    @classmethod
    def load_databases(cls, db_configs):
        """
        Load database configurations and create connections.

        :param db_configs: Dictionary of database configurations.
        """
        for name, config in db_configs.items():
            credentials = DBCredentials(name, **config)
            cls._connections[name] = DBConnection(credentials)

        cls._logger.info(f"Database connections initialized: {list(cls._connections.keys())}")

    @classmethod
    def get_connection(cls, db_name: str) -> Optional[DBConnection]:
        """
        Retrieves the DBConnection instance associated with the given database name.

        :param db_name: Name of the database whose connection is requested.
        :return: The DBConnection instance if it exists, or None if not found.
        """
        # Check if the requested database name exists in the router's connection pool
        if db_name in cls._connections:
            return cls._connections[db_name]

        # Optionally log a warning or raise a custom exception here
        return None

    @classmethod
    def has_connection(cls, db_name: str) -> bool:
        """
        Checks if a database connection exists.

        :param db_name: Name of the database.
        :return: True if the database connection exists, False otherwise.
        """
        return db_name in cls._connections

    @classmethod
    def execute_query(cls, db_name, query_type, query, params=(), params_types=(), ret_type="default"):
        """
        Execute a stored procedure or function on the specified database.

        :param db_name: The database to execute on.
        :param query_type: Type of query ("sp" for stored procedure, "fn" for function).
        :param query: The stored procedure or function name.
        :param params: Parameters to pass.
        :param params_types: Parameters to pass.
        :param ret_type: "pandas" for DataFrame, otherwise default.
        :return: (success, result)
        """
        if not cls.has_connection(db_name):
            cls._logger.error(f"Database '{db_name}' not registered.")
            return False, None

        connection = cls._connections[db_name]
        return connection.execute(query_type, query, params, params_types, ret_type)

    @classmethod
    def close_connection(cls, db_name):
        """
        Closes a specific database connection.

        :param db_name: Name of the database to close.
        """
        if cls.has_connection(db_name):
            try:
                cls._connections[db_name].close()
                del cls._connections[db_name]
                cls._logger.info(f"Closed connection to {db_name}.")
            except Exception as e:
                cls._logger.error(f"Error closing connection {db_name}: {e}", exc_info=True)
        else:
            cls._logger.warning(f"Tried to close a non-existent connection: {db_name}.")

    @classmethod
    def close_all(cls):
        """
        Close all database connections.
        """
        for db_name in list(cls._connections.keys()):
            cls.close_connection(db_name)

        cls._logger.info("All database connections closed.")
