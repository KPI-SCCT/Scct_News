# scrapers/r7_scraper.py
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

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

    def _normalize_url(self, href: str) -> str:
        """
        Normaliza URLs do R7:
        - converte URLs relativas para absolutas
        - remove espaços extras
        """
        href = (href or "").strip()
        if not href:
            return ""
        if href.startswith("/"):
            return urljoin(self.base_url, href)
        return href

    def fetch_from_url(
        self,
        url: str,
        uf: Optional[str] = None,
        limit: int = 150,
    ) -> List[NewsItem]:
        # Se tiver UF e a URL for o domínio base, ajusta para a página do estado
        if uf:
            slug = R7_STATE_SLUGS.get(uf.upper())
            base_domain = self.base_url.rstrip("/")
            # Se a URL for só o domínio base, troca pelo domínio do estado
            if slug and url.rstrip("/") in {base_domain, base_domain.replace("www.", "")}:
                url = f"{base_domain}/{slug}"

        logger.info("Buscando notícias R7 em %s (UF=%s)", url, uf or "-")

        try:
            html = get_page_html(
                url,
                # Mais tolerante: qualquer elemento com data-tb-title,
                # não só data-tb-title='true'
                wait_selector="[data-tb-title]",
                popup_handler=generic_popup_handler,
            )
        except Exception:
            logger.exception("Erro ao obter HTML do R7 em %s (UF=%s)", url, uf or "-")
            return []

        soup = BeautifulSoup(html, "html.parser")
        items: List[NewsItem] = []
        seen_urls: set[str] = set()

        # 1) Elementos "título" – em geral h3, mas pode ser outro tag
        title_nodes = soup.select("[data-tb-title]")
        logger.info(
            "R7: encontrados %d nós com data-tb-title em %s",
            len(title_nodes),
            url,
        )

        for node in title_nodes:
            # Caso o próprio elemento seja o <a> com href
            if node.name == "a" and node.get("href"):
                anchor = node
            else:
                anchor = node.find("a", href=True)

            if not anchor:
                continue

            href = self._normalize_url(anchor.get("href"))
            if not href:
                continue

            # Garante que é link de notícia do R7
            if "noticias.r7.com" not in href:
                continue

            if href in seen_urls:
                continue

            # Título: tenta title do <a>, depois do node, depois texto
            title = (
                anchor.get("title")
                or node.get("title")
                or anchor.get_text(strip=True)
                or node.get_text(strip=True)
            )
            if not title:
                continue

            title = title.strip()

            # Filtro bem leve para evitar lixo, mas não matar títulos curtos
            if len(title) < 8:
                continue

            seen_urls.add(href)

            items.append(
                NewsItem(
                    title=title,
                    url=href,
                    source=self.name,
                    published_at=datetime.utcnow(),  # se quiser, depois extraímos data real
                    uf=uf,
                )
            )

            if len(items) >= limit:
                break

        logger.info("R7: %d notícias válidas extraídas de %s", len(items), url)
        return items