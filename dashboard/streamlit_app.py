# dashboard/streamlit_app.py
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dateutil import parser as dateparser

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "news_latest.csv")


@st.cache_data
def load_data() -> pd.DataFrame:
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

    return df


def main():
    st.set_page_config(page_title="SCCT News Dashboard", layout="wide")

    st.title("Monitor de Notícias – SCCT News (Dashboard)")

    df = load_data()

    if df.empty:
        st.info("Nenhuma notícia disponível ainda. Aguarde o coletor atualizar o CSV.")
        return

    # --------- Filtros ---------
    col1, col2, col3 = st.columns(3)

    # UF
    with col1:
        uf_options = ["TODOS"] + sorted(
            [u for u in df["uf"].unique() if isinstance(u, str) and u.strip()]
        )
        uf_selected = st.selectbox("UF", uf_options, index=0)

    # Mídia
    with col2:
        media_options = ["TODAS"] + sorted(
            [m for m in df["source"].unique() if isinstance(m, str) and m.strip()]
        )
        media_selected = st.selectbox("Mídia", media_options, index=0)

    # Data
    with col3:
        all_dates = df["data"].dropna().unique()
        all_dates_sorted = sorted(all_dates)
        date_selected = st.date_input(
            "Data da reportagem",
            value=None,
            min_value=min(all_dates_sorted) if all_dates_sorted else None,
            max_value=max(all_dates_sorted) if all_dates_sorted else None,
        )

    filtered = df.copy()

    if uf_selected != "TODOS":
        filtered = filtered[filtered["uf"] == uf_selected]

    if media_selected != "TODAS":
        filtered = filtered[filtered["source"] == media_selected]

    if date_selected:
        filtered = filtered[filtered["data"] == date_selected]

    total_count = len(df)
    filtered_count = len(filtered)

    st.markdown(f"**Mostrando {filtered_count} de {total_count} notícias**")

    # --------- Botão de exportar CSV filtrado ---------
    def to_csv_bytes(df_export: pd.DataFrame) -> bytes:
        out = df_export.copy()
        out = out.sort_values(by=["published_at", "id"], ascending=[False, False])
        return out.to_csv(index=False, sep=";").encode("utf-8-sig")

    st.download_button(
        label="Exportar CSV (filtro atual)",
        data=to_csv_bytes(filtered),
        file_name=f"noticias_filtradas_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

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
