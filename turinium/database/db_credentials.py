from typing import Optional, Literal
from dataclasses import dataclass
from sqlalchemy.engine.url import URL


@dataclass
class DBCredentials:
    """
    Holds all the necessary credentials for connecting to a database using SQLAlchemy.

    Attributes:
        name (str): A short alias or identifier for the database.
        db_type (Literal["mssql","sqlserver", "postgres"]): Type of the database engine.
        server (str): Server address (IP or hostname).
        database (str): Target database name.
        username (str): Username used for authentication.
        password (str): Password used for authentication.
        port (int): Optional port (defaults based on server type if omitted).
        driver (Optional[str]): ODBC driver to use (only required for SQL Server).
    """

    name: str
    db_type: Literal["mssql", "sqlserver", "postgres"]
    server: str
    database: str
    username: str
    password: str
    port: Optional[int] = None
    driver: Optional[str] = None  # Only required for SQL Server

    def get_connection_url(self) -> URL:
        """
        Constructs a SQLAlchemy-compatible URL based on the credentials and database type.

        :returns: A SQLAlchemy URL instance that can be passed to create_engine().
        :raises ValueError: If the db_type is not supported.
        """
        db_type_normalized = self.db_type.lower()

        if db_type_normalized in ("mssql", "sqlserver"):
            port = self.port or 1433  # Correct default port for MSSQL
            return URL.create(
                drivername="mssql+pyodbc",
                username=self.username,
                password=self.password,
                host=self.server,
                port=port,
                database=self.database,
                query={"driver": self._get_driver()}
            )

        elif db_type_normalized == "postgres":
            port = self.port or 5432  # Correct default for PostgreSQL
            return URL.create(
                drivername="postgresql",
                username=self.username,
                password=self.password,
                host=self.server,
                port=self.port,
                database=self.database
            )

        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def _get_driver(self) -> str:
        """
        Selects the appropriate ODBC driver for SQL Server connections.

        If a driver name is provided, attempts to match it to the closest available one.
        If no match is found, or no driver is provided, defaults to the first available.

        :return: The most appropriate ODBC driver string.
        :raises RuntimeError: If no ODBC drivers are installed.
        """
        import pyodbc
        import difflib

        available_drivers = pyodbc.drivers()
        if not available_drivers:
            raise RuntimeError("No ODBC drivers are installed on this system.")

        if self.driver:
            closest = difflib.get_close_matches(self.driver, available_drivers, n=1, cutoff=0.3)
            if closest:
                return closest[0]

        return available_drivers[0]
