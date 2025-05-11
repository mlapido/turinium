from typing import Dict, Optional
from turinium.logging import TLogging
from turinium.config import SharedAppConfig
from turinium.ftp_credentials import FTPCredentials


class FTPServices:
    """
    Manages FTP and SFTP connections and associated services.

    Provides registration and configuration loading for FTP servers and service definitions.
    Service definitions contain additional behavior like patterns, remote paths, and workflow rules.

    Supports:
      - Manual registration via `register_servers` and `register_services`
      - Automatic loading from configuration using `auto_load()`

    Example: Manual registration
    -----------------------------
        FTPServices.register_servers({
            "LEBES": FTPCredentials(name="LEBES", host="...", ...)
        })

        FTPServices.register_services({
            "ImportaCSV": {
                "server": "LEBES",
                "remote_dir": "/incoming",
                "processing_dir": "/processing",
                "processed_dir": "/processed",
                "patterns": ["*.csv"],
                "pattern_mode": "glob"
            }
        })

    Example: Auto-loading from configuration
    ----------------------------------------
        from turinium.config import AppConfig, SharedAppConfig

        config = AppConfig("config.json")
        SharedAppConfig.set_instance(config)
        FTPServices.auto_load()
    """

    _logger = TLogging("FTPServices", log_filename="ftp_services", log_to=("console", "file"))
    _servers: Dict[str, FTPCredentials] = {}
    _services: Dict[str, dict] = {}

    @classmethod
    def register_servers(cls, servers: Dict[str, dict]) -> None:
        """
        Registers one or more FTP server credentials from a dictionary.
        """
        for name, data in servers.items():
            try:
                creds = FTPCredentials(name=name, **data)
                cls._servers[name] = creds
                cls._logger.info(f"Registered FTP server: {name}")
            except Exception as e:
                cls._logger.error(f"Failed to register FTP server '{name}': {e}")

    @classmethod
    def register_services(cls, services: Dict[str, dict]) -> None:
        """
        Registers one or more FTP service definitions.
        """
        for name, config in services.items():
            if 'server' not in config:
                cls._logger.warning(f"Service '{name}' missing required 'server' key. Skipping.")
                continue
            cls._services[name] = config
            cls._logger.info(f"Registered FTP service: {name}")

    @classmethod
    def auto_load(cls) -> None:
        """
        Automatically loads FTP servers and services from the shared application config.

        Expects:
          - 'ftp_servers' block for FTPCredentials
          - 'ftp_services' block for service definitions
        """
        if not SharedAppConfig.has_instance():
            cls._logger.warning("No SharedAppConfig instance available. Skipping auto-load.")
            return

        config = SharedAppConfig()

        ftp_servers = config.get('ftp_servers', {})
        ftp_services = config.get('ftp_services', {})

        if ftp_servers:
            cls.register_servers(ftp_servers)
        else:
            cls._logger.info("No FTP servers found in config.")

        if ftp_services:
            cls.register_services(ftp_services)
        else:
            cls._logger.info("No FTP services found in config.")
