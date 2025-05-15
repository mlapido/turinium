"""
Turinium - A Python framework to reduce boilerplate code.

This package provides utility functions for:
- Configuration management
- Database handling
- Email handling
- Logging

Author: Milton Lapido
License: MIT
"""

__version__ = "0.2.0"

# Configuration Management
from .config import AppConfig, SharedAppConfig

# Database Services
from .database import DBRouter, DBConnection, DBCredentials, DBServices

# Data Sources Services
from .datasources import FTPCredentials, FTPConnection, DataSourceServices

# Email
from .email import EmailSender

# Logging
from .logging import TLogging

__all__ = ["AppConfig", "SharedAppConfig", "DBRouter", "DBConnection", "DBCredentials", "DBServices", "EmailSender", "TLogging", "DataSourceServices", "FTPCredentials", "FTPConnection"]
