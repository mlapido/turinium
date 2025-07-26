import os
import io
import re
import time
from typing import List, Optional
from fnmatch import fnmatch

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload

from turinium.logging import TLogging
from turinium.storage.base_handler import BaseStorageHandler
from turinium.storage.gdrive.credentials import GDriveCredentials


class GDriveHandler(BaseStorageHandler):
    """
    Google Drive storage handler using a service account.

    Supports listing and downloading files from a specified folder ID
    (can be from My Drive or a Shared Drive).

    Attributes:
        credentials (GDriveCredentials): GDrive config and OAuth paths.
        logger (TLogging): Logger for operational messages.
        retries (int): Retry attempts on connection failure.
    """

    def __init__(self, credentials: GDriveCredentials, retries: int = 3):
        self.credentials = credentials
        self.logger = TLogging(
            f"GDrive-{credentials.name}",
            log_filename="gdrive_storage",
            log_to=("console", "file")
        )
        self.retries = retries
        self._service = None

    def connect(self) -> None:
        """
        Establishes connection using service account credentials.
        Retries up to `retries` times if authentication fails.
        """
        last_error = None
        for attempt in range(1, self.retries + 1):
            try:
                self.logger.info(f"Connecting to Google Drive ({self.credentials.name}) (attempt {attempt})...")
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials.credentials_json_path,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                self._service = build('drive', 'v3', credentials=creds)
                self.logger.info("Connected to Google Drive.")
                return
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                time.sleep(1)
        raise ConnectionError(f"Failed to connect to Google Drive: {last_error}")

    def list(self, remote_dir: str = "", pattern: Optional[str] = None, pattern_type: str = "regex") -> List[str]:
        """
        Lists files in the specified Google Drive folder.

        :param remote_dir: Ignored; `folder_id` from credentials is used.
        :param pattern: Optional name filter.
        :param pattern_type: 'glob' or 'regex'.
        :return: List of file names.
        """
        if not self.credentials.folder_id:
            self.logger.warning("No folder_id specified in credentials. Cannot list files.")
            return []

        try:
            results = self._service.files().list(
                q=f"'{self.credentials.folder_id}' in parents and trashed = false",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name)"
            ).execute()
            files = results.get('files', [])
            names = [f['name'] for f in files]

            if pattern:
                if pattern_type == "glob":
                    names = [n for n in names if fnmatch(n, pattern)]
                elif pattern_type == "regex":
                    regex = re.compile(pattern, re.IGNORECASE)
                    names = [n for n in names if regex.search(n)]

            return names

        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            return []

    def download(self, remote_path: str, local_path: str) -> None:
        """
        Downloads a file by name from the folder to the local file system.

        :param remote_path: File name on Drive (within folder_id).
        :param local_path: Destination path on local file system.
        """
        try:
            # Find file ID
            result = self._service.files().list(
                q=f"name = '{remote_path}' and '{self.credentials.folder_id}' in parents and trashed = false",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name)"
            ).execute()
            items = result.get("files", [])
            if not items:
                raise FileNotFoundError(f"File '{remote_path}' not found.")

            file_id = items[0]["id"]
            request = self._service.files().get_media(fileId=file_id, supportsAllDrives=True)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        self.logger.info(f"Download progress: {int(status.progress() * 100)}%")

            self.logger.info(f"Downloaded '{remote_path}' to '{local_path}'.")

        except Exception as e:
            self.logger.error(f"Failed to download '{remote_path}': {e}")
            raise

    def upload(self, local_path: str, remote_path: str) -> None:
        """
        Uploads a file from the local path to Google Drive under the configured folder.

        If a file with the same name exists, it will be replaced.

        :param local_path: Full local file path.
        :param remote_path: Desired name of the file on Drive.
        """
        if not self.credentials.folder_id:
            raise ValueError("folder_id must be set in credentials to upload files.")

        try:
            self.logger.info(f"Uploading {local_path} as '{remote_path}' to folder ID {self.credentials.folder_id}")

            # Check if a file with the same name already exists
            existing = self._service.files().list(
                q=f"name = '{remote_path}' and '{self.credentials.folder_id}' in parents and trashed = false",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id)"
            ).execute().get("files", [])

            media = MediaFileUpload(local_path, resumable=True)

            if existing:
                file_id = existing[0]["id"]
                self._service.files().update(
                    fileId=file_id,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                self.logger.info(f"Updated existing file '{remote_path}' (ID: {file_id}).")
            else:
                self._service.files().create(
                    body={
                        "name": remote_path,
                        "parents": [self.credentials.folder_id]
                    },
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True
                ).execute()
                self.logger.info(f"Uploaded new file '{remote_path}'.")

        except Exception as e:
            self.logger.error(f"Failed to upload '{remote_path}': {e}")
            raise

    def move(self, src_path: str, dest_path: str) -> None:
        """
        Renames a file in the Drive folder by changing its name.

        :param src_path: Current file name.
        :param dest_path: New file name.
        """
        try:
            result = self._service.files().list(
                q=f"name = '{src_path}' and '{self.credentials.folder_id}' in parents and trashed = false",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name)"
            ).execute()
            files = result.get("files", [])

            if not files:
                raise FileNotFoundError(f"File '{src_path}' not found for renaming.")

            file_id = files[0]["id"]

            self._service.files().update(
                fileId=file_id,
                body={"name": dest_path},
                supportsAllDrives=True
            ).execute()

            self.logger.info(f"Renamed '{src_path}' to '{dest_path}' (ID: {file_id})")

        except Exception as e:
            self.logger.error(f"Failed to rename '{src_path}' to '{dest_path}': {e}")
            raise

    def delete(self, remote_path: str) -> None:
        """
        Deletes a file with the given name in the folder.

        :param remote_path: File name on Drive.
        """
        try:
            result = self._service.files().list(
                q=f"name = '{remote_path}' and '{self.credentials.folder_id}' in parents and trashed = false",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id)"
            ).execute()
            files = result.get("files", [])

            if not files:
                self.logger.warning(f"File '{remote_path}' not found for deletion.")
                return

            for f in files:
                self._service.files().delete(
                    fileId=f["id"],
                    supportsAllDrives=True
                ).execute()
                self.logger.info(f"Deleted file '{remote_path}' (ID: {f['id']})")

        except Exception as e:
            self.logger.error(f"Failed to delete '{remote_path}': {e}")
            raise

    def make_dir(self, path: str) -> None:
        """
        Creates a folder inside the configured root folder.

        :param path: Folder name (non-nested).
        """
        try:
            # Check if folder already exists
            existing = self._service.files().list(
                q=(
                    f"name = '{path}' and "
                    f"mimeType = 'application/vnd.google-apps.folder' and "
                    f"'{self.credentials.folder_id}' in parents and trashed = false"
                ),
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id)"
            ).execute().get("files", [])

            if existing:
                self.logger.info(f"Folder '{path}' already exists.")
                return

            # Create new folder
            folder_metadata = {
                "name": path,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.credentials.folder_id]
            }
            folder = self._service.files().create(
                body=folder_metadata,
                fields="id",
                supportsAllDrives=True
            ).execute()

            self.logger.info(f"Created folder '{path}' (ID: {folder['id']})")

        except Exception as e:
            self.logger.error(f"Failed to create folder '{path}': {e}")
            raise

    def exists(self, remote_path: str) -> bool:
        """
        Checks if a file with the given name exists in the folder.

        :param remote_path: File name to check.
        :return: True if exists, else False.
        """
        try:
            result = self._service.files().list(
                q=f"name = '{remote_path}' and '{self.credentials.folder_id}' in parents and trashed = false",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id)"
            ).execute()
            return bool(result.get("files"))
        except Exception as e:
            self.logger.warning(f"exists() check failed: {e}")
            return False

    def is_alive(self) -> bool:
        """
        Tests whether we can list contents of the folder.
        """
        try:
            self.list()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """
        Cleanup not required for GDrive API.
        """
        self.logger.info("GDriveHandler closed.")
