import pytest
from turinium import AppConfig, MissingDataClassError, DataClassInstantiationError


@pytest.fixture
def sample_config_files(tmp_path):
    """Creates both .json5 and .json files; .json5 should take precedence."""
    json5_file = tmp_path / "config.json5"
    json_file = tmp_path / "config.json"

    json5_file.write_text("""
    {
      server: {
        to_dataclass: "tests.fixtures.domain.sample_classes.ServerSettings",
        host: "localhost",
        port: 8080
      },
      email: {
        address: "john.doe@gmail.com",
      }
    }
    """)

    json_file.write_text("""
    {
      "server": {
        "host": "should-be-ignored",
        "port": 1234
      }
    }
    """)

    return tmp_path


def test_json5_takes_precedence(sample_config_files):
    config = AppConfig(config_files=sample_config_files)
    server = config.get_config_block("server")
    assert server.host == "localhost"
    assert server.port == 8080


def test_get_config_block_returns_dict(sample_config_files):
    config = AppConfig(config_files=sample_config_files)
    block = config.get_config_block("email")
    assert isinstance(block, dict)
    assert block["address"] == "john.doe@gmail.com"


def test_get_config_class_returns_dataclass(sample_config_files):
    config = AppConfig(config_files=sample_config_files)
    server = config.get_config_block("server")
    assert server.__class__.__name__ == "ServerSettings"
    assert server.port == 8080


def test_missing_class_raises(tmp_path):
    file = tmp_path / "invalid_class.json5"
    file.write_text("""
    {
      broken: {
        to_dataclass: "tests.fixtures.domain.sample_classes.DoesNotExist",
        some: "value"
      }
    }
    """)
    with pytest.raises(MissingDataClassError):
        AppConfig(config_files=[file])


def test_instantiation_failure_raises(tmp_path):
    file = tmp_path / "bad_args.json5"
    file.write_text("""
    {
      server: {
        to_dataclass: "tests.fixtures.domain.sample_classes.ServerSettings",
        host: "localhost"
      }
    }
    """)
    with pytest.raises(DataClassInstantiationError):
        AppConfig(config_files=[file])


def test_missing_get_config_block_returns_empty_dict(sample_config_files):
    config = AppConfig(config_files=sample_config_files)
    assert config.get_config_block("ftp-server") == {} # not defined in this config


# Scenario: Nested to_dataclass in regular block
def test_nested_to_dataclass(tmp_path):
    file = tmp_path / "nested_block.json5"
    file.write_text("""
    {
      email_setup: {
        email: {
          to_dataclass: "tests.fixtures.domain.sample_classes.EmailSettings",
          username: "user@example.com",
          password: "securepass",
          smtp: "smtp.example.com"
        }
      }
    }
    """)
    config = AppConfig(config_files=[file])
    email_setup = config.get_config_block("email_setup")
    assert isinstance(email_setup, dict)
    email = email_setup['email']
    assert email.__class__.__name__ == "EmailSettings"
    assert email.username == "user@example.com"
    assert email.password == "securepass"
    assert email.smtp == "smtp.example.com"

# Scenario: List of dataclass items within a dataclass (ContainerWithList / ItemBlock)
def test_list_of_dataclass_blocks(tmp_path):
    file = tmp_path / "container_list.json5"
    file.write_text("""
    {
      container: {
        to_dataclass: "tests.fixtures.domain.sample_classes.ContainerWithList",
        items: {
          to_dataclass_list: "tests.fixtures.domain.sample_classes.ItemBlock",
          list: [
            { "name": "John", "value": 1 },
            { "name": "Jane", "value": 2 }
          ]
        }
      }
    }
    """)
    config = AppConfig(config_files=[file])
    container = config.get_config_block("container")
    assert container.__class__.__name__ == "ContainerWithList"
    assert isinstance(container.items, list)
    assert len(container.items) == 2
    assert container.items[0].name == "John"
    assert container.items[0].value == 1
    assert container.items[1].name == "Jane"
    assert container.items[1].value == 2

# Scenario: Deeply nested dataclass (SubBlock within WrapperBlock)
def test_deeply_nested_dataclass(tmp_path):
    file = tmp_path / "nested_subblock.json5"
    file.write_text("""
    {
      wrapper: {
        to_dataclass: "tests.fixtures.domain.sample_classes.WrapperBlock",
        sub: {
          to_dataclass: "tests.fixtures.domain.sample_classes.SubBlock",
          name: "Outer",
          age: 50,
          nested: {
            to_dataclass: "tests.fixtures.domain.sample_classes.SubBlock",
            name: "Inner",
            age: 25
          }
        }
      }
    }
    """)
    config = AppConfig(config_files=[file])
    wrapper = config.get_config_block("wrapper")
    assert wrapper.__class__.__name__ == "WrapperBlock"
    assert wrapper.sub.name == "Outer"
    assert wrapper.sub.age == 50
    assert wrapper.sub.nested.name == "Inner"
    assert wrapper.sub.nested.age == 25

# Scenario: Missing or incorrect class path
def test_missing_class_path_raises(tmp_path):
    file = tmp_path / "missing_class.json5"
    file.write_text("""
    {
      invalid: {
        to_dataclass: "tests.fixtures.domain.sample_classes.DoesNotExist",
        value: 42
      }
    }
    """)
    with pytest.raises(MissingDataClassError):
        AppConfig(config_files=[file])

# Scenario: Incorrect instantiation (missing required fields)
def test_incorrect_instantiation_raises(tmp_path):
    file = tmp_path / "incorrect_instantiation.json5"
    file.write_text("""
    {
      invalid: {
        to_dataclass: "tests.fixtures.domain.sample_classes.ServerSettings",
        host: "localhost"
      }
    }
    """)
    with pytest.raises(DataClassInstantiationError):
        AppConfig(config_files=[file])

# Scenario: Incorrect "to_dataclass_list" usage (list not provided)
def test_to_dataclass_list_missing_list_attribute(tmp_path):
    file = tmp_path / "missing_list_attribute.json5"
    file.write_text("""
    {
      invalid_list: {
        to_dataclass_list: "tests.fixtures.domain.sample_classes.ItemBlock"
      }
    }
    """)
    with pytest.raises(DataClassInstantiationError):
        AppConfig(config_files=[file])

# Scenario: "to_dataclass_list" provided but "list" not an actual list
def test_to_dataclass_list_not_list(tmp_path):
    file = tmp_path / "invalid_list_attribute.json5"
    file.write_text("""
    {
      invalid_list: {
        to_dataclass_list: "tests.fixtures.domain.sample_classes.ItemBlock",
        list: { "name": "John", "value": 1 }
      }
    }
    """)
    with pytest.raises(DataClassInstantiationError):
        AppConfig(config_files=[file])