# app.py
from datetime import datetime, timedelta
import csv
import io

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    Response
)

import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func

from config import TEMPLATES_DIR, STATIC_DIR
from database import SessionLocal, init_db
from models import News, MonitoredURL, Keyword
from monitor import run_monitor_cycle
from url_utils import infer_media_from_url, infer_uf_from_url

# Lista fixa de UFs (para filtro e formulários)
UF_LIST = [
    ("AC", "Acre"),
    ("AL", "Alagoas"),
    ("AP", "Amapá"),
    ("AM", "Amazonas"),
    ("BA", "Bahia"),
    ("CE", "Ceará"),
    ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"),
    ("GO", "Goiás"),
    ("MA", "Maranhão"),
    ("MT", "Mato Grosso"),
    ("MS", "Mato Grosso do Sul"),
    ("MG", "Minas Gerais"),
    ("PA", "Pará"),
    ("PB", "Paraíba"),
    ("PR", "Paraná"),
    ("PE", "Pernambuco"),
    ("PI", "Piauí"),
    ("RJ", "Rio de Janeiro"),
    ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"),
    ("RO", "Rondônia"),
    ("RR", "Roraima"),
    ("SC", "Santa Catarina"),
    ("SP", "São Paulo"),
    ("SE", "Sergipe"),
    ("TO", "Tocantins"),
]

MEDIA_SUGGESTIONS = ["G1", "CNN Brasil", "R7"]

def parse_flexible_date(date_str: str) -> datetime | None:
    """
    Tenta interpretar a data em formatos comuns:
    - dd/mm/aaaa  (ex.: 11/12/2025)
    - yyyy-mm-dd  (ex.: 2025-12-11, que é o que vem do <input type="date">)
    """
    if not date_str:
        return None

    s = date_str.strip()

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    return None

