from typing import Dict, Any, Type
from turinium.datasources.base import BaseDataSource
from turinium.datasources.ftp_credentials import FTPCredentials
from turinium.datasources.ftp import FTPDataSource
from turinium.logging import TLogging


class DataSourceServices:
    """
    Manages data source registration and instantiation for different types like FTP, S3, or Local folders.

    Responsibilities:
    - Parse and store configuration for all available sources.
    - Provide BaseDataSource instances on demand based on registered source names.
    """

    _sources: Dict[str, Dict[str, Any]] = {}
    _logger = TLogging("DataSourceServices", log_filename="data_sources", log_to=("console", "file"))

    _source_types: Dict[str, Type[BaseDataSource]] = {
        "FTP": FTPDataSource
        # future: "S3": S3DataSource, "LOCAL": LocalFolderDataSource
    }

    @classmethod
    def register_sources(cls, sources_dict: Dict[str, Dict[str, Any]]):
        """
        Registers source configurations from a config block.

        Expected structure:
        {
            "LEBES": {
                "source_type": "FTP",
                "host": "...",
                "port": 21,
                "username": "...",
                ...
            },
            ...
        }
        """
        for name, data in sources_dict.items():
            source_type = data.get("source_type")
            if not source_type:
                cls._logger.warning(f"Skipping source '{name}' — missing 'source_type'")
                continue
            cls._sources[name] = {
                "type": source_type.upper(),
                "config": data
            }
            cls._logger.info(f"Registered source '{name}' of type '{source_type.upper()}'")

    @classmethod
    def get_source(cls, name: str) -> BaseDataSource:
        """
        Returns an initialized BaseDataSource instance based on a registered source name.

        :param name: The name of the source to retrieve.
        :raises ValueError: If the source is not registered or source_type is unsupported.
        """
        if name not in cls._sources:
            raise ValueError(f"Source '{name}' is not registered")

        entry = cls._sources[name]
        source_type = entry["type"]
        config = entry["config"]

        if source_type not in cls._source_types:
            raise ValueError(f"Unsupported source_type '{source_type}' for source '{name}'")

        if source_type == "FTP":
            creds = FTPCredentials(name=name, **config)
            return FTPDataSource(creds)

        raise RuntimeError(f"No handler implemented for source_type: {source_type}")