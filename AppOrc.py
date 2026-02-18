1) AppOrc.py (SUBSTITUA o seu inteiro por este)

import socket
from datetime import datetime

import gspread
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials


# -----------------------------
# Config
# -----------------------------
APP_TITLE = "Orçamento de Projetos"
SPREADSHEET_NAME = "Orçamento de Projetos"
WORKSHEET_TITLE = None  # None = primeira aba (sheet1). Se quiser, coloque o nome exato da aba.

REQUIRED_COLUMNS = ["Data", "Projeto", "Valor", "Percentual", "Status"]

# evita “pendurar” em chamadas de rede e causar 503 no health-check
socket.setdefaulttimeout(20)


# -----------------------------
# Page config + basic styling
# -----------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
/* remove um pouco da "cara" padrão */
.block-container { padding-top: 1.2rem; padding-bottom: 2.0rem; }
h1, h2, h3 { letter-spacing: -0.02em; }
.small-muted { color: rgba(255,255,255,0.65); font-size: 0.9rem; }

/* cards simples */
.card {
  border-radius: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04);
  backdrop-filter: blur(6px);
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# Google Sheets helpers
# -----------------------------
def _require_secrets():
    if "gcp_service_account" not in st.secrets:
        st.error(
            "Secrets não encontrados: `gcp_service_account`.\n\n"
            "No Streamlit Cloud: Settings -> Secrets e cole seu JSON da Service Account no formato TOML."
        )
        st.stop()


@st.cache_resource
def get_gspread_client():
    _require_secrets()

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope,
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=120, show_spinner=False)
def load_data(spreadsheet_name: str, worksheet_title: str | None):
    client = get_gspread_client()

    sh = client.open(spreadsheet_name)
    if worksheet_title:
        ws = sh.worksheet(worksheet_title)
    else:
        ws = sh.sheet1

    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df


def coerce_and_validate(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(
            "A planilha não tem as colunas esperadas.\n\n"
            f"Faltando: {missing}\n\n"
            f"Colunas encontradas: {list(df.columns)}"
        )
        st.stop()

    # tipos
    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
    df["Percentual"] = pd.to_numeric(df["Percentual"], errors="coerce")

    # normalizações simples
    df["Projeto"] = df["Projeto"].astype(str).fillna("")
    df["Status"] = df["Status"].astype(str).fillna("")

    return df


# -----------------------------
# Header
# -----------------------------
left, right = st.columns([0.7, 0.3], vertical_alignment="center")

with left:
    st.title("📊 Orçamento de Projetos")
    st.markdown(
        '<div class="small-muted">Dados puxados diretamente do Google Sheets</div>',
        unsafe_allow_html=True,
    )

with right:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Atualizar agora", use_container_width=True):
            # limpa cache do dataframe e recarrega
            st.cache_data.clear()
            st.rerun()
    with c2:
        st.caption(f"⏱️ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

st.markdown("---")


# -----------------------------
# Load + guard (mostra erro real)
# -----------------------------
try:
    with st.spinner("conectando e carregando dados..."):
        df_raw = load_data(SPREADSHEET_NAME, WORKSHEET_TITLE)
        df = coerce_and_validate(df_raw)
except Exception as e:
    st.error(
        "Falha ao carregar dados do Google Sheets.\n\n"
        "Principais causas: secrets ausentes, planilha não compartilhada com a service account, "
        "nome da planilha/aba errado, ou timeout de rede."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("Nenhum dado encontrado na planilha.")
    st.stop()


# -----------------------------
# Sidebar filters
# -----------------------------
with st.sidebar:
    st.header("Filtros")

    projetos = sorted(df["Projeto"].dropna().unique().tolist())
    projeto_selecionado = st.multiselect(
        "Selecione o Projeto:",
        projetos,
        default=projetos,
    )

    # datas seguras
    data_min = df["Data"].min()
    data_max = df["Data"].max()

    if pd.isna(data_min) or pd.isna(data_max):
        st.warning("Coluna Data com valores inválidos. Verifique o formato dd/mm/aaaa.")
        data_inicio = st.date_input("Data Início:", value=datetime.now().date())
        data_fim = st.date_input("Data Fim:", value=datetime.now().date())
    else:
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início:", value=data_min.date())
        with col2:
            data_fim = st.date_input("Data Fim:", value=data_max.date())

    status_options = sorted(df["Status"].dropna().unique().tolist())
    status_selecionado = st.multiselect(
        "Selecione o Status:",
        status_options,
        default=status_options,
    )


# -----------------------------
# Apply filters
# -----------------------------
df_filtered = df[
    (df["Projeto"].isin(projeto_selecionado))
    & (df["Data"] >= pd.Timestamp(data_inicio))
    & (df["Data"] <= pd.Timestamp(data_fim))
    & (df["Status"].isin(status_selecionado))
].copy()


# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4 = st.columns(4)

total_valor = float(df_filtered["Valor"].sum(skipna=True)) if not df_filtered.empty else 0.0
total_projetos = int(df_filtered["Projeto"].nunique()) if not df_filtered.empty else 0
percentual_medio = float(df_filtered["Percentual"].mean(skipna=True)) if not df_filtered.empty else 0.0

with k1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Total Orçado", f"R$ {total_valor:,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

with k2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Total de Projetos", total_projetos)
    st.markdown("</div>", unsafe_allow_html=True)

with k3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Percentual Médio", f"{percentual_medio:.1f}%")
    st.markdown("</div>", unsafe_allow_html=True)

with k4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.metric("Registros Filtrados", len(df_filtered))
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")


# -----------------------------
# Charts
# -----------------------------
c1, c2 = st.columns(2)

with c1:
    if df_filtered.empty:
        st.info("Sem dados com os filtros atuais.")
    else:
        tmp = df_filtered.groupby("Projeto", as_index=False)["Valor"].sum()
        fig1 = px.bar(
            tmp,
            x="Projeto",
            y="Valor",
            title="Orçamento por Projeto",
            labels={"Valor": "Valor (R$)", "Projeto": "Projeto"},
        )
        fig1.update_layout(height=420, showlegend=False)
        st.plotly_chart(fig1, width="stretch")

with c2:
    if df_filtered.empty:
        st.info("Sem dados com os filtros atuais.")
    else:
        vc = df_filtered["Status"].value_counts().reset_index()
        vc.columns = ["Status", "count"]
        fig2 = px.pie(
            vc,
            values="count",
            names="Status",
            title="Distribuição por Status",
        )
        fig2.update_layout(height=420)
        st.plotly_chart(fig2, width="stretch")


# -----------------------------
# Table + download
# -----------------------------
st.subheader("Detalhes dos Registros")

cols_show = ["Data", "Projeto", "Valor", "Percentual", "Status"]
table_df = (
    df_filtered[cols_show]
    .sort_values("Data", ascending=False)
    .reset_index(drop=True)
)

st.dataframe(
    table_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
        "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
        "Percentual": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

csv_bytes = table_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "baixar csv (filtrado)",
    data=csv_bytes,
    file_name="orcamento_projetos_filtrado.csv",
    mime="text/csv",
    width="content",
)

st.markdown("---")
st.caption("Se aparecer 503 /script-health-check no Cloud, normalmente é travamento em rede/secrets. Esta versão força timeout e mostra o erro real.")

