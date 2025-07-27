# app/domain.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ServerSettings:
    host: str
    port: int


@dataclass
class EmailSettings:
    username: str
    password: str
    smtp: str = "smtp.default.com"


@dataclass
class SubBlock:
    name: str
    age: int
    nested: Optional['SubBlock'] = None  # Recursive for test_third_level


@dataclass
class WrapperBlock:
    sub: SubBlock


@dataclass
class ItemBlock:
    name: str
    value: int


@dataclass
class ContainerWithList:
    items: List[ItemBlock]
