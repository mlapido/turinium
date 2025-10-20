import pytest
import os
from turinium import AppConfig, MissingDataClassError, DataClassInstantiationError


@pytest.fixture
def config_path():
    """
    Fixture that returns a function for resolving paths to config files located
    in the testdata directory. Ensures all tests can consistently access sample files.
    """
    base_dir = os.path.dirname(__file__)
    def _resolve(filename: str) -> str:
        return os.path.join(base_dir, "testdata", filename)
    return _resolve


def test_json5_takes_precedence(tmp_path):
    """
    Tests that when both a config.json and a config.json5 file are present
    in the same directory, the AppConfig loader gives precedence to the
    .json5 file over the .json file.

    This simulates a real-world scenario where both versions of the same
    config may exist (e.g., one human-edited and one auto-generated),
    and ensures consistent and predictable loading behavior.

    The test uses `tmp_path` to isolate filesystem state and avoid polluting
    or being affected by the project's testdata folder.
    """
    # Create two files with the same base name but different extensions.
    json5_file = tmp_path / "config.json5"
    json_file = tmp_path / "config.json"

    # Write a valid config.json5 file with the correct dataclass mapping.
    # This version SHOULD be loaded, because it has higher precedence.
    json5_file.write_text("""
    {
      server: {
        to_dataclass: "tests.app_config.fixtures.domain.sample_classes.ServerSettings",
        host: "localhost",
        port: 8080
      },
      email: {
        address: "john.doe@gmail.com"
      }
    }
    """)

    # Write a config.json file with conflicting content.
    # If this one were loaded instead, the test would fail.
    json_file.write_text("""
    {
      "server": {
        "host": "should-be-ignored",
        "port": 1234
      }
    }
    """)

    # Pass the temp directory to AppConfig. The loader will search for
    # supported files in the folder. It should pick config.json5 first.
    config = AppConfig(config_files=[tmp_path])

    # Verify that the .json5 file was indeed loaded.
    server = config.get_config_block("server")
    assert server.host == "localhost"
    assert server.port == 8080


def test_get_config_block_returns_dict(config_path):
    """
    Ensures that blocks not mapped to dataclasses are returned as standard dictionaries.
    """
    config = AppConfig(config_files=[config_path("email_as_dict.json5")])
    block = config.get_config_block("email")
    assert isinstance(block, dict)
    assert block["address"] == "john.doe@gmail.com"


def test_get_config_class_returns_dataclass(config_path):
    """
    Verifies that a block with a `to_dataclass` mapping is returned as an instantiated dataclass.
    """
    config = AppConfig(config_files=[config_path("config.json5")])
    server = config.get_config_block("server")
    assert server.__class__.__name__ == "ServerSettings"
    assert server.port == 8080


def test_missing_get_config_block_returns_empty_dict(config_path):
    """
    Ensures that accessing a non-existent block returns an empty dictionary.
    """
    config = AppConfig(config_files=[config_path("config.json5")])
    assert config.get_config_block("ftp-server") == {}


@pytest.mark.parametrize("filename,expected_exception", [
    ("missing_class.json5", MissingDataClassError),
    ("invalid_class.json5", MissingDataClassError),
    ("bad_args.json5", DataClassInstantiationError),
    ("incorrect_instantiation.json5", DataClassInstantiationError),
    ("missing_list_attribute.json5", DataClassInstantiationError),
    ("invalid_list_attribute.json5", DataClassInstantiationError),
])
def test_invalid_dataclass_config_raises(config_path, filename, expected_exception):
    """
    Parametrized test that ensures invalid or malformed `to_dataclass` or `to_dataclass_list`
    mappings raise the appropriate exceptions.

    This includes:
    - missing or incorrect class references
    - incorrect or missing list usage in to_dataclass_list
    - failure to instantiate due to missing required fields
    """
    config_file = config_path(filename)
    with pytest.raises(expected_exception):
        AppConfig(config_files=[config_file])


def test_nested_to_dataclass(config_path):
    """
    Tests that a block containing a nested `to_dataclass` definition correctly converts to a nested dataclass structure.

    Scenario:
        - email_setup is a regular dict
        - email_setup["email"] is an EmailSettings dataclass
    """
    config = AppConfig(config_files=[config_path("nested_block.json5")])
    email_setup = config.get_config_block("email_setup")

    # The outer block should remain a dict
    assert isinstance(email_setup, dict)

    # The inner block should be a dataclass
    email = email_setup['email']
    assert email.__class__.__name__ == "EmailSettings"
    assert email.username == "user@example.com"
    assert email.password == "securepass"
    assert email.smtp == "smtp.example.com"


def test_list_of_dataclass_blocks(config_path):
    """
    Tests that lists of blocks using `to_dataclass_list` are converted into lists of dataclass instances.
    """
    config = AppConfig(config_files=[config_path("container_list.json5")])
    container = config.get_config_block("container")
    assert container.__class__.__name__ == "ContainerWithList"
    assert isinstance(container.items, list)
    assert len(container.items) == 2
    assert container.items[0].name == "John"
    assert container.items[0].value == 1
    assert container.items[1].name == "Jane"
    assert container.items[1].value == 2


def test_deeply_nested_dataclass(config_path):
    """
    Verifies that multiple layers of nested dataclass blocks are correctly instantiated.
    """
    config = AppConfig(config_files=[config_path("nested_subblock.json5")])
    wrapper = config.get_config_block("wrapper")
    assert wrapper.__class__.__name__ == "WrapperBlock"
    assert wrapper.sub.name == "Outer"
    assert wrapper.sub.age == 50
    assert wrapper.sub.nested.name == "Inner"
    assert wrapper.sub.nested.age == 25
