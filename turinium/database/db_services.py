import os
import time
import pandas as pd

from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import is_dataclass
from turinium.logging import TLogging
from .db_connection import DBConnection
from .db_credentials import DBCredentials
from turinium.config import SharedAppConfig


class DBServices:
    """
    DBServices is a utility class that dynamically handles the execution of
    stored procedures, functions, upserts, and raw SQL queries using registered
    database services.

    It supports two modes of operation:

    1. **Manual Registration**:
       You can register databases and service mappings manually by calling:

           DBServices.register_databases(databases_dict)
           DBServices.register_services(services_dict)

       This is useful when your app manages configuration directly or constructs
       services at runtime.

    2. **Automatic Registration**:
       If `SharedAppConfig` has been initialized, you can auto-load the
       configurations by calling:

           DBServices.auto_register()

       This method retrieves `databases` and `services` blocks from the shared
       AppConfig instance (e.g., loaded at app startup), and registers them
       automatically. This minimizes boilerplate and keeps your startup code clean.

    Each service is validated at registration time to ensure correctness of:
    - Required keys and supported service types
    - Query file paths (if type is 'query')
    - Column definitions (if type is 'upsert')
    - Existence of the database alias in the registered databases

    Supported service types include:
    - **procedure**: A SQL stored procedure (can be executed without expecting a result)
    - **function**: A SQL function (expected to return a result set)
    - **upsert**: A batch INSERT or UPSERT operation using either bulk loading
      or parameterized inserts, depending on the database backend
    - **query**: A raw SQL query loaded from a `.sql` file and executed directly
    - **view**: A SQL view that can be executed directly, with or witout params.

    All executions are routed through the appropriate `DBConnection` methods:
    `execute()` for single operations and `execute_batch()` for row-wise batched services.

    **Query File Convention**:
    For services of type `'query'`, the `.sql` file path must be provided in the `query_file` key.
    As a convention, all `.sql` files should be placed in a dedicated folder (e.g., `sql/` or `queries/`)
    within your project. Users may further organize that folder as needed (e.g., subfolders per domain),
    but must ensure that the full relative path is correctly referenced in the service definition.

    All logging is handled via the `TLogging` system and includes optional execution timing
    (for debug or performance analysis).

    This class supersedes the earlier `DBRouter` abstraction, providing a unified
    interface to interact with multiple databases through a service-driven model.
    """
    _connections: Dict[str, DBConnection] = {}
    _services: Dict[str, Dict[str, Any]] = {}
    _logger = TLogging("DBServices", log_filename="db_services", log_to=("console", "file"))

    @classmethod
    def auto_register(cls):
        """
        Automatically register databases and services from configuration using AppConfig.
          AppConfig MUST have been initialized as shared before calling this method.
        """
        if SharedAppConfig.is_initialized():
            app_config = SharedAppConfig()
            databases = app_config.get_config_block('databases')
            services = app_config.get_config_block('db_services')

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
    def register_databases(cls, db_configs: Dict[str, Any]) -> None:
        """
        Registers and instantiates database connections.

        :param db_configs: A dictionary of db_name → db_credential_config
        :raises Exception: If instantiation fails
        """
        for name, config in db_configs.items():
            try:
                credentials = DBCredentials(name, **config)
                cls._connections[name] = DBConnection(credentials)
            except Exception as e:
                cls._logger.error(f"Failed to initialize connection '{name}': {e}", exc_info=True)
                raise

        cls._logger.info(f"Databases registered: {list(db_configs.keys())}")

    @classmethod
    def register_services(cls, services_config: Dict[str, Any]) -> None:
        """
        Registers and validates service entries.

        Service types supported: 'sp', 'fn', 'query', 'upsert', 'view'

        :param services_config: Dictionary of service_name → config
        :raises ValueError: If a required field is missing
        :raises FileNotFoundError: If a query_file is specified but does not exist
        """
        valid_types = {"sp", "fn", "upsert", "query", "view"}
        for service_name, config in services_config.items():
            db = config.get("db") or config.get("database")
            service_type = config.get("type")

            if db not in cls._connections:
                cls._logger.error(f"Service '{service_name}' references unknown DB: '{db}'")
                raise ValueError(f"Unknown DB for service: {service_name}")

            if service_type not in valid_types:
                cls._logger.error(f"Service '{service_name}' has invalid type: '{service_type}'")
                raise ValueError(f"Invalid service type: {service_type}")

            required_keys = {
                "sp": ["routine"],
                "fn": ["routine"],
                "view": ["view"],
                "query": ["query_file"],
                "upsert": ["table", "columns", "constraint"]
            }

            missing = [k for k in required_keys[service_type] if k not in config]
            if missing:
                cls._logger.error(f"Service '{service_name}' is missing keys: {missing}")
                raise ValueError(f"Invalid config for service: {service_name}")

            if service_type == "query":
                path = config["query_file"]
                if not os.path.isfile(path):
                    cls._logger.error(f"Query file not found for service '{service_name}': {path}")
                    raise FileNotFoundError(f"Missing SQL file for service: {service_name}")

        cls._services.update(services_config)
        cls._logger.info(f"Services registered: {list(services_config.keys())}")

    @classmethod
    def execute(cls, service_name: str, params: Optional[Union[Tuple, list, dict]] = None,
                close_connection: bool = False) -> Tuple[bool, Union[pd.DataFrame, Any, None]]:
        """
        Executes a registered service.

        :param service_name: The registered service name.
        :param params: Parameters for execution. Tuple/list for SP/FN, dict for query.
        :param close_connection: If True, closes connection after execution.
        :return: (success, result or None)
        """
        start = time.time()

        service = cls._services.get(service_name)
        if not service:
            raise ValueError(f"Service '{service_name}' is not registered.")

        db_name = service.get("db") or service.get("database")
        conn = cls._connections.get(db_name)
        service_type = service["type"]
        ret_type = service.get("ret_type", "default")
        routine = service.get("routine")
        param_types = service.get("params_types")
        log_duration = service.get("log_duration", False)

        try:
            result = conn.execute(
                service_type=service_type,
                query=service_name if service_type in ("upsert", "query") else routine,
                params=params,
                param_types=param_types,
                ret_type=ret_type,
                service_config=service
            )
        except Exception as e:
            cls._logger.error(f"Error executing service '{service_name}': {e}", exc_info=True)
            return False, None

        if close_connection:
            conn.close()
            del cls._connections[db_name]

        success, output = result
        if not success:
            return False, None

        if log_duration:
            elapsed = time.time() - start
            cls._logger.debug(f"[{service_name}] executed in {elapsed:.3f} seconds")

        if isinstance(ret_type, type) and is_dataclass(ret_type):
            return True, [ret_type(**row) for row in output] if output else []
        return True, output

    @classmethod
    def execute_batch(cls, service_name: str, batch_data: Union[list, pd.DataFrame],
                      close_connection: bool = False, stop_on_fail: Optional[bool] = None) -> Tuple[bool, list]:
        """
        Executes a registered service for a batch of inputs.

        :param service_name: Name of registered service.
        :param batch_data: A DataFrame or list of params.
        :param close_connection: If True, closes DB connection after use.
        :param stop_on_fail: If True, aborts batch on first failure.
        :return: (overall_success, list of individual results)
        """
        import time
        start = time.time()

        if service_name not in cls._services:
            cls._logger.error(f"Service not registered: {service_name}")
            return False, []

        service = cls._services[service_name]
        results = []
        all_success = True
        failure_count = 0
        total = len(batch_data)
        log_duration = service.get("log_duration", False)

        effective_stop = stop_on_fail if stop_on_fail is not None else service.get("stop_on_fail", False)
        rows = batch_data.itertuples(index=False, name=None) if isinstance(batch_data, pd.DataFrame) else batch_data

        for i, row in enumerate(rows):
            current_params = row if isinstance(row, (tuple, list, dict)) else (row,)
            success, result = cls.execute(service_name, params=current_params, close_connection=False)
            results.append(result)

            if not success:
                failure_count += 1
                all_success = False
                cls._logger.error(f"[{service_name}] Row {i + 1} failed.")
                if effective_stop:
                    cls._logger.warning(f"[{service_name}] Aborting batch execution after first failure.")
                    break

        if close_connection:
            db_name = service["db"]
            if db_name in cls._connections:
                cls._connections[db_name].close()
                del cls._connections[db_name]

        if log_duration:
            elapsed = time.time() - start
            cls._logger.debug(f"[{service_name}] batch executed in {elapsed:.3f} seconds")

        return all_success, results

    # --- Deprecated wrappers for backward compatibility ---

    @classmethod
    def exec_service(cls, *args, **kwargs):
        """DEPRECATED. Use `execute()` instead."""
        return cls.execute(*args, **kwargs)

    @classmethod
    def exec_service_batch(cls, *args, **kwargs):
        """DEPRECATED. Use `execute_batch()` instead."""
        return cls.execute_batch(*args, **kwargs)