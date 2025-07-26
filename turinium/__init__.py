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

__version__ = "0.3.0"

# Configuration Management
from .config import AppConfig, SharedAppConfig

# Database Services
from .database import DBRouter, DBConnection, DBCredentials, DBServices

# Data Sources Services - deprecated
from .datasources import FTPCredentials, FTPConnection, DataSourceServices

# Storage Services - Replaces Data Sources Services
from .storage import StorageServices

# Email
from .email import EmailSender

# Logging
from .logging import TLogging

__all__ = ["AppConfig", "SharedAppConfig", "DBRouter", "DBConnection", "DBCredentials", "DBServices", "EmailSender", "TLogging", "DataSourceServices", "FTPCredentials", "FTPConnection"]
