import json
import logging
from pathlib import Path

from turinium.logging.logging import JSONHandler, TLogging


def test_tlogging_writes_json_log_to_json_folder(tmp_path, monkeypatch):
    """
    TLogging passes 'json/<name>.json' to JSONHandler; closing the handler must write exactly that file
    (it used to prefix './json' again and fail with 'json/json/<name>.json').
    """
    monkeypatch.chdir(tmp_path)
    logger = TLogging("t", log_filename="logs", log_to=("json",))
    logger.warning("something happened")
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)

    out = tmp_path / "json" / "logs.json"
    assert out.exists()
    assert not (tmp_path / "json" / "json").exists()
    data = json.loads(out.read_text())
    assert any("something happened" in msg for by_level in data.values() for msgs in by_level.values() for msg in msgs)


def test_json_handler_creates_missing_folder(tmp_path):
    target = tmp_path / "a" / "b" / "log.json"
    h = JSONHandler(target)
    h.emit(logging.LogRecord("x", logging.ERROR, __file__, 1, "boom", None, None))
    h.close()
    assert target.exists()
    assert "boom" in target.read_text()
