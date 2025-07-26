from typing import Dict, Any, Type
from turinium.storage.base_handler import BaseStorageHandler
from turinium.storage.base_credentials import BaseStorageCredentials
from turinium.storage.ftp.handler import FTPHandler
from turinium.storage.ftp.credentials import FTPCredentials
from turinium.storage.local.handler import LocalStorageHandler
from turinium.storage.local.credentials import LocalStorageCredentials
from turinium.storage.gdrive.handler import GDriveHandler
from turinium.storage.gdrive.credentials import GDriveCredentials
# Other handlers and credentials when implemented:
# from turinium.storage.s3.handler import S3Handler
from turinium.storage.s3.credentials import S3Credentials
# from turinium.storage.onedrive.handler import OneDriveHandler
from turinium.storage.onedrive.credentials import OneDriveCredentials

from turinium.logging import TLogging
from turinium.config import SharedAppConfig


class StorageServices:
    """
    Manages storage handler registration and retrieval for various storage
    types like FTP, SFTP, LOCAL, NAS, Google Drive, OneDrive, AWS S3, etc.

    This class allows configuration-driven initialization of file storage
    connections, enabling unified access to heterogeneous storage sources.

    Registered handlers are used via their logical names, as defined in
    your configuration (e.g., in `.env`-backed `AppConfig`).

    Usage:
        >>> with StorageServices.get_handler("FTP-FFC") as storage:
        >>>      files = storage.list_files("incoming/")
    """

    _handlers: Dict[str, Dict[str, Any]] = {}
    _logger = TLogging("StorageServices", log_filename="storage", log_to=("console", "file"))

    # Mapping protocol strings to tuples of (handler class, credentials class)
    _protocol_registry: Dict[str, Dict[str, Type]] = {
        "ftp": {"handler": FTPHandler, "credentials": FTPCredentials},
        "sftp": {"handler": FTPHandler, "credentials": FTPCredentials},
        "ftps": {"handler": FTPHandler, "credentials": FTPCredentials},
        "local": {"handler": LocalStorageHandler, "credentials": LocalStorageCredentials},
        "gdrive": {"handler": GDriveHandler, "credentials": GDriveCredentials},
        # Future handlers, e.g.:
        # "s3": {"handler": S3Handler, "credentials": S3Credentials},
        # "nas": {"handler": LocalHandler, "credentials": LocalStorageCredentials},
        # "onedrive": {"handler": OneDriveHandler, "credentials": OneDriveCredentials},
    }

    @classmethod
    def auto_register(cls) -> None:
        """
        Automatically registers all storage handler configurations defined
        in the AppConfig under the 'storages_services' block.

        This method should be called after `SharedAppConfig` has been initialized.

        :raises ImportError: If SharedAppConfig has not been initialized.
        """
        if not SharedAppConfig.is_initialized():
            cls._logger.error("Cannot auto-register storages: SharedAppConfig not initialized.")
            raise ImportError("SharedAppConfig must be initialized before calling auto_register.")

        app_config = SharedAppConfig()
        storages = app_config.get_config_block("storages_services")

        if storages:
            cls.register_handlers(storages)
        else:
            cls._logger.info("No storage configurations found to register.")

    @classmethod
    def register_handlers(cls, handler_definitions: Dict[str, Dict[str, Any]]) -> None:
        """
        Registers storage handlers and credentials based on provided configurations.

        Each handler MUST include a 'protocol' field that matches a supported handler protocol.

        :param handler_definitions: Dictionary of handlers to register.
            Example:
            {
                "LEBES-FTP": {
                    "protocol": "FTP",
                    "host": "ftp.acme.com.br",
                    "username": "user",
                    ...
                },
                ...
            }
        """
        for name, config in handler_definitions.items():
            protocol = config.get("protocol", "").lower()

            if not protocol:
                cls._logger.warning(f"Handler '{name}' skipped: 'protocol' missing.")
                continue

            registry_entry = cls._protocol_registry.get(protocol)
            if not registry_entry:
                cls._logger.warning(f"Handler '{name}' skipped: unsupported protocol '{protocol}'.")
                continue

            cred_cls = registry_entry["credentials"]
            handler_cls = registry_entry["handler"]

            try:
                # Instantiate credentials immediately for validation
                credentials = cred_cls(name=name, protocol=protocol, **config)
            except TypeError as e:
                cls._logger.warning(f"Credentials for '{name}' invalid: {e}")
                continue

            # Store both the credentials and handler class for later use
            cls._handlers[name] = {
                "credentials": credentials,
                "handler_cls": handler_cls
            }

            cls._logger.info(
                f"Registered '{name}' with protocol '{protocol}' using credentials '{cred_cls.__name__}'."
            )

    @classmethod
    def get_handler(cls, name: str) -> BaseStorageHandler:
        """
        Retrieves the storage handler for the given name, initialized with its credentials.

        The returned object supports methods like `list_files`, `download_file`, etc.

        :param name: Logical name of the storage handler as defined in config.
        :return: Initialized storage handler instance.
        :raises ValueError: If the handler is not registered.
        """
        entry = cls._handlers.get(name)
        if not entry:
            raise ValueError(f"Storage handler '{name}' is not registered.")

        handler_cls = entry["handler_cls"]
        credentials = entry["credentials"]

        return handler_cls(credentials)

    @classmethod
    def get_credentials(cls, name: str) -> BaseStorageCredentials:
        """
        Retrieves the credentials for the given registered storage name.

        :param name: Registered storage name.
        :return: Credentials instance.
        :raises ValueError: If credentials are not registered.
        """
        entry = cls._handlers.get(name)
        if not entry:
            raise ValueError(f"Credentials for '{name}' are not registered.")

        return entry["credentials"]

    @classmethod
    def list_registered_storages(cls) -> Dict[str, str]:
        """
        Lists all registered storages with their protocol types.

        :return: Dictionary of registered storages and their protocols.
        """
        return {name: entry["credentials"].protocol for name, entry in cls._handlers.items()}
