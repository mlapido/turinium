# Turinium: Empowering Intelligent Systems

Turinium is a modern Python framework designed to reduce boilerplate code and supercharge productivity across teams by offering structured utilities for configuration management, database interaction, logging, and integration with external storage and messaging services.

Turinium is ideal for development teams that want to minimize complexity, avoid repetitive code, and ensure consistent best practices across applications — all while remaining beginner-friendly and accessible to non-specialists looking to prototype or deploy intelligent solutions.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Modules and Usage](#modules-and-usage)
  - [AppConfig](#appconfig)
  - [SharedAppConfig](#sharedappconfig)
  - [DBServices](#dbservices)
  - [TLogging](#tlogging)
  - [EmailSender](#emailsender)
  - [StorageServices](#storageservices)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- Unified configuration handling from `.json`, `.json5`, `.toml`, `.yaml`, `.yml`, and `.env` files.
- Auto-instantiation of config dataclasses (including nested lists of dataclasses).
- Partitioned configuration access with `SharedAppConfig`.
- Database service registry and execution for PostgreSQL and SQL Server.
- Smart logging to console, file, and JSON formats.
- Email sending with rich support for HTML and attachments.
- Abstraction for FTP, Google Drive, OneDrive, and local file system access.

## Installation

```bash
pip install turinium
```

### Optional Database Dependencies

```bash
pip install turinium[database_all]         # PostgreSQL + SQL Server
pip install turinium[database_pg]          # PostgreSQL only
pip install turinium[database_odbc]        # SQL Server (ODBC) only
```

---

## Quick Start

```python
from turinium import AppConfig

config = AppConfig("config/")  # folder or list of files
db_conf = config.get_config_block("databases")
```

Or use the shared global config:

```python
from turinium import SharedAppConfig

config = SharedAppConfig("./config/")
api_conf = config.get_config_block("api")
```

---

## Modules and Usage

### Configuration Management (AppConfig)

Turinium's `AppConfig` reads and merges configuration from one or more files or folders.

```python
from turinium import AppConfig

config = AppConfig(["base.json", "overrides.yaml"])
db_host = config.get_config_value("databases", "host")
```

Supports:
- File types: `.json`, `.json5`, `.toml`, `.yaml`, `.yml`, `.env`
- Value overrides using environment variables
- CLI argument merging
- Mapping blocks to dataclasses:
```json
{
  "ftp": {
    "to_dataclass": "mypackage.config.FTPConfig",
    "host": "ftp.myhost.com"
  }
}
```

---

### SharedAppConfig

When you want configuration available globally:

```python
from turinium import SharedAppConfig

SharedAppConfig.load("config/")
conf = SharedAppConfig.get("databases")
```

Supports:
- Named partitions (e.g., `SharedAppConfig.load(..., name="etl")`)
- Reusable config in any module or class

---

### Database Services (DBServices)

Easily connect to one or more databases and register callable services like:

- `sp`: Stored procedure
- `fn`: Function
- `upsert`: Batch insert/update (PostgreSQL/SQL Server)
- `query`: Raw SQL from file

#### Example Configuration

```json
{
  "GetClients": {
    "db": "main",
    "type": "sp",
    "routine": "usp_GetClients"
  },
  "SalesReport": {
    "db": "analytics",
    "type": "query",
    "command": "sales_report.sql"
  }
}
```

Usage:

```python
from turinium import DBServices as dbs

dbs.register_databases(config.get_config_block("databases"))
dbs.register_services(config.get_config_block("dbservices"))

ok, result = dbs.execute("FetchData", params=("2023-01-01",))
```


---

### Logging (TLogging)

TLogging offers structured, flexible logging with a single line of setup:

```python
from turinium import TLogging

logger = TLogging(log_to=("console", "file", "json"))
logger.info("App initialized")
```

- Multi-destination logging (console, text, JSON)
- Structured or simple formats
- Rotating file support
- Structured JSON logs (great for tracing and automation)

---

### Email Sending (EmailSender)

```python
from turinium import EmailSender

with EmailSender("smtp.mail.com", "user@domain.com", "password", 0) as sender:
    sender.send_email(
        to_list=["target@x.com"],
        subject="Hello",
        html_message="<p>Test</p>",
        text_message="Test"
    )
```

Supports attachments, CC/BCC, and logs any errors on send.

---

### StorageServices

Configure access to FTP, GDrive, OneDrive, or local storage using a unified API.

```python
from turinium.storageservices import DataSourceServices

storage = DataSourceServices.from_config(config.get_config_block("sources"))
ftp = storage.get("my_ftp")
ftp.upload("local.txt", "remote/path.txt")
```

Supported operations:
- Upload/download
- Ensure/make directories
- List and filter files
- Automatically applies base path from config

---

## Contributing

Contributions are welcome!

To contribute:

1. Fork the project.
2. Add tests for any new functionality.
3. Keep docstrings and logging clean.
4. Submit a PR and describe the intent clearly.

Turinium follows best practices in Python packaging and code quality. Use docstrings and include test coverage.

---

## License

MIT License – see `LICENSE` file.