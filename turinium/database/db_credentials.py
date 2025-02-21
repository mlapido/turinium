from typing import Optional, Literal
from dataclasses import dataclass
from urllib.parse import quote_plus


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
        user = quote_plus(self.username)
        pwd = quote_plus(self.password)

        if self.db_type.lower() == "sqlserver":
            driver = quote_plus(self.driver) if self.driver else "ODBC Driver 17 for SQL Server"
            return f"mssql+pyodbc://{user}:{pwd}@{self.server}/{self.database}?driver={driver}"
        elif self.db_type.lower() == "postgres":
            return f"postgresql://{user}:{pwd}@{self.server}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")