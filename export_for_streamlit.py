# export_for_streamlit.py
# export_for_streamlit.py
from pathlib import Path
from datetime import datetime
import csv

from database import SessionLocal
from models import News

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "dashboard" / "data" / "news_latest.csv"


def export_news_to_csv() -> Path:
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
        writer.writerow(
            ["id", "published_at", "title", "url", "source", "uf", "city", "category"]
        )

        for n in rows:
            ts = (
                n.published_at.strftime("%Y-%m-%d %H:%M:%S")
                if n.published_at
                else ""
            )
            writer.writerow([
                n.id,
                ts,
                (n.title or "").strip(),
                n.url or "",
                n.source or "",
                n.uf or "",
                n.city or "",
                n.category or "",
            ])

    print(f"[export_for_streamlit] Exportados {len(rows)} registros para {CSV_PATH}")
    return CSV_PATH


if __name__ == "__main__":
    export_news_to_csv()
