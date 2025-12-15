# export_for_streamlit.py
import os
import csv
from datetime import datetime
import subprocess
from pathlib import Path

from database import SessionLocal
from models import News

REPO_ROOT = Path(__file__).resolve().parent
DASHBOARD_CSV_PATH = REPO_ROOT / "dashboard" / "data" / "news_latest.csv"


def export_news_to_csv() -> int:
    """
    Exporta todas as notícias para dashboard/data/news_latest.csv.
    Retorna a quantidade de registros exportados.
    """
    DASHBOARD_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    session = SessionLocal()
    try:
        rows = (
            session.query(News)
            .order_by(News.published_at.desc().nullslast(), News.id.desc())
            .all()
        )

        with DASHBOARD_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")

            # Cabeçalho
            writer.writerow(
                [
                    "id",
                    "published_at",
                    "title",
                    "url",
                    "source",
                    "uf",
                    "city",
                    "category",
                ]
            )

            for n in rows:
                if n.published_at:
                    published_iso = n.published_at.isoformat()
                else:
                    published_iso = ""

                writer.writerow(
                    [
                        n.id,
                        published_iso,
                        (n.title or "").strip(),
                        n.url or "",
                        n.source or "",
                        n.uf or "",
                        n.city or "",
                        n.category or "",
                    ]
                )

        print(f"[export_for_streamlit] Exportados {len(rows)} registros para {DASHBOARD_CSV_PATH}")
        return len(rows)
    finally:
        session.close()


def git_commit_and_push(file_path: Path, message: str = "Atualiza export de notícias para dashboard"):
    """
    Executa git add/commit/push do arquivo informado.

    - Se não houver alterações (nothing to commit), não levanta erro.
    - Pressupõe que o repositório já está configurado com origin e credenciais salvas.
    """
    def run(cmd: str, check: bool = True, capture_output: bool = False):
        return subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            check=check,
            shell=True,
            capture_output=capture_output,
            text=True,
        )

    try:
        # Adiciona o arquivo
        run(f'git add "{file_path.as_posix()}"')

        # Verifica se há algo para commitar
        status = run("git status --porcelain", check=False, capture_output=True)
        if not status.stdout.strip():
            print("[export_for_streamlit] Nenhuma alteração detectada; commit/push ignorados.")
            return

        # Só faz commit se houver mudanças
        run(f'git commit -m "{message}"')
        run("git push")
        print("[export_for_streamlit] Commit e push executados com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"[export_for_streamlit] Falha ao executar git: {e}")

def export_news_to_csv_and_push():
    count = export_news_to_csv()
    if count > 0:
        git_commit_and_push(DASHBOARD_CSV_PATH)
    else:
        print("[export_for_streamlit] Nenhuma notícia para exportar; não foi feito commit.")


if __name__ == "__main__":
    # usar só export_news_to_csv() (e rodar git commit/push manual);
    # ou usar export_news_to_csv_and_push() se quiser automatizar.
    export_news_to_csv_and_push()