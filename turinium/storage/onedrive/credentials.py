from dataclasses import dataclass
from typing import Optional
from turinium.storage.base_credentials import BaseStorageCredentials


@dataclass
class OneDriveCredentials(BaseStorageCredentials):
    """
    Microsoft OneDrive credentials.

    Attributes:
        client_id (str): OAuth client ID.
        client_secret (str): OAuth client secret.
        tenant_id (str): Azure tenant ID.
        refresh_token (str): Refresh token used to generate access tokens.
        drive_id (Optional[str]): ID of the target OneDrive drive.
        folder_path (Optional[str]): Path inside the drive to use as root.
    """
    client_id: str
    client_secret: str
    tenant_id: str
    refresh_token: str
    drive_id: Optional[str] = None
    folder_path: Optional[str] = None
