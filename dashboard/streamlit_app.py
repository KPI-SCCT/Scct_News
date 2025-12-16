import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dateutil import parser as dateparser

# Caminhos de dados/recursos
BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "news_latest.csv")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo_fedex.png")


def _load_data_internal(mtime: float) -> pd.DataFrame:
    """
    Função interna cacheada: recebe o mtime do arquivo CSV.
    Sempre que o mtime mudar, o cache é invalidado.
    """
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame(
            columns=["id", "published_at", "title", "url", "source", "uf", "city", "category"]
        )

    df = pd.read_csv(DATA_PATH, sep=";")

    # Converte published_at para datetime (onde não for vazio)
    if "published_at" in df.columns:
        df["published_at"] = df["published_at"].apply(
            lambda x: dateparser.parse(x) if isinstance(x, str) and x.strip() else pd.NaT
        )
        df["data"] = df["published_at"].dt.date
        df["hora"] = df["published_at"].dt.strftime("%H:%M").fillna("")
    else:
        df["data"] = pd.NaT
        df["hora"] = ""

    df["uf"] = df.get("uf", "").fillna("")
    df["source"] = df.get("source", "").fillna("")
    df["city"] = df.get("city", "").fillna("")
    df["title"] = df.get("title", "").fillna("")
    df["url"] = df.get("url", "").fillna("")

    return df


@st.cache_data
def load_data_cached(mtime: float) -> pd.DataFrame:
    """
    Wrapper cacheado em torno do loader interno.
    O argumento mtime é usado como chave de cache.
    """
    return _load_data_internal(mtime)


def load_data() -> pd.DataFrame:
    """
    Função que o restante da app usa.
    Ela calcula o mtime do CSV e delega para a função cacheada.
    """
    if os.path.exists(DATA_PATH):
        mtime = os.path.getmtime(DATA_PATH)
    else:
        mtime = 0.0
    return load_data_cached(mtime)


