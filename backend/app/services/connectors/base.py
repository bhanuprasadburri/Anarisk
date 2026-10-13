"""Connector abstraction for AUTHORIZED public-source integrations (social platform APIs, app-store data
providers, certificate-transparency feeds, ...).

To add a live source: subclass SourceConnector, set kind=SourceKind.CONNECTOR, implement `is_configured()`
(check credentials), `collect()` (return NormalizedEntity items using only data you are permitted to access) and
register it in `connectors/__init__.py`. Entities it returns are stored with provenance=COLLECTED.
No live connector ships enabled in this repository because no credentials or data-sharing agreements exist.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models import Brand
from app.models.enums import Provenance, SourceKind
from app.services.ingestion import NormalizedEntity


class ConnectorNotConfigured(Exception):
    pass


class SourceConnector(ABC):
    key: str
    name: str
    kind: SourceKind
    description: str = ""
    live: bool = False  # True only for connectors that really read an external system

    @property
    def provenance(self) -> Provenance:
        return {SourceKind.CONNECTOR: Provenance.COLLECTED, SourceKind.SYNTHETIC: Provenance.SYNTHETIC, SourceKind.MANUAL: Provenance.MANUAL}[self.kind]

    @abstractmethod
    def is_configured(self) -> bool: ...

    def configuration_help(self) -> str | None:
        return None

    @abstractmethod
    def collect(self, brand: Brand, query: dict[str, Any]) -> list[NormalizedEntity]: ...
