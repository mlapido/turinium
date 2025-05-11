from abc import ABC, abstractmethod


class BaseValidator(ABC):
    """
    Abstract base class for file validation before database loading.

    Subclasses should implement `is_valid()` to return a boolean.
    """

    def __init__(self, file_path: str, file_type: str = None):
        """
        Initializes the validator with file path and optional type tag.

        :param file_path: Path to the file to validate.
        :param file_type: A short identifier for the kind of file (optional).
        """
        self.file_path = file_path
        self.file_type = file_type

    @abstractmethod
    def is_valid(self) -> bool:
        """
        Returns True if the file is considered valid and safe to process.

        :return: Boolean result of validation.
        """
        pass