import pandas as pd
from typing import Any, Dict, Optional, Tuple, Union
from turinium.database.db_router import DBRouter
from turinium.logging import TLogging
from dataclasses import is_dataclass

class DBServices:
    """
    DBServices is a utility class that dynamically handles the execution of
    stored procedures and functions using registered database services.

    It supports two modes of operation:

    1. **Manual Registration**:
       You can register databases and service mappings manually by calling:

           DBServices.register_databases(databases_dict)
           DBServices.register_services(services_dict)

       This is useful when your app manages configuration directly or
       constructs services at runtime.

    2. **Automatic Registration**:
       If `SharedAppConfig` has been initialized, you can auto-load the
       configurations by calling:

           DBServices.auto_register()

       This method will retrieve `databases` and `services` blocks from the
       shared AppConfig instance (e.g., loaded at app startup), and register
       them automatically. This minimizes boilerplate and keeps your startup
       code clean.

    Internally, DBServices handles logging via TLogging and supports execution
    abstractions designed to standardize interaction with multiple databases
    through a unified service interface.
    """

    _services = {}
    _logger = TLogging("DBServices", log_filename="db_services", log_to=("console", "file"))

    @classmethod
    def auto_register(cls):
        """
        Automatically register databases and services from configuration using AppConfig.
          AppConfig MUST have been initialized as shared before calling this method.
        """
        from turinium.config import SharedAppConfig

        if SharedAppConfig.has_instance():
            app_config = SharedAppConfig.get_instance()
            databases = app_config.get(' databases', None)
            services = app_config.get(' services', None)

            if databases:
                cls.register_databases(databases)
            else:
                cls._logger.info(f"No database configurations found to register, skipping.")

            if services:
                cls.register_services(services)
            else:
                cls._logger.info(f"No services configurations found to register, skipping.")
        else:
            cls._logger.info(f"Couldn't auto, register no instance of AppConfig found.")

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
        success, result = DBRouter.execute_query(db_name, query_type, query_name, params, ret_type)

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

    @classmethod
    def exec_service_batch(
            cls,
            service_name: str,
            batch_data: Union[pd.DataFrame, list],
            close_connection: bool = False,
            stop_on_fail: Optional[bool] = None
    ) -> Tuple[bool, list]:
        """
        Executes a registered stored procedure or function for each row in the provided batch.

        :param service_name: The name of the registered service.
        :param batch_data: A DataFrame or a list of tuples/lists containing parameters per call.
        :param close_connection: Whether to immediately close the DB connection after execution.
        :param stop_on_fail: Whether to stop execution on the first failure. If None, uses service config.
        :return: (success, list_of_results) where each item is the result of a call (or an error dict).
        """
        if service_name not in cls._services:
            cls._logger.error(f"Service '{service_name}' not found in registered services.")
            return False, []

        service = cls._services[service_name]
        results = []
        all_success = True

        # Determine stop behavior
        config_stop_on_fail = service.get("stop_on_fail", False)
        effective_stop_on_fail = stop_on_fail if stop_on_fail is not None else config_stop_on_fail

        # Normalize input
        if isinstance(batch_data, pd.DataFrame):
            rows = batch_data.itertuples(index=False, name=None)
        elif isinstance(batch_data, list):
            rows = batch_data
        else:
            cls._logger.error("batch_data must be a DataFrame or a list of rows.")
            return False, []

        for i, row in enumerate(rows):
            params = (row,) if not isinstance(row, (tuple, list)) else tuple(row)
            success, result = cls.exec_service(service_name, params=params, close_connection=False)

            if success:
                cls._logger.info(f"[{service_name}][Row {i}] Success.")
            else:
                cls._logger.error(f"[{service_name}][Row {i}] Failed. Params: {params}")
                all_success = False
                if effective_stop_on_fail:
                    cls._logger.warning("Batch execution stopped due to failure.")
                    break

            results.append(result)

        if close_connection:
            db_name = service["db"]
            if DBRouter.has_connection(db_name):
                DBRouter.close_connection(db_name)

        return all_success, results