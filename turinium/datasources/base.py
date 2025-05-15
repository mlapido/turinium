from abc import ABC, abstractmethod
from typing import List, Optional


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
    def list_files(self, remote_dir: str, pattern: Optional[str] = None, pattern_type: str = "regex") -> List[str]:
        """
        Lists files in the given remote directory, optionally filtered by a pattern.

        :param remote_dir: Directory to list.
        :param pattern: Pattern to filter file names.
        :param pattern_type: Either 'regex' or 'glob'. Default is 'regex'.
        :return: Filtered list of file names.
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

    def ensure_dir(self, remote_path: str) -> None:
        """
        Ensures the specified directory exists on the remote system.

        :param remote_path: Remote directory path to ensure.
        """
        # Optional override
        pass

    def exists(self, remote_path: str) -> bool:
        """
        Checks if the specified path exists on the remote system.

        :param remote_path: Path to check.
        :return: True if it exists, False otherwise.
        """
        return False

    def close(self) -> None:
        """Closes the connection, if applicable."""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()