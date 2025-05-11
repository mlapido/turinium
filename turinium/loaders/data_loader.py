import importlib
import os
from typing import Dict, Any
from turinium.datasources.services import DataSourceServices
from turinium.logging import TLogging
from turinium.loaders.interfaces import BaseValidator
from turinium.db import DBServices


class DataLoader:
    """
    Loads and processes files from a configured data source (FTP, S3, local, etc.).
    For each matching file, it performs validation and forwards it to a registered
    DB service, managing file movement through processing stages.

    This class is designed to be configuration-driven, and can be extended if needed.
    """

    def __init__(self, service_name: str, config: Dict[str, Any]):
        """
        Initializes the DataLoader with a service name and its configuration block.

        :param service_name: The name of the service to run.
        :param config: The full configuration dictionary for the service, as defined
                       in the services block (e.g., ftp_services).
        """
        self.service_name = service_name
        self.config = config
        self.logger = TLogging(f"DataLoader-{service_name}", log_filename="data_loader", log_to=("console", "file"))
        self.source = DataSourceServices.get_source(config["source"])
        self.pattern_mode = config.get("pattern_mode", "glob")
        self.handlers = config.get("handlers", {})

    def run(self):
        """
        Executes the file processing flow:
        - Lists files from the source
        - Validates them
        - Dispatches them to the appropriate DB service
        - Manages movement between folders
        """
        with self.source as conn:
            for type_key, handler in self.handlers.items():
                pattern = handler["pattern"]
                db_service = handler["db_service"]

                file_list = self._list_matching_files(conn, pattern)

                for file_name in file_list:
                    self.logger.info(f"Processing file '{file_name}' (type: {type_key})")

                    try:
                        # Move to the processing directory (if configured)
                        remote_src = os.path.join(self.config["remote_dir"], file_name)
                        remote_tmp = os.path.join(self.config["processing_dir"], file_name)

                        if self.config.get("move_to_processing", True):
                            conn.move_file(remote_src, remote_tmp)
                        else:
                            remote_tmp = remote_src

                        # Download to temporary local path
                        local_path = os.path.join("/tmp", file_name)
                        conn.download_file(remote_tmp, local_path)

                        # Instantiate and run validator
                        validator_cls = self._load_class(handler["validator_class"])
                        validator = validator_cls(local_path, type_key)

                        if not validator.is_valid():
                            self.logger.warning(f"Validation failed for '{file_name}'.")
                            conn.move_file(remote_tmp, os.path.join(self.config["error_dir"], file_name))
                            continue

                        # Send file to DB service
                        DBServices.execute(db_service, local_path)

                        # Move to the processed directory, renaming if configured
                        final_name = self._rename(file_name)
                        conn.move_file(remote_tmp, os.path.join(self.config["processed_dir"], final_name))

                    except Exception as e:
                        self.logger.error(f"Error processing '{file_name}': {e}")
                        conn.move_file(remote_tmp, os.path.join(self.config["error_dir"], file_name))

    def _list_matching_files(self, conn, pattern: str) -> list[str]:
        """
        Lists files from the remote directory that match the specified pattern.

        :param conn: The connected data source.
        :param pattern: Glob or regex pattern for filtering files.
        :return: List of matching file names.
        """
        all_files = conn.list_files(self.config["remote_dir"])

        if self.pattern_mode == "glob":
            from fnmatch import fnmatch
            return [f for f in all_files if fnmatch(f, pattern)]

        elif self.pattern_mode == "regex":
            import re
            compiled = re.compile(pattern)
            return [f for f in all_files if compiled.search(f)]

        return []

    def _load_class(self, dotted_path: str):
        """
        Dynamically imports a class using a dotted path.

        :param dotted_path: Full dotted path to the class (e.g., 'myapp.validators.MyValidator')
        :return: The class object.
        """
        module_path, class_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def _rename(self, original_name: str) -> str:
        """
        Returns the new name for the file based on the rename_mask configuration.
        If no mask is defined, the original name is returned unchanged.

        :param original_name: The original file name.
        :return: The new file name, formatted using the rename_mask.
        """
        mask = self.config.get("rename_mask")
        if not mask:
            return original_name

        from datetime import datetime
        return mask.format(original_name=original_name, date=datetime.now())
