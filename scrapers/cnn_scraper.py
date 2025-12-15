# scrapers/cnn_scraper.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, NewsItem
from .playwright_client import get_page_html, generic_popup_handler

logger = logging.getLogger(__name__)


class CNNScraper(BaseScraper):
    name = "CNN Brasil"
    base_url = "https://www.cnnbrasil.com.br/"

    def fetch_from_url(
        self, url: str, uf: Optional[str] = None, limit: int = 150
    ) -> List[NewsItem]:
        
        if uf:
            base_domain = self.base_url.rstrip("/")  # https://www.cnnbrasil.com.br
            if url.rstrip("/") in {base_domain, base_domain + ""}:
                url = f"{base_domain}/{uf.lower()}/"

        logger.info("Buscando notícias CNN em %s", url)
        try:
            html = get_page_html(
                url,
                # Títulos importantes geralmente usam h2.font-bold
                wait_selector="h2.font-bold",
                popup_handler=generic_popup_handler,
            )
        except Exception as e:
            logger.warning("Nenhum HTML retornado de %s, UF=%s", url, uf or "N/A")
            return []

        soup = BeautifulSoup(html, "html.parser")
        items: List[NewsItem] = []
        seen_urls = set()

        # Pega links do domínio CNN com texto relevante
        for a in soup.select("a[href^='https://www.cnnbrasil.com.br/']"):
            href = a.get("href")
            if not href or href in seen_urls:
                continue

            title = a.get_text(strip=True)
            if not title:
                continue

            # Evita menu/rodapé: considera apenas textos um pouco maiores
            if len(title) < 20:
                continue

            seen_urls.add(href)

            items.append(
                NewsItem(
                    title=title,
                    url=href,
                    source=self.name,
                    published_at=datetime.utcnow(),  # se quiser, podemos refinar depois
                    uf=uf,
                )
            )

            if len(items) >= limit:
                break

        logger.info("CNN: %d notícias em %s", len(items), url)
        return items
