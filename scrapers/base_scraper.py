# scrapers/base_scraper.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Type
import logging
import pkgutil
import importlib
import scrapers  # pacote atual

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    city: Optional[str] = None
    uf: Optional[str] = None
    category: Optional[str] = None


_SCRAPER_REGISTRY: Dict[str, Type["BaseScraper"]] = {}


class BaseScraper(ABC):
    """
    Classe base para todos os scrapers.
    Qualquer subclasse é registrada automaticamente via __init_subclass__.
    """

    name: str  # Ex: "G1", "R7", "CNN Brasil"
    base_url: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if getattr(cls, "name", None):
            if cls.name in _SCRAPER_REGISTRY:
                logger.warning("Scraper %s já registrado. Sobrescrevendo.", cls.name)
            _SCRAPER_REGISTRY[cls.name] = cls

    @abstractmethod
    def fetch_from_url(
        self, url: str, uf: Optional[str] = None, limit: int = 100
    ) -> List[NewsItem]:
        """Retorna notícias a partir de uma URL específica."""
        raise NotImplementedError

    def fetch_latest(self, limit: int = 100) -> List[NewsItem]:
        """Atalho para buscar na base_url padrão."""
        return self.fetch_from_url(self.base_url, limit=limit)


def _auto_discover_scrapers() -> None:
    """
    Importa dinamicamente todos os módulos em scrapers/ para que as subclasses
    de BaseScraper sejam registradas.
    """
    for module_info in pkgutil.iter_modules(scrapers.__path__):
        if module_info.name in {"base_scraper", "__init__"}:
            continue
        importlib.import_module(f"{scrapers.__name__}.{module_info.name}")


def get_scraper_classes() -> Dict[str, Type[BaseScraper]]:
    _auto_discover_scrapers()
    return dict(_SCRAPER_REGISTRY)


def get_scraper_instances() -> List[BaseScraper]:
    return [cls() for cls in get_scraper_classes().values()]
