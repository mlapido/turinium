from turinium.config.app_config import AppConfig


class SharedAppConfig:
    """
    Named-instance factory for managing shared AppConfig instances.

    By default, returns or creates the instance named "_main_". Multiple named
    configurations are supported for more complex scenarios.

    Example:
        cfg = SharedAppConfig()  # returns '_main_'
        alt = SharedAppConfig(name="test", config_files="test.toml")
        assert SharedAppConfig() is cfg
    """

    _instances: dict[str, AppConfig] = {}

    def __new__(cls, config_files=None, env_file=None, name="_main_"):
        """
        Returns a shared AppConfig instance for the given name.

        If the instance does not exist, it is created using the provided arguments.

        :param config_files: Path(s) to config file(s) or folder.
        :type config_files: str | Path | list[str | Path] | None
        :param env_file: Optional path to an .env file.
        :type env_file: str | Path | None
        :param name: Logical name for this configuration context.
        :type name: str

        :return: A shared AppConfig instance.
        :rtype: AppConfig

        :raises TypeError: If name is not a string.
        """
        if not isinstance(name, str):
            raise TypeError("Instance name must be a string.")

        if name not in cls._instances:
            cls._instances[name] = AppConfig(config_files, env_file)

        return cls._instances[name]

    @classmethod
    def get(cls, name="_main_"):
        """
        Retrieves an AppConfig instance by name without creating it.

        :param name: The name of the instance to retrieve.
        :type name: str

        :return: The named AppConfig instance, or None if not found.
        :rtype: AppConfig | None
        """
        return cls._instances.get(name)

    @classmethod
    def get_all(cls):
        """
        Returns a dictionary of all currently cached AppConfig instances.

        :return: A dictionary mapping instance names to AppConfig objects.
        :rtype: dict[str, AppConfig]
        """
        return cls._instances.copy()

    @classmethod
    def reset(cls, name=None):
        """
        Clears stored instance(s) by name, or all if no name is given.

        :param name: Optional name of the instance to remove.
        :type name: str | None
        """
        if name is None:
            cls._instances.clear()
        else:
            cls._instances.pop(name, None)

    @classmethod
    def is_initialized(cls, name="_main_"):
        """
        Checks whether an AppConfig instance is already created for a given name.

        :param name: Name of the instance.
        :type name: str

        :return: True if the instance exists, False otherwise.
        :rtype: bool
        """
        return name in cls._instances

    @classmethod
    def describe(cls):
        """
        Returns a string summary of all configured instance names.

        :return: A human-readable description of current shared instances.
        :rtype: str
        """
        if not cls._instances:
            return "No AppConfig instances are currently registered."
        return "Registered AppConfig instances:\n" + "\n".join(
            f" - {name}" for name in sorted(cls._instances)
        )

    def __repr__(cls):
        return f"<SharedAppConfig: {len(cls._instances)} instance(s) cached>"
