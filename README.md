# Turinium: Empowering Intelligent Systems

Turinium is a modern Python framework designed to streamline software development by reducing boilerplate code and providing essential utility modules for configuration management, logging, database operations, email sending, and more. Inspired by the pioneering work of Alan Turing, Turinium aims to empower intelligent systems for modern developers.

This README provides complete instructions and examples for using each module provided by Turinium. By following this guide, you can integrate Turinium's utilities into your own applications to gain structured configuration, flexible database services, simplified logging, and robust email sending.

## Table of Contents

* [Features](#features)
* [Installation](#installation)
* [Quick Start](#quick-start)
* [Modules and Usage](#modules-and-usage)

  * [Configuration Management (AppConfig)](#configuration-management-appconfig)
  * [Database Services (DBServices)](#database-services-dbservices)
  * [Logging (TLogging)](#logging-tlogging)
  * [Email Sending (EmailSender)](#email-sending-emailsender)
* [Contributing](#contributing)
* [License](#license)

## Features

* Multi-source Configuration Management: Read and merge settings from JSON, YAML, TOML, `.env` files, and command-line arguments.
* Database Connectivity: Easily connect to and operate on PostgreSQL and MS SQL Server using registered services.
* Structured Logging: Log to console, plain-text file, or structured JSON log files.
* Email Sending: Send HTML and plain-text emails with optional attachments and support for CC/BCC.
* Extensibility: Modular architecture to allow simple enhancements and integration into larger systems.

## Installation

### Local Development Installation (Editable Mode)

To work on and test Turinium locally alongside another project:

```bash
pip install -e /path/to/turinium
```

### Remote Installation from Git

If your project is hosted on Bitbucket or another Git provider, you can install it from a branch:

```bash
pip install git+ssh://git@bitbucket.org/ffcservicos/turinium.git@dev
```

### Installing Optional Database Dependencies

Turinium provides optional extras for installing the database drivers:

* To install all supported drivers:

```bash
pip install turinium[database_all]
```

* Only for SQL Server (ODBC):

```bash
pip install turinium[database_odbc]
```

* Only for PostgreSQL:

```bash
pip install turinium[database_pg]
```

## Quick Start

The following example demonstrates how to configure your application to use Turinium for configuration loading:

```python
from turinium import AppConfig

def main():
    # Your app logic here
    pass

if __name__ == '__main__':
    app_config = AppConfig(['./config/config.json', './config/cmd_args.json'])
    main()
```

This ensures that command-line arguments are parsed early, and the configuration system is fully initialized.

## Modules and Usage

### Configuration Management (AppConfig)

The `AppConfig` class centralizes configuration for the application. It supports JSON, TOML, YAML, and `.env` files, and it can parse command-line arguments automatically.

#### Purpose

* Automatically load multiple configuration files
* Apply overrides from environment variables
* Extract structured blocks for easier downstream access
* Share and extend configuration data throughout the app

#### Initialization

You can pass a single file path or a list of file paths:

```python
from turinium import AppConfig

app_config = AppConfig(['./config/base.json', './config/overrides.json'])
```

#### Accessing Blocks and Values

Retrieve a full configuration block:

```python
db_settings = app_config.get_config_block('databases')
```

Retrieve a specific value within a block:

```python
host = app_config.get_config_value('databases', 'host')
```

#### Reading Command-Line Arguments

Turinium automatically reads CLI arguments if defined in a config file. You can access them via:

```python
cmd_args = app_config.get_config_value('Arguments', 'cmd_line_params')
```

#### Adding Runtime Blocks

You can dynamically insert configuration at runtime:

```python
app_config.add_block('runtime', {'timestamp': '2024-01-01T00:00:00'})
```

#### Mapping Environment Variables

You can map environment variables into configuration files using the `%%VAR_NAME%%` syntax:

.env file:

```
SMTP_SERVER=smtp.mail.com
```

JSON config:

```json
{
  "email": {
    "smtp_server": "%%SMTP_SERVER%%"
  }
}
```

Turinium will automatically resolve `%%SMTP_SERVER%%` using the value in the `.env` file.

### Database Services (DBServices)

`DBServices` provides a centralized interface to handle multiple databases and execute queries, functions, or stored procedures using simple, declarative configuration.

#### Registering Databases

```python
from turinium import DBServices as dbs

dbs.register_databases(app_config.get_config_block("databases"))
```

Example `databases` block in your config:

```json
{
  "main": {
    "type": "mssql",
    "server": "localhost",
    "database": "MyDatabase",
    "username": "sa",
    "password": "yourpassword",
    "driver": "ODBC Driver 17 for SQL Server"
  },
  "analytics": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "dbname": "AnalyticsDB",
    "user": "postgres",
    "password": "secret"
  }
}
```

#### Registering Services

```python
dbs.register_services(app_config.get_config_block("dbservices"))
```

Example `dbservices` block:

```json
{
  "GetClients": {
    "database": "main",
    "type": "procedure",
    "command": "usp_GetClients"
  },
  "SalesReport": {
    "database": "analytics",
    "type": "query",
    "command": "SELECT * FROM sales WHERE region = ? AND date > ?"
  }
}
```

#### Executing a Service

```python
success, df = dbs.exec_service("SalesReport", ("South", "2024-01-01"))
```

`df` will be a pandas DataFrame if successful, or `None` otherwise. Errors and return codes are automatically logged.

### Logging (TLogging)

`TLogging` enhances Python's built-in logging module with multi-destination support and structured output.

#### Initialization

```python
from turinium import TLogging

logger = TLogging(log_to=("console", "file", "json"), log_type="verbose")
```

#### Supported Outputs

* console: Logs printed to standard output.
* file: Logs written to a rotating file.
* json: Logs written to a JSON file for machine processing.

#### Logging Levels

```python
logger.debug("This is a debug message")
logger.info("Routine started")
logger.warning("Something looks suspicious")
logger.error("An error occurred")
logger.critical("Critical failure")
```

You can subclass or inject contextual loggers into different parts of the application to segment logs by subsystem.

### Email Sending (EmailSender)

`EmailSender` provides a simple interface to send HTML or plain-text emails with optional CC, BCC, and attachments.

#### Usage

```python
from turinium import EmailSender

smtp_info = {
  "smtp_server": "smtp.example.com",
  "sender_login": "user@example.com",
  "password": "yourpassword",
  "debug_level": 0
}

with EmailSender(
    smtp_info['smtp_server'],
    smtp_info['sender_login'],
    smtp_info['password'],
    smtp_info['debug_level']
) as email_sender:
    email_sender.send_email(
        to_list=["recipient@example.com"],
        subject="Weekly Report",
        html_message="<h1>Report Ready</h1><p>See attached report.</p>",
        text_message="Report Ready. Please see attached.",
        cc_list=["teamlead@example.com"],
        bcc_list=["auditor@example.com"]
    )
```

The `EmailSender` handles server connection and authentication behind the scenes.

## Contributing

We welcome contributions! To get involved:

1. Fork the repository on Git.
2. Create a feature or fix branch.
3. Make your changes with proper documentation and tests.
4. Submit a pull request.

Please follow the coding standards and provide clear commit messages.

## License

Turinium is licensed under the MIT License. See the LICENSE file for full details.
