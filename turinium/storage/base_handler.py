from abc import ABC, abstractmethod
from typing import List, Optional


class BaseStorageHandler(ABC):
    """
    Abstract base class for a storage handler.

    All specific storage types (FTP, Local, Google Drive, etc.) must inherit from this
    and implement the required methods to support listing, downloading, moving,
    deleting, and checking files.

    All paths used in these methods should be relative to the handler's configured base.
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Establishes a connection to the storage system if required.

        For storage types that don't require a persistent connection (e.g., local disk),
        this can be a no-op.
        """
        pass

    @abstractmethod
    def list(self, remote_dir: str, pattern: Optional[str] = None, pattern_type: str = "regex") -> List[str]:
        """
        Lists files in a given directory, optionally filtering by pattern.

        :param remote_dir: The directory to search (relative to base path).
        :param pattern: Optional pattern to filter file names.
        :param pattern_type: 'regex' or 'glob'. Default is 'regex'.
        :return: A list of matching file paths (relative to base path).
        """
        pass

    @abstractmethod
    def download(self, from_path: str, to_path: str) -> None:
        """
        Copies/Downloads a file from the storage system to a local path.

        :param from_path: Path to the file on the remote system.
        :param to_path: Full local path to save the downloaded file.
        """
        pass

    @abstractmethod
    def upload(self, from_path: str, to_path: str) -> None:
        """
        Uploads a file from the local path to the storage system.

        :param from_path: Full local path to the file.
        :param to_path: Target path on the remote storage.
        """
        pass

    @abstractmethod
    def move(self, from_path: str, to_path: str) -> None:
        """
        Moves or renames a file on the remote system.

        :param from_path: Original remote path.
        :param to_path: Target remote path.
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """
        Deletes a file from the remote system.

        :param path: Path to the file to delete.
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Checks whether a file or folder exists in the storage system.

        :param path: Relative path to check.
        :return: True if it exists, False otherwise.
        """
        pass

    @abstractmethod
    def make_dir(self, path: str) -> None:
        """
        Creates a folder if it doesn't exist.

        :param path: Directory path to ensure (relative).
        """
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """
        Checks if the connection or path to the storage system is active and responsive.

        :return: True if responsive or reachable, False otherwise.
        """
        pass

    def close(self) -> None:
        """
        Closes the connection to the storage system, if applicable.
        """
        pass

    def __enter__(self):
        """
        Enables context management using 'with' statements.
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures that the connection is properly closed when exiting the context.
        """
        self.close()
