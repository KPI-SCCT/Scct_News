# scrapers/r7_scraper.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, NewsItem
from .playwright_client import get_page_html, generic_popup_handler

logger = logging.getLogger(__name__)

R7_STATE_SLUGS = {
    "AC": "acre",
    "AL": "alagoas",
    "AP": "amapa",
    "AM": "amazonas",
    "BA": "bahia",
    "CE": "ceara",
    "DF": "distrito-federal",
    "ES": "espirito-santo",
    "GO": "goias",
    "MA": "maranhao",
    "MT": "mato-grosso",
    "MS": "mato-grosso-do-sul",
    "MG": "minas-gerais",
    "PA": "para",
    "PB": "paraiba",
    "PR": "parana",
    "PE": "pernambuco",
    "PI": "piaui",
    "RJ": "rio-de-janeiro",
    "RN": "rio-grande-do-norte",
    "RS": "rio-grande-do-sul",
    "RO": "rondonia",
    "RR": "roraima",
    "SC": "santa-catarina",
    "SP": "sao-paulo",
    "SE": "sergipe",
    "TO": "tocantins",
}


class R7Scraper(BaseScraper):
    name = "R7"
    base_url = "https://noticias.r7.com/"

    def fetch_from_url(
        self, url: str, uf: Optional[str] = None, limit: int = 150
    ) -> List[NewsItem]:
        # Se tiver UF, ajusta a URL para o formato de estado
        if uf:
            slug = R7_STATE_SLUGS.get(uf.upper())
            base_domain = self.base_url.rstrip("/")
            if slug and url.rstrip("/") in {base_domain, base_domain + ""}:
                url = f"{base_domain}/{slug}"

        logger.info("Buscando notícias R7 em %s", url)

        try:
            html = get_page_html(
                url,
                wait_selector="[data-tb-title='true']",
                popup_handler=generic_popup_handler,
            )
        except Exception as e:
            logger.warning("Nenhum HTML retornado de %s, UF=%s", url, uf or "N/A")
            return []

        soup = BeautifulSoup(html, "html.parser")
        items: List[NewsItem] = []
        seen_urls = set()

        for h in soup.select("[data-tb-title='true'] a[href^='https://noticias.r7.com/']"):
            href = h.get("href")
            if not href or href in seen_urls:
                continue

            title = h.get("title") or h.get_text(strip=True)
            if not title:
                continue

            if len(title) < 20:
                continue

            seen_urls.add(href)

            items.append(
                NewsItem(
                    title=title,
                    url=href,
                    source=self.name,
                    published_at=datetime.utcnow(),
                    uf=uf,
                )
            )

            if len(items) >= limit:
                break

        logger.info("R7: %d notícias em %s", len(items), url)
        return items
