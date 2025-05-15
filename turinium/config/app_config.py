import os
import json
import toml
import yaml
import argparse
import re

from dotenv import load_dotenv
from pathlib import Path


class AppConfig:
    """
    A flexible configuration manager for JSON, TOML, and YAML files, environment variables,
    and command-line arguments. It can also merge multiple config files if a list of paths
    is provided.

    It supports loading from a single file, a list of files, or a folder containing supported
    config files. Environment variables are loaded from a .env file (if present), and any
    placeholders in the config (e.g. %%VAR_NAME%%) are resolved. Command-line arguments can
    also be parsed and injected based on definitions within the config.

    Supported extensions: .json, .toml, .yaml, .yml
    """

    def __init__(self, config_files=None, env_file=None):
        """
        Constructor for AppConfig. Loads configuration from the specified files (or auto-detected
        `config.ext`), then loads environment variables, resolves placeholders, and parses any
        command-line arguments defined in the config.

        :param config_files: A file path, a directory path, or a list of either.
        :type config_files: str | Path | list[str | Path], optional
        :param env_file: Path to an optional .env file, defaults to ".env".
        :type env_file: str | Path, optional

        :raises FileNotFoundError: If no config files are found or valid.
        :raises ValueError: If a file has an unsupported extension or parsing fails.
        """
        self.config_data = {}
        self.config_files = self._resolve_config_files(config_files)
        self.env_file_path = Path(env_file) if env_file else Path(".env")

        self._load_config_from_files()
        self._load_env_vars()
        self._resolve_env_placeholders(self.config_data)
        self._handle_cmd_line_params()

    def _resolve_config_files(self, config_files):
        """
        Resolves the config files to load, validating extensions and flattening directories if needed.

        :param config_files: Input path(s) from constructor (file, folder, or list).
        :type config_files: str | Path | list[str | Path] | None

        :return: A list of Path objects pointing to config files to be loaded.
        :rtype: list[Path]

        :raises FileNotFoundError: If no valid config files are found.
        :raises ValueError: If a file has an unsupported extension.
        """
        exts = {'.json', '.toml', '.yml', '.yaml'}
        resolved_files = []

        def valid_config_file(path: Path):
            return path.is_file() and path.suffix.lower() in exts

        def scan_and_add(pathlike):
            path = Path(pathlike).resolve()
            if path.is_dir():
                for child in sorted(path.iterdir()):
                    if valid_config_file(child):
                        resolved_files.append(child)
            elif valid_config_file(path):
                resolved_files.append(path)
            else:
                raise ValueError(f"Unsupported config file or path: {path}")

        if config_files is None:
            # auto-detect in current directory
            for ext in exts:
                candidate = Path.cwd() / f"config{ext}"
                if candidate.exists():
                    resolved_files.append(candidate.resolve())
        elif isinstance(config_files, (str, Path)):
            scan_and_add(config_files)
        elif isinstance(config_files, list):
            for item in config_files:
                scan_and_add(item)
        else:
            raise TypeError("config_files must be a path, list of paths, or None")

        if not resolved_files:
            raise FileNotFoundError("No configuration file(s) found or valid.")

        return resolved_files
    def _load_config_from_files(self):
        """
        Iterates over all resolved config files, loading and merging them into `self.config_data`.
        """
        for config_file in self.config_files:
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_file}")

            try:
                with config_file.open("r", encoding="utf-8") as f:
                    new_data = self._parse_config_file(f, config_file.suffix)
                    self._merge_dicts(self.config_data, new_data)
            except Exception as e:
                raise ValueError(f"Error loading config file {config_file}: {e}")

    def _parse_config_file(self, file_obj, file_suffix):
        """
        Parses a single config file (JSON/TOML/YAML) and returns its dictionary data.

        :param file_obj: An opened file-like object.
        :type file_obj: typing.IO
        :param file_suffix: The file extension (e.g., ".json", ".toml", ".yaml").
        :type file_suffix: str
        :return: Parsed configuration data.
        :rtype: dict
        :raises ValueError: If the file suffix is unsupported.
        """
        if file_suffix == ".json":
            return json.load(file_obj)
        elif file_suffix == ".toml":
            return toml.load(file_obj)
        elif file_suffix in [".yml", ".yaml"]:
            return yaml.safe_load(file_obj)
        else:
            raise ValueError(f"Unsupported config format: {file_suffix}")

    def _merge_dicts(self, base, new):
        """
        Recursively merges the `new` dictionary into the `base` dictionary.

        :param base: The base dictionary to merge into.
        :type base: dict
        :param new: The new dictionary whose keys/values will be merged into `base`.
        :type new: dict
        """
        for key, value in new.items():
            if (key in base and isinstance(base[key], dict)
                    and isinstance(value, dict)):
                self._merge_dicts(base[key], value)
            else:
                base[key] = value

    def _load_env_vars(self):
        """
        Loads environment variables from a .env file (if it exists), merging them
        into `self.config_data`.

        - Uses `.` to define block nesting (e.g., `DB.Host` → `config_data["DB"]["Host"]`).
        - Standalone variables are placed inside the `"Env_Vars"` block.
        - If a value is enclosed in `{}`, it's parsed as JSON and treated as a full block.

        Example .env:
            DB.Host=localhost
            DB.Port=5432
            API_Key=secret123
            AWS_Credentials={"access_key": "ABC", "secret_key": "XYZ"}

        Results in:
            {
                "DB": {
                    "Host": "localhost",
                    "Port": "5432"
                },
                "Env_Vars": {
                    "API_Key": "secret123"
                },
                "AWS_Credentials": {
                    "access_key": "ABC",
                    "secret_key": "XYZ"
                }
            }
        """
        if not self.env_file_path.exists():
            return  # No .env file found, skip

        load_dotenv(self.env_file_path)

        for key, value in os.environ.items():
            # Handle JSON-like blocks (values inside `{}` become full objects)
            if value.startswith("{") and value.endswith("}"):
                try:
                    self.config_data[key] = json.loads(value)
                    continue  # Skip further processing since it's a full block
                except json.JSONDecodeError:
                    pass  # Ignore errors and treat as a regular string

            # Handle key with `.` notation for nesting
            parts = key.split(".", 1)
            if len(parts) == 2:
                block_name, key_name = parts
                if block_name not in self.config_data:
                    self.config_data[block_name] = {}
                self.config_data[block_name][key_name] = value
            else:
                # Place standalone variables in "Env_Vars"
                if "Env_Vars" not in self.config_data:
                    self.config_data["Env_Vars"] = {}
                self.config_data["Env_Vars"][key] = value

    def _resolve_env_placeholders(self, data):
        """
        Recursively traverses the configuration structure and replaces values
        matching the pattern %%ENV_VAR%% with their actual environment variable value.

        :param data: The config data dictionary (possibly nested).
        :type data: dict
        """
        for key, value in data.items():
            if isinstance(value, dict):
                self._resolve_env_placeholders(value)
            elif isinstance(value, list):
                for i in range(len(value)):
                    if isinstance(value[i], dict):
                        self._resolve_env_placeholders(value[i])
                    elif isinstance(value[i], str):
                        value[i] = self._resolve_placeholder_string(value[i])
            elif isinstance(value, str):
                data[key] = self._resolve_placeholder_string(value)

    def _resolve_placeholder_string(self, value):
        """
        Replaces a string formatted as %%ENV_VAR%% with the corresponding value from
        the environment variables. If not matched or not set, the original string is returned.

        :param value: The string to evaluate.
        :type value: str
        :return: The environment-substituted string if matched, or the original string.
        :rtype: str
        """
        match = re.fullmatch(r"%%([A-Z0-9_]+)%%", value)
        if match:
            env_var = match.group(1)
            return os.getenv(env_var, value)
        return value

    def _handle_cmd_line_params(self):
        """
        Dynamically parses command-line arguments if `cmd_line_params` is found
        in the loaded config data. Each parameter in `cmd_line_params["Parameters"]`
        is passed to `argparse.ArgumentParser.add_argument()`.
        """
        if "cmd_line_params" not in self.config_data:
            return

        cmd_section = self.config_data["cmd_line_params"]
        if not isinstance(cmd_section, dict):
            return

        parser = argparse.ArgumentParser(description=cmd_section.get("Description", "Command-line arguments"))
        param_list = cmd_section.get("Parameters", [])
        if not isinstance(param_list, list):
            return

        for param in param_list:
            name_or_flag = param.pop("name_or_flag", None)
            if name_or_flag:
                parser.add_argument(name_or_flag, **param)

        args = parser.parse_args()
        self.config_data["cmd_line_params"]["Arguments"] = vars(args)

    def get_config_block(self, block_name):
        """
        Retrieves a configuration block by name.

        :param block_name: The name of the block to retrieve.
        :type block_name: str
        :return: The dictionary block if found, else an empty dict.
        :rtype: dict
        """
        return self.config_data.get(block_name, {})

    def get_config_value(self, key, block_name=None):
        """
        Retrieves a specific configuration value from a block or top-level.

        :param key: The key to retrieve from the configuration.
        :type key: str
        :param block_name: The name of the block, if any. Defaults to None for top-level.
        :type block_name: str, optional
        :return: The value if found, else None.
        """
        if block_name:
            block = self.config_data.get(block_name, {})
            return block.get(key)
        return self.config_data.get(key)

    def set_config_block(self, block_name, block, method=0):
        """
        Sets or updates a configuration block with the specified method.

        :param block_name: The name of the block to set or update.
        :type block_name: str
        :param block: The new block data (dict or list).
        :type block: dict or list
        :param method: The update method:
            * 0: Update (merge) if existing block is a dict, else replace.
            * 1: Append if existing block is a list, else replace.
            * 2: Replace block entirely.
        :type method: int
        :raises ValueError: If method is invalid or block type is incompatible.
        """
        if method not in [0, 1, 2]:
            raise ValueError("Invalid method. Use 0 (update), 1 (append), or 2 (replace).")

        existing_block = self.config_data.get(block_name)
        if method == 0:
            # Update dictionary
            if existing_block is None:
                # If block doesn't exist, just set it
                self.config_data[block_name] = block
            elif isinstance(existing_block, dict):
                if not isinstance(block, dict):
                    raise ValueError(f"Cannot update dict with non-dict for block '{block_name}'.")
                existing_block.update(block)
            else:
                # If it's not a dict, replace it
                self.config_data[block_name] = block
        elif method == 1:
            # Append to list
            if existing_block is None:
                self.config_data[block_name] = [block] if not isinstance(block, list) else block
            elif isinstance(existing_block, list):
                if isinstance(block, list):
                    existing_block.extend(block)
                else:
                    existing_block.append(block)
            else:
                # If it's not a list, replace it
                self.config_data[block_name] = block
        else:
            # method == 2 => Replace entire block
            self.config_data[block_name] = block

    def set_config_block_from_file(self, file_path, block_name=None, method=0):
        """
        Loads configuration data from an external file (JSON/TOML/YAML) and sets it into
        the specified block using a chosen method.

        :param file_path: Path to the external config file.
        :type file_path: str
        :param block_name: The block name to store data under. Defaults to the file stem if not given.
        :type block_name: str, optional
        :param method: The update method (0=update, 1=append, 2=replace).
        :type method: int, optional
        :raises ValueError: If the external file format is unsupported or has parse errors.
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Block source file not found: {file_path_obj}")

        with file_path_obj.open("r", encoding="utf-8") as f:
            new_data = self._parse_config_file(f, file_path_obj.suffix)

        if not block_name:
            block_name = file_path_obj.stem

        self.set_config_block(block_name, new_data, method)

    def save_config(self, file_path=None):
        """
        Saves the current configuration data back to disk. If multiple config files
        were originally loaded, only the **first** one is updated unless a different
        file_path is specified.

        :param file_path: Optional path to save the config. If None, uses the first loaded file.
        :type file_path: str, optional
        :raises ValueError: If the file format is unsupported.
        """
        if file_path:
            target = Path(file_path)
            suffix = target.suffix.lower()
        else:
            target = self.config_files[0]
            suffix = target.suffix.lower()

        with target.open("w", encoding="utf-8") as f:
            if suffix == ".json":
                json.dump(self.config_data, f, indent=4)
            elif suffix == ".toml":
                toml.dump(self.config_data, f)
            elif suffix in [".yml", ".yaml"]:
                yaml.safe_dump(self.config_data, f)
            else:
                raise ValueError(f"Unsupported config format: {suffix}")
