from dataclasses import dataclass
from turinium.storage.base_credentials import BaseStorageCredentials


@dataclass
class LocalStorageCredentials(BaseStorageCredentials):
    """
    Local or NAS-based file system credentials.

    Attributes:
        root_path (str): Absolute root path on local or network file system.
    """
    root_path: str = '/'
