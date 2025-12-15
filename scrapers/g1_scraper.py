# scrapers/g1_scraper.py
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, NewsItem
from .playwright_client import get_page_html, g1_popup_handler

logger = logging.getLogger(__name__)


def _parse_g1_datetime(text: str) -> datetime:
    """
    Converte strings como 'Há 1 hora' ou '09/12/2025 09h43' em datetime.
    Fallback: datetime.utcnow().
    """
    now = datetime.utcnow()
    if not text:
        return now

    text = text.strip().lower()

    # Formatos relativos
    if text.startswith("há "):
        m = re.search(r"(\d+)\s+hora", text)
        if m:
            return now - timedelta(hours=int(m.group(1)))
        m = re.search(r"(\d+)\s+minuto", text)
        if m:
            return now - timedelta(minutes=int(m.group(1)))
        return now

    # Formato absoluto dd/mm/aaaa hh[h]mm
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s*(\d{2})?h?(\d{2})?", text)
    if m:
        date_str = m.group(1)
        hour = int(m.group(2) or 0)
        minute = int(m.group(3) or 0)
        day, month, year = map(int, date_str.split("/"))
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            return now

    return now


class G1Scraper(BaseScraper):
    name = "G1"
    base_url = "https://g1.globo.com/"

    def fetch_from_url(
        self, url: str, uf: Optional[str] = None, limit: int = 100
    ) -> List[NewsItem]:
        
        # Se vier a URL base + UF, redireciona para /uf
        if uf:
            base_domain = self.base_url.rstrip("/")  # https://g1.globo.com
            if url.rstrip("/") in {base_domain, base_domain + ""}:
                url = f"{base_domain}/{uf.lower()}"

        logger.info("Buscando notícias G1 em %s", url)
        try:
            html = get_page_html(
                url,
                wait_selector="div.feed-post-body",   # estrutura que você mostrou
                popup_handler=g1_popup_handler,
            )
        except Exception as e:
            logger.warning("Nenhum HTML retornado de %s, UF=%s", url, uf or "N/A")
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.feed-post-body")
        items: List[NewsItem] = []
        seen_urls = set()

        for card in cards:
            link_tag = card.select_one("a.feed-post-link")
            if not link_tag:
                continue

            link = link_tag.get("href")
            if not link or link in seen_urls:
                continue
            seen_urls.add(link)

            title = link_tag.get_text(strip=True)
            if not title:
                continue

            summary_tag = card.select_one("div.feed-post-body-resumo")
            summary = summary_tag.get_text(strip=True) if summary_tag else None

            dt_tag = card.select_one("span.feed-post-datetime")
            published_at = (
                _parse_g1_datetime(dt_tag.get_text(strip=True))
                if dt_tag
                else datetime.utcnow()
            )

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    source=self.name,
                    summary=summary,
                    published_at=published_at,
                    uf=uf,
                )
            )

            if len(items) >= limit:
                break

        logger.info("G1: %d notícias em %s", len(items), url)
        return items
