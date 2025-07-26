from dataclasses import dataclass
from typing import Optional
from turinium.storage.base_credentials import BaseStorageCredentials


@dataclass
class FTPCredentials(BaseStorageCredentials):
    """
    Extends StorageCredentials for FTP, FTPS, or SFTP protocols.

    Attributes:
        passive (bool): Passive mode for FTP/FTPS.
        private_key_path (Optional[str]): Path to SFTP private key.
        key_passphrase (Optional[str]): Optional passphrase for private key.
    """
    passive: bool = True
    private_key_path: Optional[str] = None
    key_passphrase: Optional[str] = None
