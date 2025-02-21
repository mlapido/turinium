from setuptools import setup, find_packages
import os

# Read long description from README.md (if available)
long_description = ""
if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="turinium",
    version="0.1.0",
    author="Milton Lapido",
    author_email="milton.lapido@gmail.com",
    description=(
        "Turinium is a Python framework designed to streamline software "
        "development by reducing boilerplate code and providing utility "
        "functions for database connections, logging, error handling, "
        "and configuration management. Inspired by the pioneering work of "
        "Alan Turing, Turinium aims to empower intelligent systems for modern developers."
    ),
    long_description=long_description,  # Use README.md for PyPI if available
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/turinium",  # Change this to the actual GitHub repo if available
    license="MIT",
    packages=find_packages(include=["turinium*"]),  # Only include the turinium package and its submodules
    python_requires=">=3.8",  # Ensures minimum Python version compatibility
    install_requires=[
        "pyyaml",  # YAML support
        "toml",  # TOML support
        "python-dotenv",  # Env file support
        "colorlog",  # Colored console logging
        "sqlalchemy"
    ],
    extras_require={
        "database": ["sqlalchemy", "pyodbc", "psycopg2-binary"],
        "cli": ["click"],
        "testing": ["pytest", "pytest-cov"],  # Optional testing dependencies
        "dev": ["black", "flake8", "mypy"],  # Development tools
    },
    include_package_data=True,  # Include non-code files (e.g., config files)
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="software development, utilities, database, logging, configuration, python framework",
)
