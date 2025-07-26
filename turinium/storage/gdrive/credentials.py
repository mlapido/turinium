from dataclasses import dataclass
from typing import Optional
from turinium.storage.base_credentials import BaseStorageCredentials


@dataclass
class GDriveCredentials(BaseStorageCredentials):
    """
    Google Drive credentials.

    Attributes:
        credentials_json_path (str): Path to the OAuth credentials file.
        token_path (str): Path to token file.
        folder_id (Optional[str]): Folder ID to act as the working directory.
    """
    credentials_json_path: str
    token_path: str
    folder_id: Optional[str] = None

