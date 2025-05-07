from typing import Optional, Literal
from dataclasses import dataclass
from sqlalchemy.engine.url import URL

@dataclass
class DBCredentials:
    """
    Holds database connection credentials.
    """

    name: str
    db_type: Literal["sqlserver", "postgres"]
    server: str
    database: str
    username: str
    password: str
    driver: Optional[str] = None  # Only required for SQL Server

    def get_connection_url(self) -> str:
        """
        Generate a secure connection URL for SQLAlchemy.

        :return: Database connection string.
        """
        if self.db_type.lower() == "sqlserver":
            driver = self.driver if self.driver else "ODBC Driver 17 for SQL Server"
            return URL.create(
                drivername="mssql+pyodbc",
                username=self.username,
                password=self.password,
                host=self.server,
                database=self.database,
                query={"driver": driver}
            )
        elif self.db_type.lower() == "postgres":
            return URL.create(
                drivername="postgresql",
                username=self.username,
                password=self.password,
                host=self.server,
                database=self.database
            )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")