def build_news_query(session, uf, media, date_str):
    query = session.query(News)

    # UF
    if uf and uf != "TODOS":
        query = query.filter(News.uf == uf)

    # Mídia
    if media:
        query = query.filter(News.source == media)

    # Data única
    if date_str:
        base_date = parse_flexible_date(date_str)
        if base_date:
            next_day = base_date + timedelta(days=1)
            query = query.filter(
                News.published_at >= base_date,
                News.published_at < next_day,
            )

    return query

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
    )

    with app.app_context():
        init_db()

    # Agendador para rodar o monitor automaticamente a cada 30 minutos
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo", daemon=True)
    scheduler.add_job(run_monitor_cycle, "interval", minutes=30, id="news_monitor")

    # Evita duplicar o agendador no modo debug com reloader
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))

    # Dashboard principal
    @app.route("/", methods=["GET"])
    def index():
        session = SessionLocal()
        try:
            query = session.query(News)

            uf = request.args.get("uf") or None
            media = request.args.get("media") or None
            date_str = request.args.get("date") or None
            monitor_msg = request.args.get("monitor") or None

            # Filtro UF
            if uf and uf != "TODOS":
                query = query.filter(News.uf == uf)

            # Filtro Mídia
            if media:
                query = query.filter(News.source == media)

            # Filtro por data única
            selected_date_br = None  # só para exibir na tela se quiser no futuro
            if date_str:
                base_date = parse_flexible_date(date_str)
                if base_date:
                    next_day = base_date + timedelta(days=1)
                    query = query.filter(
                        News.published_at >= base_date,
                        News.published_at < next_day,
                    )
                    # versão BR apenas para exibição (se quisermos mostrar em algum lugar)
                    selected_date_br = base_date.strftime("%d/%m/%Y")

            base_query = build_news_query(session, uf, media, date_str)

            total_count = base_query.count()

            query = base_query.order_by(
                News.published_at.desc().nullslast(),
                News.id.desc(),
            )
            news_list = query.limit(500).all()

            medias = [m[0] for m in session.query(News.source).distinct().all()]

            return render_template(
                "index.html",
                news_list=news_list,
                medias=medias,
                uf_list=UF_LIST,
                selected_uf=uf or "TODOS",
                selected_media=media,
                selected_date=date_str,   # vai como veio na query (ISO), compatível com type="date"
                monitor_msg=monitor_msg,
                # se quiser exibir em algum lugar, está disponível:
                selected_date_br=selected_date_br,
                total_count=total_count,
            )
        finally:
            session.close()

    @app.route("/export", methods=["GET"])
    def export_news():
        session = SessionLocal()
        try:
            uf = request.args.get("uf") or None
            media = request.args.get("media") or None
            date_str = request.args.get("date") or None

            base_query = build_news_query(session, uf, media, date_str)
            query = base_query.order_by(
                News.published_at.desc().nullslast(),
                News.id.desc(),
            )
            rows = query.all()

            output = io.StringIO()
            writer = csv.writer(output, delimiter=";")

            # Cabeçalho
            writer.writerow(
                ["data", "hora", "titulo", "link", "fonte", "uf", "cidade", "categoria"]
            )

            for n in rows:
                if n.published_at:
                    data_br = n.published_at.strftime("%d/%m/%Y")
                    hora_br = n.published_at.strftime("%H:%M")
                else:
                    data_br = ""
                    hora_br = ""

                writer.writerow(
                    [
                        data_br,
                        hora_br,
                        (n.title or "").strip(),
                        n.url or "",
                        n.source or "",
                        n.uf or "",
                        n.city or "",
                        n.category or "",
                    ]
                )

            csv_data = output.getvalue()
            output.close()

            # Prefixo BOM para ajudar o Excel a reconhecer UTF-8 corretamente
            csv_data = "\ufeff" + csv_data

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"noticias_{timestamp}.csv"

            return Response(
                csv_data,
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                },
            )
        finally:
            session.close()

    # Status/healthcheck com métricas
    @app.route("/status", methods=["GET"])
    def status():
        session = SessionLocal()
        try:
            news_count = session.query(func.count(News.id)).scalar() or 0
            last_created = session.query(func.max(News.created_at)).scalar()
            last_published = session.query(func.max(News.published_at)).scalar()
            monitored_total = session.query(func.count(MonitoredURL.id)).scalar() or 0
            monitored_active = (
                session.query(func.count(MonitoredURL.id))
                .filter(MonitoredURL.is_active.is_(True))
                .scalar()
                or 0
            )
            keywords_active = (
                session.query(func.count(Keyword.id))
                .filter(Keyword.is_active.is_(True))
                .scalar()
                or 0
            )
        finally:
            session.close()

        return jsonify(
            {
                "status": "ok",
                "news_count": news_count,
                "last_created_at": last_created.isoformat()
                if last_created
                else None,
                "last_published_at": last_published.isoformat()
                if last_published
                else None,
                "monitored_urls_total": monitored_total,
                "monitored_urls_active": monitored_active,
                "keywords_active": keywords_active,
            }
        )

    # Rodar monitor manualmente
    @app.route("/run-monitor", methods=["POST"])
    def run_monitor():
        start = datetime.utcnow()
        run_monitor_cycle()
        duration = (datetime.utcnow() - start).total_seconds()
        return redirect(
            url_for(
                "index",
                monitor=f"Monitor executado em {duration:.1f} segundos.",
            )
        )

    # Configurar mídias (habilitar/desabilitar)
    @app.route("/media-settings", methods=["GET", "POST"])
    def media_settings():
        session = SessionLocal()
        try:
            if request.method == "POST":
                active_medias = set(request.form.getlist("media"))
                all_medias = [
                    m[0] for m in session.query(MonitoredURL.media).distinct().all()
                ]
                for media_name in all_medias:
                    is_active = media_name in active_medias
                    session.query(MonitoredURL).filter(
                        MonitoredURL.media == media_name
                    ).update({"is_active": is_active})
                session.commit()
                return redirect(url_for("media_settings"))

            medias_config = []
            for (media_name,) in session.query(MonitoredURL.media).distinct().all():
                active_count = (
                    session.query(MonitoredURL)
                    .filter(
                        MonitoredURL.media == media_name,
                        MonitoredURL.is_active.is_(True),
                    )
                    .count()
                )
                medias_config.append(
                    {
                        "name": media_name,
                        "active": active_count > 0,
                        "active_count": active_count,
                    }
                )

            return render_template("media_settings.html", medias=medias_config)
        finally:
            session.close()

    # ------- CRUD de URLs monitoradas -------

    @app.route("/urls", methods=["GET"])
    def url_list():
        session = SessionLocal()
        try:
            urls = (
                session.query(MonitoredURL)
                .order_by(MonitoredURL.media, MonitoredURL.uf, MonitoredURL.url)
                .all()
            )
            return render_template(
                "url_list.html",
                urls=urls,
                uf_list=UF_LIST,
            )
        finally:
            session.close()

    @app.route("/urls/new", methods=["GET", "POST"])
    def url_new():
        session = SessionLocal()
        try:
            if request.method == "POST":
                url_str = (request.form.get("url") or "").strip()
                media = (request.form.get("media") or "").strip()
                uf = request.form.get("uf") or ""
                city = (request.form.get("city") or "").strip()
                is_active = request.form.get("is_active") == "on"

                if not url_str:
                    # Poderia adicionar flash, mas por simplicidade só redireciona
                    return redirect(url_for("url_list"))

                # inferir mídia/UF se não informados
                if not media:
                    media = infer_media_from_url(url_str) or ""
                if not uf:
                    uf = infer_uf_from_url(url_str) or None
                else:
                    uf = uf if uf != "NONE" else None

                existing = session.query(MonitoredURL).filter_by(url=url_str).first()
                if existing:
                    existing.media = media
                    existing.uf = uf
                    existing.city = city or None
                    existing.is_active = is_active
                else:
                    new_url = MonitoredURL(
                        url=url_str,
                        media=media or "DESCONHECIDA",
                        uf=uf,
                        city=city or None,
                        is_active=is_active,
                    )
                    session.add(new_url)

                session.commit()
                return redirect(url_for("url_list"))

            return render_template(
                "url_form.html",
                form_title="Nova URL monitorada",
                submit_label="Salvar",
                url_obj=None,
                uf_list=UF_LIST,
                media_suggestions=MEDIA_SUGGESTIONS,
            )
        finally:
            session.close()

    @app.route("/urls/<int:url_id>/edit", methods=["GET", "POST"])
    def url_edit(url_id: int):
        session = SessionLocal()
        try:
            url_obj = session.get(MonitoredURL, url_id)
            if not url_obj:
                return redirect(url_for("url_list"))

            if request.method == "POST":
                url_str = (request.form.get("url") or "").strip()
                media = (request.form.get("media") or "").strip()
                uf = request.form.get("uf") or ""
                city = (request.form.get("city") or "").strip()
                is_active = request.form.get("is_active") == "on"

                if url_str:
                    url_obj.url = url_str

                if not media:
                    media = infer_media_from_url(url_str or url_obj.url) or url_obj.media
                url_obj.media = media

                if uf:
                    url_obj.uf = uf if uf != "NONE" else None
                else:
                    inferred_uf = infer_uf_from_url(url_str or url_obj.url)
                    url_obj.uf = inferred_uf or url_obj.uf

                url_obj.city = city or None
                url_obj.is_active = is_active

                session.commit()
                return redirect(url_for("url_list"))

            return render_template(
                "url_form.html",
                form_title="Editar URL monitorada",
                submit_label="Atualizar",
                url_obj=url_obj,
                uf_list=UF_LIST,
                media_suggestions=MEDIA_SUGGESTIONS,
            )
        finally:
            session.close()

    @app.route("/urls/<int:url_id>/delete", methods=["POST"])
    def url_delete(url_id: int):
        session = SessionLocal()
        try:
            url_obj = session.get(MonitoredURL, url_id)
            if url_obj:
                session.delete(url_obj)
                session.commit()
            return redirect(url_for("url_list"))
        finally:
            session.close()

    # ------- CRUD de Palavras-chave -------

    @app.route("/keywords", methods=["GET", "POST"])
    def keywords():
        session = SessionLocal()
        try:
            if request.method == "POST":
                term = (request.form.get("term") or "").strip()
                if term:
                    existing = session.query(Keyword).filter(
                        func.lower(Keyword.term) == term.lower()
                    ).first()
                    if not existing:
                        session.add(Keyword(term=term))
                        session.commit()
                return redirect(url_for("keywords"))

            keywords_list = (
                session.query(Keyword)
                .order_by(Keyword.is_active.desc(), Keyword.term.asc())
                .all()
            )
            return render_template("keywords.html", keywords=keywords_list)
        finally:
            session.close()

    @app.route("/keywords/<int:kw_id>/toggle", methods=["POST"])
    def keyword_toggle(kw_id: int):
        session = SessionLocal()
        try:
            kw = session.get(Keyword, kw_id)
            if kw:
                kw.is_active = not kw.is_active
                session.commit()
            return redirect(url_for("keywords"))
        finally:
            session.close()

    @app.route("/keywords/<int:kw_id>/delete", methods=["POST"])
    def keyword_delete(kw_id: int):
        session = SessionLocal()
        try:
            kw = session.get(Keyword, kw_id)
            if kw:
                session.delete(kw)
                session.commit()
            return redirect(url_for("keywords"))
        finally:
            session.close()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)