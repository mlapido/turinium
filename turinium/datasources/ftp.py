from turinium.datasources.base import BaseDataSource
from turinium.datasources.ftp_credentials import FTPCredentials
from turinium.datasources.ftp_connection import FTPConnection


class FTPDataSource(BaseDataSource):
    """
    FTP implementation of BaseDataSource.

    Uses the FTPConnection wrapper internally and applies base_dir from FTPCredentials automatically.
    """

    def __init__(self, credentials: FTPCredentials):
        """
        Initializes an FTPDataSource using a FTPCredentials object.

        :param credentials: FTPCredentials instance containing connection info.
        """
        self.credentials = credentials
        self._conn = FTPConnection(credentials)

    def connect(self) -> None:
        """Establishes the FTP/FTPS/SFTP connection."""
        self._conn.connect()

    def list_files(self, remote_dir: str) -> list[str]:
        """
        Lists all files in a directory on the remote FTP server.

        :param remote_dir: The remote path relative to base_dir (if defined).
        :return: A list of filenames.
        """
        return self._conn.list_files(remote_dir)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Downloads a file from the FTP server.

        :param remote_path: Remote file path relative to base_dir.
        :param local_path: Local file path to save to.
        """
        self._conn.download_file(remote_path, local_path)

    def move_file(self, src_path: str, dest_path: str) -> None:
        """
        Renames or moves a file on the remote server.

        :param src_path: Source path relative to base_dir.
        :param dest_path: Target path relative to base_dir.
        """
        self._conn.move_file(src_path, dest_path)

    def delete_file(self, remote_path: str) -> None:
        """
        Deletes a file on the remote server.

        :param remote_path: File path relative to base_dir.
        """
        self._conn.delete_file(remote_path)

    def is_alive(self) -> bool:
        """
        Tests whether the connection to the FTP server is still alive.

        :return: True if connection works, False otherwise.
        """
        return self._conn.is_alive()

    def close(self) -> None:
        """Closes the FTP connection."""
        self._conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()