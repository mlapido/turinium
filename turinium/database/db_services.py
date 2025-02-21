import pandas as pd
from typing import Any, Dict, Optional, Tuple, Union
from turinium.database.db_router import DBRouter
from turinium.logging import TLogging
from dataclasses import is_dataclass

class DBServices:
    """
    Handles stored procedure and function execution dynamically
    using registered database services.
    """

    _services = {}
    _logger = TLogging("DBServices", log_filename="db_services", log_to=("console", "file"))

    @classmethod
    def register_databases(cls, db_configs: Dict[str, Any]):
        """
        Register database connections from configuration.

        :param db_configs: Dictionary of database configurations.
        """
        DBRouter.load_databases(db_configs)  # Use class directly
        cls._logger.info(f"Databases registered: {list(db_configs.keys())}")

    @classmethod
    def register_services(cls, services_config: Dict[str, Any]):
        """
        Register stored procedures and functions from configuration.

        :param services_config: Dictionary mapping service names to configurations.
        """
        cls._services.update(services_config)
        cls._logger.info(f"Services registered: {list(services_config.keys())}")

    @classmethod
    def exec_service(
        cls, service_name: str, params: Optional[Union[Tuple, Any]] = None,
        close_connection: bool = False
    ) -> Tuple[bool, Union[pd.DataFrame, Any]]:
        """
        Execute a registered stored procedure or function.

        :param service_name: The name of the registered service.
        :param params: Parameters for the stored procedure or function.
        :param close_connection: Whether to immediately close the DB connection after execution.
        :return: (success, result) where result is a Pandas DataFrame or a DataClass.
        """
        if service_name not in cls._services:
            cls._logger.error(f"Service '{service_name}' not found in registered services.")
            return False, None

        service = cls._services[service_name]
        required_keys = {"db", "type", "ret_type"}
        if service["type"] == "sp":
            required_keys.add("sp")
        elif service["type"] == "fn":
            required_keys.add("fn")

        missing_keys = required_keys - set(service.keys())
        if missing_keys:
            cls._logger.error(f"Service '{service_name}' is missing keys: {missing_keys}")
            return False, None

        db_name = service["db"]
        query_type = service["type"]
        ret_type = service["ret_type"]
        query_name = service.get("sp", service.get("fn"))[0]

        if not query_name:
            cls._logger.error(f"Service '{service_name}' does not have a valid 'sp' or 'fn'.")
            return False, None

        # Ensure params is always a tuple
        params = (params,) if params and not isinstance(params, tuple) else params or ()

        # Execute the query
        success, result = DBRouter.execute_query(db_name, query_type, query_name, params)

        # Close connection if requested
        if close_connection and DBRouter.has_connection(db_name):
            DBRouter.close_connection(db_name)

        # Process result based on return type
        if not success:
            return False, None
        elif ret_type == "pandas":
            return True, result  # Pandas DataFrame is already in the right format
        elif isinstance(ret_type, type) and is_dataclass(ret_type):  # Convert **all** rows to DataClass instances
            return True, [ret_type(**row) for row in result] if result else []
        else:
            return True, result  # Default return
