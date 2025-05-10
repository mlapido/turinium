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

__version__ = "0.1.1"

# Configuration Management
from .config import AppConfig

# Database Services
from .database import DBRouter, DBConnection, DBCredentials, DBServices

# Email
from .email import EmailSender

# Logging
from .logging import TLogging

__all__ = ["AppConfig", "DBRouter", "DBConnection", "DBCredentials", "DBServices", "EmailSender", "TLogging"]
