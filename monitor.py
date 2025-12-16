# monitor.py
from __future__ import annotations

from sqlalchemy.exc import IntegrityError

import logging
import threading
from typing import Iterable, List, Tuple, Optional

from config import SCRAPER_LOG_FILE
from database import SessionLocal
from models import News, MonitoredURL, Keyword
from scrapers import NewsItem, get_scraper_classes
from url_utils import infer_uf_from_url

from concurrent.futures import ThreadPoolExecutor, as_completed

from export_for_streamlit import export_news_to_csv

# ----------------- Configuração de log -----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(SCRAPER_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Mapeia mídia -> classe de scraper (G1, CNN Brasil, R7, etc.)
SCRAPER_CLASSES = get_scraper_classes()

# Lista de UFs brasileiras (para expandir G1/CNN/R7 quando uf for None)
UF_CODES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


# ----------------- Palavras-chave -----------------

def _get_active_keywords() -> List[str]:
    session = SessionLocal()
    try:
        rows = session.query(Keyword).filter(Keyword.is_active.is_(True)).all()
        return [k.term for k in rows]
    finally:
        session.close()


def _filter_by_keywords(items: Iterable[NewsItem], keywords: List[str]) -> List[NewsItem]:
    """
    - Se não houver nenhuma palavra-chave ativa: traz TODAS as notícias.
    - Caso contrário: só traz notícias cujo título ou resumo contenham
      pelo menos uma das palavras-chave (case-insensitive).
    """
    if not keywords:
        return list(items)

    lowered_keywords = [k.lower() for k in keywords]
    filtered: List[NewsItem] = []

    for item in items:
        haystack = ((item.title or "") + " " + (item.summary or "")).lower()
        if any(kw in haystack for kw in lowered_keywords):
            filtered.append(item)

    return filtered


# ----------------- Expansão por UF -----------------

def _expand_targets_for_monitored(
    monitored: MonitoredURL,
) -> List[Tuple[str, str, Optional[str], Optional[str]]]:
    """
    Gera uma lista de alvos (media, url, uf, city) a partir de uma MonitoredURL.

    Regras:
    - G1/CNN Brasil/R7 com uf=None -> cria um alvo por UF (AC, AL, ..., TO)
    - G1/CNN Brasil/R7 com uf=XX  -> cria apenas um alvo com essa UF
    - Demais mídias:
        - se uf definida -> um alvo com essa UF
        - se uf None     -> tenta inferir UF pela URL; senão deixa None mesmo
    """
    media = monitored.media
    url = monitored.url
    uf = monitored.uf
    city = monitored.city

    targets: List[Tuple[str, str, Optional[str], Optional[str]]] = []

    if media in ("G1", "CNN Brasil", "R7"):
        # Portais nacionais
        if uf:
            # UF definida = roda só esse estado
            targets.append((media, url, uf, city))
        else:
            # UF None = queremos rodar para TODOS os estados
            for uf_code in UF_CODES:
                targets.append((media, url, uf_code, city))
    else:
        # Sites locais ou outras mídias
        uf_effective = uf or infer_uf_from_url(url)
        targets.append((media, url, uf_effective, city))

    return targets


# ----------------- Persistência -----------------

def save_news_items(
    items: Iterable[NewsItem],
    default_city: Optional[str] = None,
    default_uf: Optional[str] = None,
) -> None:
    """
    Salva notícias no banco.

    - Usa a constraint UNIQUE(url) como proteção principal contra duplicatas.
    - Commit item a item, tratando IntegrityError (duplicatas) sem derrubar o monitor.
    """
    session = SessionLocal()
    try:
        for item in items:
            if not item.url:
                continue

            news = News(
                title=item.title,
                url=item.url,
                summary=item.summary,
                source=item.source,
                # evita gravar string "None" – usa None de verdade
                city=item.city or (default_city if default_city not in ("", "None") else None),
                uf=item.uf or (default_uf if default_uf not in ("", "None") else None),
                category=item.category,
                published_at=item.published_at,
            )

            session.add(news)
            try:
                session.commit()
            except IntegrityError:
                # URL já existe: desfaz essa transação e segue o jogo
                session.rollback()
                logger.debug("Notícia duplicada ignorada (UNIQUE url): %s", item.url)
            except Exception as e:
                session.rollback()
                logger.error("Erro ao salvar notícia %s: %s", item.url, e)
                # Aqui podemos optar por continuar ou re-levantar.
                # Como é caso inesperado, vamos re-levantar:
                raise
    finally:
        session.close()


