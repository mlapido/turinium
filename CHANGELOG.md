# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.3] - unreleased

### Added
- [DBServices] New `view` services type added.

### Changed

### Removed

---

## [0.2.2a0] - 2025-08-18

### Added
- [AppConfig] Support for `.json5` configuration files using the `json5` package.
- [AppConfig] When both `.json` and `.json5` files exist with the same name, `.json5` is prioritized and `.json` is ignored.
- [AppConfig] New feature to automatically instantiate dataclass objects from blocks that declare a `to_dataclass` property.
- [AppConfig] Recursive resolution of `to_dataclass` entries within nested config blocks in `AppConfig`.
- [AppConfig] Support for resolving lists of dataclasses via the `to_dataclass_list` and `list` keys.
- [AppConfig] Added error handling with specific exceptions:
  - `MissingDataClassError` is raised when a referenced dataclass cannot be imported.
  - `DataClassInstantiationError` is raised when a dataclass cannot be instantiated due to missing or invalid arguments.
- [Tests] Introduced unit tests for the `AppConfig` module covering JSON5 support and `to_dataclass` and `to_dataclass_list` functionality.
- [Tests] Complete unit test suite for the revamped `database` module covering `DBConnection`, `DBServices`, service registration, error handling, and execution flow.
- [DBServices] New `execute()` and `execute_batch()` methods introduced as unified entry points for running services (stored procedures, functions, or upsert operations). They support service type dispatching, batch handling, and optional execution time logging via the `log_duration` config flag.
- [DBServices] Added support for a new service type `"query"` for executing raw SQL queries from `.sql` files. All `.sql` files must reside in a designated folder (e.g., `sql/` or `queries/`) to be discoverable and organized.
- [DBServices] `log_duration` flag in the service config enables optional debug-level logging of execution duration per service call.
- [DBServices] Support for service pre-validation at registration time (missing keys, unsupported types, etc.) with detailed exceptions:
  - `InvalidServiceConfigError` for incomplete or malformed service declarations.
  - `UnsupportedServiceTypeError` for unknown service types.
  - `DatabaseNotRegisteredError` for references to non-registered database aliases.
- [DBServices] Deprecated legacy methods `exec_service()` and `exec_service_batch()` are retained with warning messages for backward compatibility.
- [DBCredentials] Introduced `_get_driver()` as a private method to resolve the SQL Server ODBC driver with a fallback to `"ODBC Driver 17 for SQL Server"` if not explicitly provided.
- [DBConnection] Unified `execute()` method introduced to handle `sp`, `fn`, `query`, and `upsert` service types consistently.
- [DBConnection] Support for `ret_type` in service definitions, allowing automatic return conversion to DataFrame or mapped dataclass instances.
- [DBConnection] Optional `log_duration` per-service flag to log execution duration.
- [DBConnection] Optional `service_config` parameter in `execute()` method, providing runtime access to extended metadata.
- [DBConnection] Result mapping to dataclass lists when `ret_type` is a dataclass type.
- [Docs] Introduced `docs/` folder with initial documentation structure using `MkDocs`.
- [Docs] Added `index.md` and `intro.md` to provide an overview of the Turinium framework.
- [Docs] Added `api.md` as a placeholder for future auto-generated API reference via `mkdocstrings`.
- [Docs] Included `mkdocs.yml` configuration file to define site structure, theme, and plugin settings.

### Changed
- [AppConfig] `get_config_block(block_name)` method now retrieves the instantiated dataclass for a given configuration block.
- [AppConfig] `_resolve_config_files()` now prioritizes `.json5` over `.json` and filters out duplicate base names.
- [AppConfig] `_parse_config_file()` now supports `.json5` and improved its docstring accordingly.
- [AppConfig] `_load_config_from_files()` now resolves dataclasses immediately after loading.
- [AppConfig] All relevant docstrings updated to reflect new capabilities and Sphinx-style documentation guidelines.
- [DBServices] Refactored and modularized internal logic for execution and batch processing. Moved core logic into `_execute_single()` and `_execute_batch()` internal methods.
- [DBServices] Private attributes and helper methods are now consistently prefixed with `_`, following internal naming conventions.
- [DBServices] Expanded and standardized all docstrings using Sphinx-style conventions, and added inline comments for maintainability and clarity.
- [DBServices] All raised exceptions now provide clear contextual error messages, including service name and reason for failure when possible.
- [DBCredentials] Improved internal logic in `get_connection_url()` to delegate SQL Server driver resolution to `_get_driver()` method.
- [DBCredentials] Updated inline comments and docstrings for clarity and maintainability. Enforced consistent use of `Literal["sqlserver", "postgres"]` as an interim solution before migrating to Enums in a future version.
- [DBConnection] Refactored dispatching logic to remove duplication across service type handlers (`sp`, `fn`, `query`, `upsert`).
- [DBConnection] Improved error handling and execution fallback flow, returning `(False, None)` only on expected soft failures.
- [DBConnection] All docstrings updated to follow Sphinx formatting and clarify the behavior of public methods and parameters.
- README.md was updated to reflect the new features and changes.

