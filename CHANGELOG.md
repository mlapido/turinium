# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- .

### Changed
- .

---

## [0.2.0] - 2025-05-11

### Added
- [AppConfig] `SharedAppConfig` factory class for managing and caching shared `AppConfig` instances based on normalized `config_files` and `env_file` arguments.
- [AppConfig] Support for passing a directory as `config_files`, automatically loading all files with supported extensions (`.json`, `.toml`, `.yaml`, `.yml`).
- [AppConfig] Support for passing a list containing paths to files and/or directories as `config_files`.
- [DBServices] Support for automatic registration of databases and services in `DBServices`via the `auto_register()` class method.
- [DBServices] Added support for executing a registered service across multiple rows (from a DataFrame or list) via the new `exec_service_batch` method, with optional `stop_on_fail` behavior configurable per call or via service config.
- [DataSourceServices:NEW] Supoport for handling different data sources like FTP, S3, FileSystem, and others. At this time only FTP is implemented.
- [DataSourceServices:NEW] `FTPCredentials` dataclass to hold connection info to a FTP server.
- [DataSourceServices:NEW] `FTPConnection` class to handle the connection to a FTP server.
- [DataSourceServices:NEW] `FTPDataSource` class that implements a FTP server as a data source.
- [DataSourceServices:NEW] `BaseDataSource` base class to implement data sources.

### Changed
- [AppConfig] Improved `_resolve_config_files()` to validate config extensions and normalize inputs to absolute `Path` objects.
- [AppConfig] Updated all docstrings in `AppConfig` and `SharedAppConfig` to align with project-wide Sphinx-style documentation guidelines.

### Removed
- None.

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