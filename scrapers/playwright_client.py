# scrapers/playwright_client.py
from typing import Optional, Callable
import logging

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
    Page,
)

logger = logging.getLogger(__name__)


def g1_popup_handler(page: Page) -> None:
    """Fecha popups conhecidos do G1 (feedback, notificações, etc.)."""
    # Popup de feedback (id que você informou)
    try:
        page.locator("#QSIFeedbackButton-close-btn").click(timeout=2000)
        logger.debug("Popup de feedback do G1 fechado.")
    except PlaywrightTimeoutError:
        logger.debug("Popup de feedback do G1 não apareceu.")
    except Exception:
        logger.debug("Erro ao fechar popup de feedback do G1.", exc_info=True)

    # Heurísticas para outros popups (notificações, etc.)
    candidates = [
        "button:has-text('Agora não')",
        "button:has-text('Não, obrigado')",
        "button:has-text('Não, obrigado!')",
        "button:has-text('Fechar')",
        "button[aria-label='Fechar']",
    ]
    for selector in candidates:
        try:
            page.locator(selector).first.click(timeout=1500)
            logger.debug("Popup extra fechado com seletor %s", selector)
            break
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue


def generic_popup_handler(page: Page) -> None:
    """Tentativa genérica de fechar popups (CNN, R7, etc.)."""
    selectors = [
        "button[aria-label='Fechar']",
        "button:has-text('Fechar')",
        "button:has-text('Fechar anúncio')",
        "button:has-text('Aceitar')",
        "button:has-text('Concordo')",
        "[role='dialog'] button",
    ]
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=1500)
            logger.debug("Popup genérico fechado com seletor %s", selector)
            break
        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue


def get_page_html(
    url: str,
    wait_selector: str | None = None,
    popup_handler=None,
    timeout_ms: int = 20000,
    headless: bool = True,
) -> str:
    """
    Navega até a URL com Playwright, trata popups opcionais e retorna o HTML.
    Em caso de erro de rede / timeout, loga e retorna string vazia.
    """
    html = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except (PlaywrightTimeoutError, PlaywrightError) as e:
                logger.error("Erro Playwright em %s: %s", url, e)
                return ""  # devolve vazio para o scraper tratar

            # Tenta fechar popups, se foi passado um handler
            if popup_handler:
                try:
                    popup_handler(page)
                except Exception as e:
                    logger.debug("Erro ao executar popup_handler em %s: %s", url, e)

            # Se o scraper pediu para esperar um seletor específico
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                except (PlaywrightTimeoutError, PlaywrightError) as e:
                    logger.debug("Timeout/erro ao esperar seletor '%s' em %s: %s", wait_selector, url, e)

            html = page.content()
        finally:
            browser.close()

    return html