### Removed
- [DBServices] Internal duplication of execution logic between single and batch service calls, replacing it with a shared dispatching mechanism.
- [DBServices] Reliance on `Tuple[bool, Any]` returns in favor of raising precise exceptions for fatal issues, except when fallback `(False, None)` returns are appropriate (e.g., unknown service).
- [DBServices] The `DBRouter` class; its responsibilities were merged into `DBServices` to simplify connection management.
- [DBConnection] Removed legacy methods like `execute_sp()`, `execute_fn()`, and `execute_query()` in favor of unified `execute()`.
- [DBConnection] Removed special casing for `"as_dataframe"` argument in favor of `ret_type`-based return mapping.

---

## [0.2.1] - 2025-05-24

### Changed
- [DBServices] Improved database writing issues handling by catching exceptions on integrity and foreign key violations.

---

## [0.2.0] - 2025-05-11

### Added
- [AppConfig] `SharedAppConfig` factory class for managing and caching shared `AppConfig` instances based on normalized `config_files` and `env_file` arguments.
- [AppConfig] Support for passing a directory as `config_files`, automatically loading all files with supported extensions (`.json`, `.toml`, `.yaml`, `.yml`).
- [AppConfig] Support for passing a list containing paths to files and/or directories as `config_files`.
- [DBServices] Support for automatic registration of databases and services via the `auto_register()` class method.
- [DBServices] Added `exec_service_batch` method for executing a registered service across multiple rows (from a DataFrame or list), with optional `stop_on_fail` behavior configurable per call or via service config.
- [DataSourceServices:NEW] Support for handling different data sources like FTP, S3, FileSystem, and others. At this time, only FTP is implemented.
- [DataSourceServices:NEW] `FTPCredentials` dataclass to hold connection info to an FTP server.
- [DataSourceServices:NEW] `FTPConnection` class to manage FTP connections.
- [DataSourceServices:NEW] `FTPDataSource` class to handle FTP servers as data sources.
- [DataSourceServices:NEW] `BaseDataSource` abstract base class for implementing data sources.
- [DataSource] Added `ensure_dir()` and `folder_exists()` methods to create folders if missing and check for their existence.
- [DataSource] Enhanced `list_files()` method to support optional file filtering via pattern matching.
- [DataSourceServices] Now supports auto-registering its configuration using `SharedAppConfig`.

### Changed
- [AppConfig] Improved `_resolve_config_files()` to validate config extensions and normalize inputs to absolute `Path` objects.
- [AppConfig] Updated all docstrings in `AppConfig` and `SharedAppConfig` to align with project-wide Sphinx-style documentation guidelines.
- [DBServices] Replaced the config tags `"sp"` and `"fn"` with a unified `"routine"` tag for consistency.
- [Project Structure] Some `__init__.py` entries were corrected.
- [Project Structure] `SharedAppConfig` moved to its own dedicated file.
- [DBServices] Adjusted to handle stored procedures with params properly..
- [DataSource] Alass FTPConnection had several fixes related to file names and paths,

### Removed
- [Loaders] The `loaders` module has been abandoned and removed from the project.

---

## [0.1.1] - 2025-05-07

### Added
- First stable release of the `turinium` package.
- Core classes: `AppConfig`, `EmailSender`, `DBConnection`, `TLogging`, etc.
- Logging support with multiple outputs (console, file, JSON).
- Configuration merging from CLI, .env, and config files.
- SQL execution helpers for PostgreSQL and SQL Server.
- Streamlit authentication scaffolding.

### Changed
- None.

### Removed
- None.

---