def inject_custom_css():
    """
    Injeta CSS para aplicar a paleta roxo + laranja e um layout mais moderno.
    """
    st.markdown(
        """
        <style>
        /* Fundo geral da aplicação */
        .stApp {
            background: linear-gradient(135deg, #f5f3ff 0%, #fff7f0 40%, #ffffff 100%);
        }

        /* Container principal */
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2.5rem;
            max-width: 1400px;
        }

        /* Título e subtítulo */
        .app-title {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
            color: #4D148C; /* roxo */
        }

        .app-subtitle {
            font-size: 0.95rem;
            color: #5f5f7a;
        }
        
        .filter-title {
            font-weight: 600;
            font-size: 0.95rem;
            color: #4D148C;
            margin-bottom: 0.6rem;
        }

        /* Métricas */
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 0.9rem 1.1rem;
            border-left: 4px solid #FF6600; /* laranja FedEx*/
            box-shadow: 0 6px 15px rgba(0,0,0,0.05);
        }
        .metric-label {
            font-size: 0.8rem;
            color: #77748f;
        }
        .metric-value {
            font-size: 1.4rem;
            font-weight: 700;
            color: #4D148C;
        }

        /* Botão de download */
        .stDownloadButton button {
            background: linear-gradient(135deg, #FF6600, #ff8b3d);
            color: white;
            border-radius: 999px;
            border: none;
            padding: 0.5rem 1.4rem;
            font-weight: 600;
            box-shadow: 0 8px 18px rgba(255,102,0,0.35);
        }
        .stDownloadButton button:hover {
            filter: brightness(1.05);
        }

        /* Tabela */
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            border: 1px solid rgba(77,20,140,0.08);
            box-shadow: 0 10px 25px rgba(0,0,0,0.04);
            background: white;
        }

        /* ---------- CARD DE FILTROS ---------- */
        /* Apenas o VerticalBlock cujo FILHO imediato é um ElementContainer
           que contém .filter-title (ou seja, o bloco de filtros) */
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .filter-title) {
            background: #ffffff;
            border-radius: 12px;
            padding: 1.2rem 1.4rem 0.8rem 1.4rem;
            border: 1px solid rgba(77,20,140,0.08);   /* borda geral suave */
            border-left: 4px solid #4D148C;           /* faixa roxa só no card */
            box-shadow: 0 10px 25px rgba(0,0,0,0.06);
            margin-bottom: 1rem;
        }

        .filter-title {
            font-weight: 600;
            font-size: 0.95rem;
            color: #4D148C;
            margin-bottom: 0.6rem;
        }
        /* ------------------------------------- */

        /* Labels dos filtros */
        label[data-testid="stMetricLabel"] {
            font-size: 0.85rem;
        }

        /* Ajusta labels dos inputs */
        .st-emotion-cache-16idsys p, .st-emotion-cache-1cypcdb p {
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """
    Renderiza header com logo (se existir) + título.
    """
    top = st.container()
    with top:
        col_logo, col_text = st.columns([1, 3])

        with col_logo:
            if os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=120)
            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)  # placeholder

        with col_text:
            st.markdown(
                '<div class="app-title">SCCT News – Monitor de Notícias</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="app-subtitle">'
                'Monitoramento centralizado'
                '</div>',
                unsafe_allow_html=True,
            )


def main():
    st.set_page_config(
        page_title="SCCT News Dashboard",
        page_icon="📰",
        layout="wide",
    )

    inject_custom_css()
    render_header()

    df = load_data()

    if df.empty:
        st.info("Nenhuma notícia disponível ainda. Aguarde o coletor atualizar o CSV.")
        return

    st.markdown("")

    # --------- Filtros em card ---------
    with st.container():

        st.markdown(
            '<div class="filter-title">Filtros</div>',
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)

        # UF
        with col1:
            uf_options = ["TODOS"] + sorted(
                [u for u in df["uf"].unique() if isinstance(u, str) and u.strip()]
            )
            uf_selected = st.selectbox("UF", uf_options, index=0, key="uf_filter")

        # Mídia
        with col2:
            media_options = ["TODAS"] + sorted(
                [m for m in df["source"].unique() if isinstance(m, str) and m.strip()]
            )
            media_selected = st.selectbox("Mídia", media_options, index=0, key="media_filter")

        # Data
        with col3:
            all_dates = df["data"].dropna().unique()
            all_dates_sorted = sorted(all_dates)
            if all_dates_sorted:
                date_selected = st.date_input(
                    "Data da reportagem",
                    value=None,
                    min_value=min(all_dates_sorted),
                    max_value=max(all_dates_sorted),
                    key="date_filter",
                )
            else:
                date_selected = None

    # --------- Aplicação dos filtros ---------
    filtered = df.copy()

    if uf_selected != "TODOS":
        filtered = filtered[filtered["uf"] == uf_selected]

    if media_selected != "TODAS":
        filtered = filtered[filtered["source"] == media_selected]

    if date_selected:
        filtered = filtered[filtered["data"] == date_selected]

    total_count = len(df)
    filtered_count = len(filtered)

    # --------- Métricas + botão de exportação ---------
    col_metric, col_btn = st.columns([2, 1])

    with col_metric:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Notícias exibidas</div>
                <div class="metric-value">{filtered_count}</div>
                <div class="metric-label">Total disponível: {total_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def to_csv_bytes(df_export: pd.DataFrame) -> bytes:
        out = df_export.copy()
        out = out.sort_values(by=["published_at", "id"], ascending=[False, False])
        return out.to_csv(index=False, sep=";").encode("utf-8-sig")

    with col_btn:
        st.download_button(
            label="Exportar CSV (filtro atual)",
            data=to_csv_bytes(filtered),
            file_name=f"noticias_filtradas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    st.markdown("")

    # --------- Tabela de resultados ---------
    cols_show = ["data", "hora", "title", "source", "uf", "city", "url"]
    cols_show = [c for c in cols_show if c in filtered.columns]

    st.dataframe(
        filtered[cols_show],
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
