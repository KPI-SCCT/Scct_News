# export_for_streamlit.py
# export_for_streamlit.py
from pathlib import Path
from datetime import datetime
import csv

from database import SessionLocal
from models import News

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "dashboard" / "data" / "news_latest.csv"


def export_news_to_csv() -> tuple[Path, bool]:
    """
    Exporta todas as notícias da tabela News para o CSV usado pelo dashboard.

    Retorna:
      (CSV_PATH, changed)
      - changed = True se o conteúdo do arquivo mudou em relação à versão anterior.
    """
    # Conteúdo anterior (se existir) para comparar
    old_bytes = CSV_PATH.read_bytes() if CSV_PATH.exists() else None

    session = SessionLocal()
    try:
        rows = (
            session.query(News)
            .order_by(News.published_at.desc().nullslast(), News.id.desc())
            .all()
        )
    finally:
        session.close()

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        # Cabeçalho compatível com o streamlit_app.py
        writer.writerow(
            ["id", "published_at", "title", "url", "source", "uf", "city", "category"]
        )

        for n in rows:
            if n.published_at:
                ts = n.published_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                ts = ""

            writer.writerow(
                [
                    n.id,
                    ts,
                    (n.title or "").strip(),
                    n.url or "",
                    n.source or "",
                    n.uf or "",
                    n.city or "",
                    n.category or "",
                ]
            )

    new_bytes = CSV_PATH.read_bytes()
    changed = (old_bytes != new_bytes)

    print(
        f"[export_for_streamlit] Exportados {len(rows)} registros para {CSV_PATH} "
        f"(changed={changed})"
    )
    return CSV_PATH, changed


if __name__ == "__main__":
    path, changed = export_news_to_csv()
    if changed:
        print("\n>>> CSV atualizado. Lembre-se de fazer COMMIT + PUSH no VS Code.\n")
    else:
        print("\n>>> CSV regravado, mas sem mudanças em relação à versão anterior.\n")
