from abc import ABC, abstractmethod
from typing import List, Dict


class BaseDataSource(ABC):
    """
    Abstract base class for a file-based data source.
    Subclasses must implement connection, listing, download, and file management.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establishes the connection to the data source (if needed)."""
        pass

    @abstractmethod
    def list_files(self, remote_dir: str) -> List[str]:
        """
        Lists all files in a given directory.

        :param remote_dir: Path to directory on the remote system.
        :return: A list of filenames (no full paths).
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Downloads a remote file to a local path.

        :param remote_path: Full path to the remote file.
        :param local_path: Full path to the local destination file.
        """
        pass

    @abstractmethod
    def move_file(self, src_path: str, dest_path: str) -> None:
        """
        Moves or renames a file on the remote system.

        :param src_path: Source path on the remote system.
        :param dest_path: Target path on the remote system.
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> None:
        """
        Deletes a file from the remote system.

        :param remote_path: Full path to the file.
        """
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Checks if the connection to the source is alive.

        :return: True if responsive, False otherwise.
        """
        pass

    def close(self) -> None:
        """Closes the connection, if applicable."""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()