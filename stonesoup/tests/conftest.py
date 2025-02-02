import pytest

from ..base import Base, prop


class _TestBase(Base):
    property_a: int = prop()
    property_b: str = prop()
    property_c: int = prop(default=123)


@pytest.fixture(scope='session')
def base():
    return _TestBase
