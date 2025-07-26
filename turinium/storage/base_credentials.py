from dataclasses import dataclass
from typing import Optional


@dataclass
class BaseStorageCredentials:
    """
    Base class for credentials used to connect to any storage system.

    Attributes:
        name (str): Unique identifier for this storage config.
        protocol (str): Storage type or protocol (e.g., 'ftp', 'sftp', 'local', 's3', 'onedrive').
        host (Optional[str]): Hostname or address (if applicable).
        port (Optional[int]): Port for communication (if applicable).
        username (Optional[str]): Username for authentication (if applicable).
        password (Optional[str]): Password or token for authentication.
        base_dir (Optional[str]): Root path used as prefix for operations.
    """
    name: str
    protocol: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    base_dir: Optional[str] = None
