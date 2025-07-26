import os
import shutil
import time
import re
from typing import List, Optional
from fnmatch import fnmatch

from turinium.logging import TLogging
from turinium.storage.base_handler import BaseStorageHandler
from turinium.storage.local.credentials import LocalStorageCredentials


class LocalStorageHandler(BaseStorageHandler):
    """
    Local or NAS-based storage handler. Supports operations on local disk or mounted drives,
    with root and base path resolution and credential validation.

    Attributes:
        credentials (LocalStorageCredentials): Storage credentials including root and base dir.
        timeout (int): Timeout for retry attempts (not used in local, placeholder for consistency).
        retries (int): Retry attempts for transient failures (e.g. network mounts).
        logger (TLogging): Logger instance for operations.
    """

    def __init__(self, credentials: LocalStorageCredentials, timeout: int = 5, retries: int = 1):
        self.credentials = credentials
        self.timeout = timeout
        self.retries = retries
        self.logger = TLogging(
            f"LocalStorage-{credentials.name}",
            log_filename="local_storage",
            log_to=("console", "file")
        )
        self._base_path = os.path.abspath(
            os.path.join(credentials.root_path, credentials.base_dir or "")
        )

    def _full_path(self, relative_path: str) -> str:
        """
        Constructs the absolute path from base and a relative file or folder path.
        """
        return os.path.abspath(os.path.join(self._base_path, relative_path))

    def connect(self) -> None:
        """
        Verifies access to the root+base path. Acts as authentication check on mounted paths or NAS.
        Retries if the path is temporarily unavailable.
        """
        for attempt in range(1, self.retries + 1):
            try:
                self.logger.info(f"Checking access to {self._base_path} (attempt {attempt})...")
                if not os.path.exists(self._base_path):
                    raise FileNotFoundError(f"Path does not exist: {self._base_path}")
                test_file = os.path.join(self._base_path, ".connection_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                self.logger.info("Connection to local storage verified.")
                return
            except Exception as e:
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                time.sleep(self.timeout)
        raise ConnectionError(f"Failed to access local storage at {self._base_path}")

    def list(self, remote_dir: str, pattern: Optional[str] = None, pattern_type: str = "regex") -> List[str]:
        """
        Lists files in the given directory, filtered by pattern if provided.
        """
        path = self._full_path(remote_dir)
        self.logger.info(f"Listing files in {path}")
        try:
            files = os.listdir(path)
        except Exception as e:
            self.logger.error(f"Could not list directory: {e}")
            return []

        if pattern:
            if pattern_type == "glob":
                files = [f for f in files if fnmatch(f, pattern)]
            elif pattern_type == "regex":
                regex = re.compile(pattern, re.IGNORECASE)
                files = [f for f in files if regex.search(f)]
            else:
                self.logger.warning(f"Unknown pattern_type '{pattern_type}', skipping filter.")

        return files

    def download(self, remote_path: str, local_path: str) -> None:
        """
        Copies a file from local base path to another local path.
        """
        src = self._full_path(remote_path)
        dest = os.path.abspath(local_path)
        self.logger.info(f"Copying {src} to {dest}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)

    def upload(self, from_path: str, to_path: str) -> None:
        """
        Uploads a file by copying it from one local path to the handler’s base path.

        :param from_path: Source path on local disk.
        :param to_path: Destination path relative to storage base.
        """
        dest = self._full_path(to_path)
        self.logger.info(f"Uploading {from_path} to {dest}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(from_path, dest)

    def move(self, from_path: str, to_path: str) -> None:
        """
        Moves or renames a file inside the local base path.
        """
        src = self._full_path(from_path)
        dest = self._full_path(to_path)
        self.logger.info(f"Moving {src} to {dest}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)

    def delete(self, path: str) -> None:
        """
        Deletes a file in the local base path.
        """
        full_path = self._full_path(path)
        self.logger.info(f"Deleting {full_path}")
        if os.path.exists(full_path):
            os.remove(full_path)

    def make_dir(self, path: str) -> None:
        """
        Ensures that a given folder exists inside the local base.
        """
        full_path = self._full_path(path)
        self.logger.info(f"Ensuring directory exists: {full_path}")
        os.makedirs(full_path, exist_ok=True)

    def exists(self, path: str) -> bool:
        """
        Checks if a file or directory exists in the base path.
        """
        full_path = self._full_path(path)
        return os.path.exists(full_path)

    def is_alive(self) -> bool:
        """
        Checks if the base path is accessible and writable.
        """
        try:
            test_file = os.path.join(self._base_path, ".alive_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception as e:
            self.logger.warning(f"is_alive check failed: {e}")
            return False

    def close(self) -> None:
        """
        Closes the handler. No-op for local systems.
        """
        self.logger.info("Closing LocalStorageHandler.")
