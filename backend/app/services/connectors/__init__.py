from app.services.connectors.base import ConnectorNotConfigured, SourceConnector
from app.services.connectors.sample import SampleListingsConnector

_REGISTRY: dict[str, SourceConnector] = {}


def register(c: SourceConnector) -> None:
    _REGISTRY[c.key] = c


register(SampleListingsConnector())


def all_connectors() -> list[SourceConnector]:
    return list(_REGISTRY.values())


def get_connector(key: str) -> SourceConnector | None:
    return _REGISTRY.get(key)


__all__ = ["SourceConnector", "ConnectorNotConfigured", "all_connectors", "get_connector", "register"]
