# url_utils.py
from urllib.parse import urlparse
from typing import Optional


def infer_media_from_url(url: str) -> Optional[str]:
    netloc = urlparse(url).netloc.lower()
    if "g1.globo.com" in netloc:
        return "G1"
    if "cnnbrasil.com.br" in netloc:
        return "CNN Brasil"
    if "noticias.r7.com" in netloc:
        return "R7"
    return None


def infer_uf_from_url(url: str) -> Optional[str]:
    """
    Para G1 e CNN, tenta inferir a UF pela primeira parte do path:
    https://g1.globo.com/sp -> SP
    https://www.cnnbrasil.com.br/al/ -> AL
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return None

    first = path.split("/")[0]
    if len(first) == 2:
        return first.upper()

    return None
