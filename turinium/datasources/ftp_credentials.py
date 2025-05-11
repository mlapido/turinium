from dataclasses import dataclass
from typing import Optional


@dataclass
class FTPCredentials:
    """
    Represents connection credentials and settings for an FTP, FTPS, or SFTP server.

    These credentials are typically loaded from the 'ftp_servers' block in the application's config
    and registered via FTPServices.

    Attributes:
        name (str): Unique identifier for this server configuration.
        host (str): Hostname or IP address of the server.
        port (int): Port number (FTP/FTPS typically use 21, SFTP uses 22).
        username (str): Username for authentication.
        password (str): Password for authentication. Required for FTP/FTPS and also used for
            SFTP unless a private key is configured.
        protocol (str): Protocol to use: 'ftp', 'ftps', or 'sftp'.
        passive (bool): If True, use passive mode for FTP/FTPS. Ignored for SFTP.
        base_dir (Optional[str]): Optional base directory prepended to all paths for this server.

        private_key_path (Optional[str]): Path to the private key file used for SFTP key-based
            authentication. If set, this overrides the need for a password.
        key_passphrase (Optional[str]): Optional passphrase for decrypting the private key file.
    """
    name: str
    host: str
    port: int
    username: str
    password: Optional[str] = None
    protocol: str = 'ftp'  # 'ftp', 'ftps', or 'sftp'
    passive: bool = True
    base_dir: Optional[str] = None
    private_key_path: Optional[str] = None
    key_passphrase: Optional[str] = None
