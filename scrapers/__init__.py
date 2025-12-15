# scrapers/__init__.py
from .base_scraper import (
    BaseScraper,
    NewsItem,
    get_scraper_classes,
    get_scraper_instances,
)

__all__ = ["BaseScraper", "NewsItem", "get_scraper_classes", "get_scraper_instances"]
