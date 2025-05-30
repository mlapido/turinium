# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

<!-- Links for version comparison (optional) -->
[Unreleased]: https://bitbucket.org/your-org/turinium/compare/master...HEAD
[1.0.0]: https://bitbucket.org/your-org/turinium/compare/v0.0.1...v1.0.0