# ----------------- Execução de scrapers -----------------

def _run_scraper_target(
    media: str,
    url: str,
    uf: Optional[str],
    city: Optional[str],
    keywords: List[str],
) -> None:
    """
    Executa um scraper para uma combinação específica:
    (mídia, url, uf, city).

    Ex:
    - ("G1", "https://g1.globo.com/", "SP", None)
    - ("CNN Brasil", "https://www.cnnbrasil.com.br/", "AL", None)
    - ("Jornal Local", "https://jornallocal.com.br/", "PR", "Curitiba")
    """
    scraper_cls = SCRAPER_CLASSES.get(media)
    if not scraper_cls:
        logger.error("Nenhum scraper registrado para a mídia '%s'", media)
        return

    scraper = scraper_cls()

    try:
        uf_log = uf or "N/A"
        logger.info("Executando scraper %s em %s (UF=%s)", media, url, uf_log)

        items = scraper.fetch_from_url(url, uf=uf)
        logger.info("Mídia %s (%s, UF=%s): %d itens brutos", media, url, uf_log, len(items))

        filtered_items = _filter_by_keywords(items, keywords)
        logger.info(
            "Mídia %s (%s, UF=%s): %d itens após filtro de palavras-chave",
            media,
            url,
            uf_log,
            len(filtered_items),
        )

        save_news_items(filtered_items, default_city=city, default_uf=uf)
    except Exception as e:
        logger.exception(
            "Erro ao executar scraper %s para URL %s (UF=%s): %s",
            media,
            url,
            uf_log,
            e,
        )


# ----------------- Ciclo de monitoramento -----------------

def run_monitor_cycle(max_workers: int = 6) -> None:
    """
    Executa um ciclo de monitoramento:
    - Carrega URLs monitoradas ativas
    - Expande os alvos por UF (G1/CNN/R7 -> todos os estados, se uf=None)
    - Coleta palavras-chave ativas
    - Roda cada alvo em um pool de threads (concorrência limitada)
    """
    session = SessionLocal()
    try:
        monitored_urls = (
            session.query(MonitoredURL)
            .filter(MonitoredURL.is_active.is_(True))
            .all()
        )
    finally:
        session.close()

    if not monitored_urls:
        logger.warning("Nenhuma URL monitorada ativa encontrada.")
        return

    # Expande os alvos por UF
    targets: List[Tuple[str, str, Optional[str], Optional[str]]] = []
    for mon in monitored_urls:
        targets.extend(_expand_targets_for_monitored(mon))

    keywords = _get_active_keywords()

    logger.info(
        "Iniciando ciclo de monitoramento. %d URLs monitoradas geraram %d alvos (mídia+UF), %d palavras-chave ativas.",
        len(monitored_urls),
        len(targets),
        len(keywords),
    )

    # Pool de threads, em vez de 1 thread por alvo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for media, url, uf, city in targets:
            futures.append(
                executor.submit(
                    _run_scraper_target,
                    media,
                    url,
                    uf,
                    city,
                    keywords,
                )
            )

        for fut in as_completed(futures):
            # Se der erro dentro do _run_scraper_target, tratamos aqui tb
            try:
                fut.result()
            except Exception:
                logger.exception("Erro inesperado em um alvo de scraping.")

    logger.info("Ciclo de monitoramento concluído.")

    try:
        export_news_to_csv()
    except Exception:
        logger.exception("Falha ao exportar CSV para o dashboard.")
    else:
        logger.info("CSV exportado com sucesso (sem commit/push automático).")


if __name__ == "__main__":
    run_monitor_cycle()
