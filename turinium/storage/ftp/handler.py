import re
import os
import time
import socket
import paramiko
import posixpath

from ftplib import FTP, FTP_TLS, error_perm
from typing import List, Optional
from turinium.logging import TLogging

from fnmatch import fnmatch

from turinium.storage.base_handler import BaseStorageHandler
from turinium.storage.ftp.credentials import FTPCredentials


class FTPHandler(BaseStorageHandler):
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
        Prepends base_dir to a remote path, if not already present.

        :param remote_path: The relative or absolute path requested.
        :return: The full remote path with base_dir applied if applicable.
        """
        remote_path = remote_path.replace("\\", "/")
        base_dir = self.credentials.base_dir.replace("\\", "/") if self.credentials.base_dir else ""

        if base_dir:
            if not remote_path.startswith(base_dir):
                remote_path = posixpath.join(base_dir, remote_path.lstrip("/"))

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

    def list(self, path: str, pattern: Optional[str] = None, pattern_type: str = "regex") -> List[str]:
        """
        Lists files in the specified remote directory, optionally filtering by pattern.

        :param path: Path to the remote directory.
        :param pattern: Optional glob or regex pattern to match.
        :param pattern_type: 'Regex' (default) or 'glob'.
        :return: A list of matching file names in the directory.
        """
        full_path = self._full_path(path)
        self.logger.info(f"Listing files in {full_path}")
        files = self._sftp.listdir(path) if self._sftp else self._client.nlst(full_path)

        if pattern:
            if pattern_type == "glob":
                files = [f for f in files if fnmatch(f, pattern)]
            elif pattern_type == "regex":
                compiled = re.compile(pattern, re.IGNORECASE)
                files = [f for f in files if compiled.search(os.path.basename(f))]
            else:
                self.logger.warning(f"Unknown pattern_type '{pattern_type}', skipping filter.")

        return files

    def download(self, from_path: str, to_path: str):
        """
        Downloads a file from the remote server to a local path.

        :param from_path: Full path of the remote file.
        :param to_path: Full path to the local destination file.
        """
        path = self._full_path(from_path)
        self.logger.info(f"Downloading {path} to {to_path}")

        # Normalize slashes
        to_path = to_path.replace("\\", "/")

        # Ensure the directory exists
        os.makedirs(os.path.dirname(to_path), exist_ok=True)

        if self._sftp:
            self._sftp.get(path, to_path)
        else:
            with open(to_path, 'wb') as f:
                self._client.retrbinary(f"RETR {path}", f.write)

    def upload(self, from_path: str,to_path: str) -> None:
        """
        Uploads a local file to the FTP/SFTP server.

        :param from_path: Path to the local file.
        :param to_path: Target path on the remote system.
        """
        path = self._full_path(to_path)
        self.logger.info(f"Uploading {from_path} to {path}")

        if self._sftp:
            self._sftp.put(from_path, path)
        else:
            with open(from_path, 'rb') as f:
                self._client.storbinary(f"STOR {path}", f)

    def move(self, from_path: str, to_path: str):
        """
        Renames or moves a file on the remote server.

        :param from_path: Source path of the file.
        :param to_path: Destination path.
        """
        src = self._full_path(from_path)
        dest = self._full_path(to_path)
        self.logger.info(f"Moving '{src}' -> '{dest}'")
        if self._sftp:
            self._sftp.rename(src, dest)
        else:
            self._client.rename(src, dest)

    def delete(self, path: str):
        """
        Deletes a file on the remote server.

        :param path: Full path to the remote file to delete.
        """
        full_path = self._full_path(path)
        self.logger.info(f"Deleting {full_path}")
        if self._sftp:
            self._sftp.remove(full_path)
        else:
            self._client.delete(full_path)

    def make_dir(self, path: str) -> None:
        """
        Ensures that the given remote directory path exists by creating any missing folders.
        Restores the original working directory after the operation.

        :param path: Remote path that may include a filename — only folders will be created.
        """
        # Normalize slashes and remove filename
        full_path = self._full_path(path).replace("\\", "/")
        dir_path = posixpath.dirname(full_path) if not full_path.endswith("/") else full_path
        parts = dir_path.strip("/").split("/")

        # Capture original working directory
        try:
            original_dir = self._sftp.getcwd() if self._sftp else self._client.pwd()
        except Exception as e:
            self.logger.warning(f"Could not determine current working directory: {e}")
            original_dir = None

        try:
            for part in parts:
                try:
                    if self._sftp:
                        self._sftp.chdir(part)
                    else:
                        self._client.cwd(part)
                except Exception:
                    try:
                        if self._sftp:
                            self._sftp.mkdir(part)
                            self._sftp.chdir(part)
                        else:
                            self._client.mkd(part)
                            self._client.cwd(part)
                    except Exception as e:
                        self.logger.warning(f"Failed to create or enter directory '{part}': {e}")
                        raise
        finally:
            # Change back to original working directory
            try:
                if original_dir:
                    if self._sftp:
                        self._sftp.chdir(original_dir)
                    else:
                        self._client.cwd(original_dir)
            except Exception as e:
                self.logger.warning(f"Could not restore working directory to '{original_dir}': {e}")

    def exists(self, path: str) -> bool:
        """
        Checks whether a file or folder exists at the given remote path.

        :param path: Full remote path to check.
        :return: True if it exists, False otherwise.
        """
        full_path = self._full_path(path)
        try:
            if self._sftp:
                self._sftp.stat(full_path)
            else:
                self._client.size(full_path)  # Will raise error if file doesn't exist
            return True
        except Exception:
            return False

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
