import os
import time
import socket
import paramiko
from ftplib import FTP, FTP_TLS, error_perm
from typing import List, Optional
from turinium.logging import TLogging
from turinium.ftp.ftpcore import FTPCredentials


class FTPConnection:
    """
    Manages a unified interface for FTP, FTPS, or SFTP operations using a single FTPCredentials object.
    Automatically applies base_dir to all remote paths and supports logging, retries, timeouts, and connection testing.

    Attributes:
        credentials (FTPCredentials): The credentials and connection configuration to use.
        timeout (int): Timeout in seconds for the connection attempt.
        retries (int): Number of connection attempts before failing.
        logger (TLogging): Logger instance scoped to the named FTP server.
    """

    def __init__(self, credentials: FTPCredentials, timeout: int = 30, retries: int = 3):
        """
        Initializes the connection handler with the given credentials and optional timeout/retry settings.

        :param credentials: A FTPCredentials instance with connection parameters.
        :param timeout: Timeout in seconds for the connection attempts (default: 30).
        :param retries: Number of retry attempts if connection fails (default: 3).
        """
        self.credentials = credentials
        self.timeout = timeout
        self.retries = retries
        self._client = None
        self._sftp = None
        self.logger = TLogging(
            f"FTPConnection-{credentials.name}",
            log_filename="ftp_connection",
            log_to=("console", "file")
        )

    def _full_path(self, remote_path: str) -> str:
        """
        Prepends base_dir to a remote path, if defined.

        :param remote_path: The relative or absolute path requested.
        :return: The full remote path with base_dir applied if applicable.
        """
        if self.credentials.base_dir:
            return os.path.join(self.credentials.base_dir.rstrip('/'), remote_path.lstrip('/'))
        return remote_path

    def connect(self):
        """
        Opens the connection to the FTP, FTPS, or SFTP server based on the provided protocol.
        Automatically retries up to `self.retries` times on failure.
        """
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                self.logger.info(f"Connecting to {self.credentials.name} (attempt {attempt})...")
                if self.credentials.protocol == 'sftp':
                    self._connect_sftp()
                elif self.credentials.protocol == 'ftps':
                    self._connect_ftps()
                elif self.credentials.protocol == 'ftp':
                    self._connect_ftp()
                self.logger.info(f"Connected to {self.credentials.name}.")
                return
            except Exception as e:
                last_error = e
                self.logger.warning(f"Connection attempt {attempt} failed: {e}")
                time.sleep(1)
        raise ConnectionError(f"Failed to connect to {self.credentials.name} after {self.retries} attempts: {last_error}")

    def _connect_ftp(self):
        """
        Establishes a plain FTP connection using ftplib.
        """
        ftp = FTP(timeout=self.timeout)
        ftp.connect(self.credentials.host, self.credentials.port)
        ftp.login(self.credentials.username, self.credentials.password)
        ftp.set_pasv(self.credentials.passive)
        self._client = ftp

    def _connect_ftps(self):
        """
        Establishes an FTPS (FTP with explicit TLS) connection using ftplib.FTP_TLS.
        """
        ftps = FTP_TLS(timeout=self.timeout)
        ftps.connect(self.credentials.host, self.credentials.port)
        ftps.login(self.credentials.username, self.credentials.password)
        ftps.prot_p()  # Secure the data channel
        ftps.set_pasv(self.credentials.passive)
        self._client = ftps

    def _connect_sftp(self):
        """
        Establishes an SFTP connection using paramiko.
        Supports both password and private key authentication.
        """
        sock = socket.create_connection((self.credentials.host, self.credentials.port), timeout=self.timeout)
        transport = paramiko.Transport(sock)

        if self.credentials.private_key_path:
            key = paramiko.RSAKey.from_private_key_file(
                self.credentials.private_key_path,
                password=self.credentials.key_passphrase
            )
            transport.connect(username=self.credentials.username, pkey=key)
        else:
            transport.connect(username=self.credentials.username, password=self.credentials.password)

        self._client = transport
        self._sftp = paramiko.SFTPClient.from_transport(transport)

    def list_files(self, remote_dir: str) -> List[str]:
        """
        Lists files in the specified remote directory.

        :param remote_dir: Path to the remote directory.
        :return: A list of file names in the directory.
        """
        path = self._full_path(remote_dir)
        self.logger.info(f"Listing files in {path}")
        return self._sftp.listdir(path) if self._sftp else self._client.nlst(path)

    def download_file(self, remote_path: str, local_path: str):
        """
        Downloads a file from the remote server to a local path.

        :param remote_path: Full path of the remote file.
        :param local_path: Full path to the local destination file.
        """
        rpath = self._full_path(remote_path)
        self.logger.info(f"Downloading {rpath} to {local_path}")
        if self._sftp:
            self._sftp.get(rpath, local_path)
        else:
            with open(local_path, 'wb') as f:
                self._client.retrbinary(f"RETR {rpath}", f.write)

    def move_file(self, src_path: str, dest_path: str):
        """
        Renames or moves a file on the remote server.

        :param src_path: Source path of the file.
        :param dest_path: Destination path.
        """
        src = self._full_path(src_path)
        dest = self._full_path(dest_path)
        self.logger.info(f"Moving {src} → {dest}")
        if self._sftp:
            self._sftp.rename(src, dest)
        else:
            self._client.rename(src, dest)

    def delete_file(self, remote_path: str):
        """
        Deletes a file on the remote server.

        :param remote_path: Full path to the remote file to delete.
        """
        rpath = self._full_path(remote_path)
        self.logger.info(f"Deleting {rpath}")
        if self._sftp:
            self._sftp.remove(rpath)
        else:
            self._client.delete(rpath)

    def is_alive(self) -> bool:
        """
        Checks if the connection is alive by trying to list the base_dir or root.
        :return: True if connection is responsive, False otherwise.
        """
        try:
            check_path = self.credentials.base_dir or '/'
            if self._sftp:
                self._sftp.listdir(check_path)
            else:
                self._client.nlst(check_path)
            return True
        except Exception as e:
            self.logger.warning(f"Connection check failed: {e}")
            return False

    def close(self):
        """
        Closes the connection cleanly.
        """
        self.logger.info(f"Closing connection to {self.credentials.name}...")
        try:
            if self._sftp:
                self._sftp.close()
            if self._client:
                quit_or_close = getattr(self._client, "quit", self._client.close)
                quit_or_close()
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")

    def __enter__(self):
        """
        Enters context manager, automatically connecting to the server.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exits context manager, closing the connection.
        """
        self.close()
