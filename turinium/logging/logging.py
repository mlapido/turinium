import os
import json
import logging
import colorlog
from pathlib import Path


import logging


def _safe_text_for_encoding(text: str, encoding: str) -> str:
    """Return a version of *text* that is guaranteed encodable in *encoding*.

    Workflow:
        1. Try to encode using the target encoding.
        2. If it fails, encode again using errors='backslashreplace' so characters that
           cannot be represented become escape sequences (e.g. '\\u2705').
        3. Decode back to str in the same encoding.

    This prevents StreamHandler.emit() from raising UnicodeEncodeError on Windows cp1252.

    Params:
        text: Original text that may contain non-encodable characters (e.g. emojis).
        encoding: The target stream encoding (e.g. 'cp1252', 'utf-8').

    Returns:
        A safe string that can be written to a stream using that encoding.
    """
    if not text:
        return text

    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, errors='backslashreplace').decode(encoding, errors='strict')


class SafeStreamHandler(logging.StreamHandler):
    """A StreamHandler that never crashes on UnicodeEncodeError.

    Notes:
        - PyCharm and some Windows consoles may use cp1252 even when Python is UTF-8 capable.
        - This handler guarantees logging doesn't emit '--- Logging error ---' blocks.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record, sanitizing the message if the stream can't encode it."""
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Determine the stream encoding; fallback to cp1252 because that's the common Windows case.
            stream = getattr(self, 'stream', None)
            encoding = getattr(stream, 'encoding', None) or 'cp1252'

            msg = record.getMessage()
            safe_msg = _safe_text_for_encoding(msg, encoding)

            # Rebuild the formatted output with the sanitized message.
            # We must not permanently mutate the record for other handlers (e.g. file handlers).
            original_msg = record.msg
            original_args = record.args
            try:
                record.msg = safe_msg
                record.args = ()
                super().emit(record)
            finally:
                record.msg = original_msg
                record.args = original_args


class JSONHandler(logging.Handler):
    """
    Custom logging handler to output logs in structured JSON format.
    Logs messages grouped by filename and severity level.
    """

    def __init__(self, filename):
        """
        Initialize the JSONHandler.

        :param filename: Path to the JSON log file.
        :type filename: str
        """
        super().__init__()
        self.filename = filename
        self.json_data = {}

    def emit(self, record):
        """
        Process and store the log message in JSON format.

        :param record: The log record.
        :type record: logging.LogRecord
        """
        try:
            file_being_processed = getattr(record, 'file_being_processed', 'unknown')
            msg = record.msg
            line_numbers = getattr(record, 'line_numbers', [])
            level = record.levelname

            if file_being_processed not in self.json_data:
                self.json_data[file_being_processed] = {}

            if level not in self.json_data[file_being_processed]:
                self.json_data[file_being_processed][level] = {}

            if msg not in self.json_data[file_being_processed][level]:
                self.json_data[file_being_processed][level][msg] = {'lines': []}

            if isinstance(line_numbers, list):
                self.json_data[file_being_processed][level][msg]['lines'].extend(line_numbers)
            else:
                self.json_data[file_being_processed][level][msg]['lines'].append(line_numbers)

        except Exception as e:
            print(f"Error in JSON logging: {e}")

    def get_json_data(self):
        """Return the current JSON log data."""
        return self.json_data

    def has_logged_to_json(self):
        """Check if any data has been logged to JSON."""
        return bool(self.json_data)

    def close(self):
        """Write the JSON log to disk upon closing."""
        try:
            json_dir = Path("./json")
            json_dir.mkdir(parents=True, exist_ok=True)
            with open(json_dir / self.filename, 'w') as f:
                json.dump(self.json_data, f, indent=4)
        except Exception as e:
            print(f"Error saving JSON log: {e}")
        super().close()


class TLogging(logging.Logger):
    """
    A custom logging class supporting console, file, and JSON-based logging.
    Uses structured logging and supports colorized console output.

    :param name: The logger name.
    :type name: str
    :param log_filename: The base filename for log files (without extension).
    :type log_filename: str, optional
    :param level: The logging level (default: NOTSET).
    :type level: int, optional
    :param log_to: A tuple specifying where logs should be written ('console', 'file', 'json').
    :type log_to: tuple[str], optional
    """

    def __init__(self, name, log_filename='logs', level=logging.NOTSET, log_to=('console', 'file', 'json')):
        super().__init__(name, level)

        log_dir = Path("./logs")
        json_dir = Path("./json")
        log_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        self.log_filename = log_dir / f"{log_filename}.log"
        self.json_filename = json_dir / f"{log_filename}.json"

        # Set up handlers based on log_to selection
        if 'console' in log_to:
            self.addHandler(self._create_console_handler())

        if 'file' in log_to:
            self.addHandler(self._create_file_handler())

        if 'json' in log_to:
            self.addHandler(JSONHandler(self.json_filename))

    def _create_console_handler(self):
        """Creates and returns a colorized console handler."""
        ch = SafeStreamHandler()

        color_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)s: %(message)s',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        )
        ch.setFormatter(color_formatter)
        return ch

    def _create_file_handler(self):
        """Creates and returns a file handler for logging to a file."""
        fh = logging.FileHandler(self.log_filename)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        return fh

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False,
             file_being_processed=None, line_numbers=None, **kwargs):
        """
        Logs a message with additional metadata such as filename and line numbers.

        :param level: The logging level.
        :param msg: The log message.
        :param args: Positional arguments.
        :param exc_info: Exception information.
        :param extra: Extra data for logging.
        :param stack_info: Whether to include stack info.
        :param file_being_processed: The filename associated with the log entry.
        :param line_numbers: Line numbers associated with the log entry.
        """
        if extra is None:
            extra = {}

        if file_being_processed:
            extra['file_being_processed'] = file_being_processed

        if line_numbers:
            extra['line_numbers'] = line_numbers

        super()._log(level, msg, args, exc_info, extra=extra, stack_info=stack_info)

    def get_json_data(self):
        """Retrieve JSON log data."""
        for handler in self.handlers:
            if isinstance(handler, JSONHandler):
                return handler.get_json_data()
        return None

    def was_logged_to_json(self):
        """Check if any logs were recorded in JSON format."""
        for handler in self.handlers:
            if isinstance(handler, JSONHandler):
                return handler.has_logged_to_json()
        return False

    def __enter__(self):
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point. Ensures logs are written before exit."""
        for handler in self.handlers:
            handler.close()
            self.removeHandler(handler)
        return False
