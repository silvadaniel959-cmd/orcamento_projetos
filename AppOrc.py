"""
Controle Orçamentário v6.2 (revisado)
====================================
Streamlit + Google Sheets

Inclui:
- Tela "Acesso Restrito" (senha) antes de abrir tudo (igual ao print)
- carregar_dados sempre retorna 3 DataFrames
- Conversão moeda BR robusta (vectorizada)
- Mes_Num garantido + ordenações sem KeyError
- Exclusão segura por Lanc_ID (batch_update)
- Cache buster via session_state (sem st.cache_data.clear())
"""

import streamlit as st
import streamlit.components.v1 as components  # (mantém disponível se quiser usar HTML via iframe)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import gspread
import json
import os
import math
import numpy as np
import uuid
from typing import List, Tuple, Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. CONFIGURAÇÃO GERAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(
    page_title="Controle Orçamentário",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. CSS GLOBAL + CSS TELA DE LOGIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown(
    """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    /* ══════════ Reset & Base ══════════ */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                     "Inter", "Helvetica Neue", Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
    }

    /* ══════════ FUNDO BRANCO ══════════ */
    .stApp, .stApp > header, [data-testid="stHeader"] {
        background: #FFFFFF !important;
    }
    .block-container {
        padding: 1.5rem 2rem 5rem 2rem;
        max-width: 1400px;
        background: #FFFFFF !important;
    }

    /* ══════════ Sidebar ══════════ */
    [data-testid="stSidebar"] {
        background: #FAFAFA;
        border-right: 1px solid #F0F0F0;
    }

    /* ══════════ Metric Cards (st.metric nativo) ══════════ */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #F0F0F0;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label {
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #8E8E93 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #1C1C1E !important;
        letter-spacing: -0.5px;
    }
    [data-testid="stMetricDelta"] {
        font-size: 12px !important;
        font-weight: 500 !important;
    }

    /* ══════════ Forms ══════════ */
    [data-testid="stForm"] {
        background: #FAFAFA;
        border: 1px solid #F0F0F0;
        border-radius: 14px;
        padding: 24px;
    }

    /* ══════════ Inputs — Touch-friendly ══════════ */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stDateInput > div > div > input {
        border-radius: 10px !important;
        border: 1.5px solid #E5E5EA !important;
        background: #FFFFFF !important;
        font-size: 15px !important;
        min-height: 44px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #007AFF !important;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.1) !important;
    }

    /* ══════════ BOTÕES AZUIS — Seletores agressivos ══════════ */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"],
    .stFormSubmitButton > button,
    .stFormSubmitButton > button[kind="primary"],
    button[kind="primary"],
    div.stFormSubmitButton > button {
        background: #007AFF !important;
        background-image: none !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(0,122,255,0.25) !important;
        min-height: 44px;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover,
    button[kind="primary"]:hover,
    div.stFormSubmitButton > button:hover {
        background: #0066D6 !important;
        box-shadow: 0 4px 16px rgba(0,122,255,0.3) !important;
        transform: translateY(-1px);
    }
    .stButton > button[kind="primary"]:active,
    .stFormSubmitButton > button:active {
        transform: scale(0.98);
    }

    /* Secondary buttons */
    .stButton > button:not([kind="primary"]) {
        border-radius: 12px !important;
        font-weight: 500 !important;
        min-height: 44px;
        border: 1.5px solid #E5E5EA !important;
        background: #FFFFFF !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        background: #F8F8F8 !important;
        border-color: #D1D1D6 !important;
    }

    /* ══════════ Data Editor / Tables ══════════ */
    .stDataFrame, [data-testid="stDataEditor"] {
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid #F0F0F0 !important;
    }
    [data-testid="stDataEditor"] > div {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
    }

    /* ══════════ Expander ══════════ */
    [data-testid="stExpander"] {
        background: #FAFAFA;
        border: 1px solid #F0F0F0;
        border-radius: 14px !important;
        overflow: hidden;
    }

    /* ══════════ Headings ══════════ */
    h1 { font-size: 28px !important; font-weight: 700 !important; color: #1C1C1E !important; }
    h2 { font-size: 22px !important; font-weight: 600 !important; color: #1C1C1E !important; }
    h3 { font-size: 17px !important; font-weight: 600 !important; color: #1C1C1E !important; }

    /* ══════════ Alerts ══════════ */
    [data-testid="stAlert"] { border-radius: 12px !important; border: none !important; }

    /* ══════════ Divider ══════════ */
    hr { border: none; border-top: 1px solid #F0F0F0; margin: 1.2rem 0; }

    /* ══════════ Scrollbar ══════════ */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D1D1D6; border-radius: 3px; }

    /* ══════════ RESPONSIVE: iPad ══════════ */
    @media screen and (max-width: 1024px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; max-width: 100%; }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        h1 { font-size: 24px !important; }
    }

    /* ══════════ RESPONSIVE: iPhone ══════════ */
    @media screen and (max-width: 768px) {
        .block-container { padding: 0.8rem 0.75rem 5rem 0.75rem; }
        div[data-testid="stMetric"] { padding: 14px 16px; border-radius: 12px; }
        div[data-testid="stMetric"] label { font-size: 10px !important; }
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 15px !important; }
        [data-testid="stForm"] { padding: 16px; border-radius: 12px; }
    }

    /* ══════════ Tela de Login (Acesso Restrito) ══════════ */
    .auth-wrap{
      max-width: 980px;
      margin: 9vh auto 0 auto;
      padding: 0 16px;
    }
    .auth-title{
      display:flex; align-items:center; gap:14px;
      font-size: 54px; font-weight: 800; color:#111827;
      letter-spacing: -1px;
      margin: 0 0 10px 0;
    }
    .auth-sub{
      font-size: 16px; color:#6B7280;
      margin: 0 0 14px 0;
    }
    .auth-card{
      background: transparent;
      border-radius: 18px;
    }
    .auth-card .stTextInput input{
      height: 52px !important;
      border-radius: 14px !important;
      border: 1.5px solid #E5E7EB !important;
      background: #F3F4F6 !important;
      font-size: 16px !important;
      padding-left: 16px !important;
    }
    .auth-card .stTextInput input:focus{
      border-color:#007AFF !important;
      box-shadow: 0 0 0 3px rgba(0,122,255,0.12) !important;
      background: #FFFFFF !important;
    }
    .auth-card .stButton button{
      height: 52px !important;
      border-radius: 14px !important;
      font-size: 16px !important;
      font-weight: 700 !important;
      padding: 0 26px !important;
    }
    .auth-card label { display:none !important; }

    @media (max-width: 768px){
      .auth-title{ font-size: 40px; }
      .auth-wrap{ margin-top: 7vh; }
    }
</style>
""",
    unsafe_allow_html=True,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. CONSTANTES / SCHEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORES = {
    "primaria": "#007AFF",
    "orcado": "#98989D",
    "realizado": "#34C759",
    "alerta": "#FF3B30",
    "aviso": "#FF9500",
    "texto": "#1C1C1E",
    "texto2": "#3A3A3C",
    "texto3": "#8E8E93",
}

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

SHEET_NAME = "dados_app_orcamento"
TAB_LANC = "lançamentos"
TAB_LANC_FALLBACK = ["lancamentos", "Lancamentos", "LANÇAMENTOS", "Lançamentos"]
TAB_CAD = "cadastros"
TAB_ENV = "envolvidos"
TAB_LOG = "logs"

COLS_LANC = [
    "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria",
    "Valor", "Descrição", "Parcela", "Abatido",
    "Envolvidos", "Info Gerais",
    "Lanc_ID", "Grupo_ID", "Orcado_Vinculo", "Criado_Em"
]

PLOTLY_LAYOUT = dict(
    font_family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
    font_color="#3A3A3C",
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    margin=dict(l=8, r=8, t=8, b=48),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.22,
        xanchor="center", x=0.5,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#8E8E93")
    ),
    xaxis=dict(showgrid=False, showline=False,
               tickfont=dict(size=11, color="#8E8E93"), fixedrange=True),
    yaxis=dict(showgrid=True, gridcolor="#F5F5F5", gridwidth=1,
               showline=False, tickfont=dict(size=11, color="#8E8E93"), fixedrange=True),
    hoverlabel=dict(bgcolor="white", bordercolor="#E5E5EA",
                    font_size=13, font_color="#1C1C1E"),
    dragmode=False,
)

PLOTLY_CONFIG = {
    "displayModeBar": False, "scrollZoom": False,
    "doubleClick": False, "showTips": False, "responsive": True,
}

THRESH_OK = 70
THRESH_WARN = 85
THRESH_MAX = 100


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def uuid4() -> str:
    return str(uuid.uuid4())


def mes_str_from_date(d: date) -> str:
    return f"{d.month:02d} - {MESES_PT[d.month]}"


def mes_num(m: str) -> int:
    try:
        return int(str(m).split(" - ")[0])
    except Exception:
        return 0


def fmt_real(v) -> str:
    try:
        v = float(v)
    except Exception:
        v = 0.0
    if v < 0:
        return f"-R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(realizado, orcado) -> float:
    try:
        realizado = float(realizado)
        orcado = float(orcado)
    except Exception:
        return 0.0
    return (realizado / orcado * 100.0) if orcado else 0.0


def render_section_title(title: str):
    st.markdown(
        f"""
    <div style="font-size:11px; font-weight:600; color:#8E8E93;
         text-transform:uppercase; letter-spacing:1px; padding:16px 0 8px 0;">
        {title}
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_progress_bar(consumido, orcado, label=None):
    p = min(pct(consumido, orcado), 120)
    if p <= THRESH_OK:
        cor = CORES["realizado"]
        cor_bg = "rgba(52,199,89,0.12)"
    elif p <= THRESH_MAX:
        cor = CORES["aviso"]
        cor_bg = "rgba(255,149,0,0.12)"
    else:
        cor = CORES["alerta"]
        cor_bg = "rgba(255,59,48,0.12)"

    label_html = (
        f'<div style="font-size:14px; font-weight:600; color:#1C1C1E; margin-bottom:10px;">{label}</div>'
        if label else ""
    )

    st.markdown(
        f"""
    <div style="background:#FFFFFF; border:1px solid #F0F0F0; border-radius:14px;
         padding:18px 20px; box-shadow:0 1px 4px rgba(0,0,0,0.04); margin-bottom:20px;">
      {label_html}
      <div style="display:flex; justify-content:space-between; align-items:center;
           margin-bottom:10px; flex-wrap:wrap; gap:4px;">
        <span style="font-size:13px; font-weight:500; color:#3A3A3C;">
          Consumido: <strong>{fmt_real(consumido)}</strong>
        </span>
        <span style="background:{cor_bg}; color:{cor}; padding:4px 12px; border-radius:8px;
              font-size:13px; font-weight:700;">{p:.0f}%</span>
      </div>
      <div style="background:#F5F5F5; border-radius:6px; height:8px; width:100%; overflow:hidden;">
        <div style="background:{cor}; width:{min(p,100):.0f}%; height:8px; border-radius:6px;"></div>
      </div>
      <div style="display:flex; justify-content:space-between; margin-top:6px;">
        <span style="font-size:11px; color:#C7C7CC;">R$ 0</span>
        <span style="font-size:11px; color:#C7C7CC;">{fmt_real(orcado)}</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_progress_row(nome, consumido, orcado):
    p = min(pct(consumido, orcado), 120)
    if p <= THRESH_OK:
        cor = CORES["realizado"]
        cor_bg = "rgba(52,199,89,0.12)"
    elif p <= THRESH_MAX:
        cor = CORES["aviso"]
        cor_bg = "rgba(255,149,0,0.12)"
    else:
        cor = CORES["alerta"]
        cor_bg = "rgba(255,59,48,0.12)"

    saldo = float(orcado) - float(consumido)
    saldo_cor = CORES["realizado"] if saldo >= 0 else CORES["alerta"]

    return (
        f'<div style="padding:14px 0;border-bottom:1px solid #F5F5F5;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:4px;">'
        f'<span style="font-size:14px;font-weight:600;color:#1C1C1E;">{nome}</span>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:12px;color:#8E8E93;">{fmt_real(consumido)} / {fmt_real(orcado)}</span>'
        f'<span style="background:{cor_bg};color:{cor};padding:2px 10px;border-radius:6px;font-size:12px;font-weight:700;">{p:.0f}%</span>'
        f"</div></div>"
        f'<div style="background:#F5F5F5;border-radius:4px;height:6px;width:100%;overflow:hidden;">'
        f'<div style="background:{cor};width:{min(p,100):.0f}%;height:6px;border-radius:4px;"></div>'
        f"</div>"
        f'<div style="display:flex;justify-content:flex-end;margin-top:4px;">'
        f'<span style="font-size:11px;color:{saldo_cor};font-weight:500;">Saldo: {fmt_real(saldo)}</span>'
        f"</div></div>"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. TELA DE SENHA (ANTES DE ABRIR O APP)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def gate_password_screen() -> None:
    """Tela de acesso restrito antes de mostrar o app inteiro."""
    if st.session_state.get("auth_ok"):
        return

    senha_correta = st.secrets.get("app_password") or os.getenv("APP_PASSWORD")
    if not senha_correta:
        st.error("Senha não configurada. Defina `app_password` em .streamlit/secrets.toml ou APP_PASSWORD no ambiente.")
        st.stop()

    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">🔒 <span>Acesso Restrito</span></div>', unsafe_allow_html=True)
    st.markdown('<p class="auth-sub">Digite a senha de acesso</p>', unsafe_allow_html=True)
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    with st.form("auth_form", clear_on_submit=False):
        senha = st.text_input("Senha", type="password", placeholder="••••••••••")
        entrar = st.form_submit_button("Entrar", type="primary")

    st.markdown("</div></div>", unsafe_allow_html=True)

    if entrar:
        if senha == senha_correta:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    st.stop()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. GOOGLE SHEETS — CONEXÃO + SCHEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_resource(ttl=300)
def conectar_google():
    try:
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_json = os.path.join(diretorio_atual, "credentials.json")
        if os.path.exists(caminho_json):
            return gspread.service_account(filename=caminho_json)
        elif "google_credentials" in st.secrets:
            creds_data = st.secrets["google_credentials"]["content"]
            creds_dict = json.loads(creds_data) if isinstance(creds_data, str) else dict(creds_data)
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return gspread.service_account_from_dict(creds_dict)
        else:
            st.error("Credenciais não encontradas (credentials.json ou st.secrets).")
            return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None


def get_worksheet_case_insensitive(sh, nome: str):
    for ws in sh.worksheets():
        if ws.title.strip().lower() == nome.strip().lower():
            return ws
    return None


def get_ws_lanc(sh):
    ws = get_worksheet_case_insensitive(sh, TAB_LANC)
    if ws:
        return ws
    for alt in TAB_LANC_FALLBACK:
        ws = get_worksheet_case_insensitive(sh, alt)
        if ws:
            return ws
    return None


def get_or_create_worksheet(sh, title: str, rows: int, cols: int, header: Optional[List[str]] = None):
    ws = get_worksheet_case_insensitive(sh, title)
    if ws:
        return ws
    ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
    if header:
        ws.append_row(header, value_input_option="USER_ENTERED")
    return ws


def ensure_schema_simple(ws, header: List[str]):
    values = ws.get_all_values()
    if not values:
        ws.append_row(header, value_input_option="USER_ENTERED")
        return
    existing = [c.strip() for c in values[0]]
    if existing != header:
        ws.update("1:1", [header])


def ensure_schema_lanc(ws):
    values = ws.get_all_values()
    if not values:
        ws.append_row(COLS_LANC, value_input_option="USER_ENTERED")
        return

    header = [h.strip() for h in values[0]]
    missing = [c for c in COLS_LANC if c not in header]
    if not missing:
        return

    new_header = header + missing
    ws.update("1:1", [new_header])

    n_rows = len(values) - 1
    if n_rows <= 0:
        return

    total_cols = len(new_header)
    body = values[1:]
    padded = []
    for row in body:
        r = row + [""] * (total_cols - len(row))
        padded.append(r[:total_cols])

    start_row = 2
    end_row = n_rows + 1
    ws.update(
        f"A{start_row}:{gspread.utils.rowcol_to_a1(end_row, total_cols)}",
        padded
    )


def log_event(sh, action: str, detail: str, n: int = 0):
    try:
        ws = get_or_create_worksheet(sh, TAB_LOG, rows=500, cols=5,
                                     header=["Timestamp", "Ação", "Detalhe", "Qtd", "Origem"])
        ensure_schema_simple(ws, ["Timestamp", "Ação", "Detalhe", "Qtd", "Origem"])
        ws.append_row([now_iso(), action, detail, str(n), "streamlit_app"], value_input_option="USER_ENTERED")
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. DADOS — LOAD / CLEAN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def moeda_to_float_series(s: pd.Series) -> pd.Series:
    if s is None or len(s) == 0:
        return pd.Series([], dtype="float64")

    x = s.astype(str).fillna("").str.strip()
    x = x.replace({"": "0", "None": "0", "nan": "0", "NaN": "0"})
    x = x.str.replace("R$", "", regex=False).str.replace(" ", "", regex=False)

    has_comma = x.str.contains(",", regex=False)
    x = x.where(~has_comma, x.str.replace(".", "", regex=False))
    x = x.where(~has_comma, x.str.replace(",", ".", regex=False))

    dot_count = x.str.count(r"\.")
    maybe_thousand = (dot_count == 1) & (x.str.split(".").str[-1].str.len() == 3)
    x = x.where(~maybe_thousand, x.str.replace(".", "", regex=False))

    return pd.to_numeric(x, errors="coerce").fillna(0.0).astype(float)


def normalize_text_cols(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("").str.strip()
    return df


def normalize_tipo(df: pd.DataFrame) -> pd.DataFrame:
    if "Tipo" not in df.columns:
        return df
    m = {
        "orcado": "Orçado",
        "orçado": "Orçado",
        "planejado": "Orçado",
        "realizado": "Realizado",
        "efetivado": "Realizado",
    }
    df["Tipo"] = (
        df["Tipo"]
        .astype(str)
        .fillna("")
        .str.strip()
        .apply(lambda v: m.get(v.lower(), v))
    )
    return df


def derive_year_from_date(df: pd.DataFrame) -> pd.DataFrame:
    df["Data_dt"] = pd.to_datetime(df.get("Data", ""), format="%d/%m/%Y", errors="coerce")

    if "Ano" not in df.columns:
        df["Ano"] = np.nan

    ano_num = pd.to_numeric(df["Ano"], errors="coerce")
    ano_from_data = df["Data_dt"].dt.year
    ano_final = ano_num.where(~ano_num.isna(), ano_from_data)

    df["Ano_Invalido"] = ano_final.isna()
    df["Ano"] = ano_final.fillna(date.today().year).astype(int)
    return df


def ensure_month_consistency(df: pd.DataFrame) -> pd.DataFrame:
    if "Mês" not in df.columns:
        df["Mês"] = ""
    mask = (df["Mês"].astype(str).str.strip() == "") & (df["Data_dt"].notna())
    df.loc[mask, "Mês"] = df.loc[mask, "Data_dt"].dt.month.apply(
        lambda m: f"{int(m):02d} - {MESES_PT[int(m)]}"
    )
    return df


@st.cache_data(ttl=120, show_spinner=False)
def carregar_dados(cache_buster: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    client = conectar_google()
    if not client:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    try:
        sh = client.open(SHEET_NAME)

        ws_lanc = get_ws_lanc(sh)
        if not ws_lanc:
            ws_lanc = get_or_create_worksheet(sh, TAB_LANC, rows=3000, cols=len(COLS_LANC), header=COLS_LANC)
        ensure_schema_lanc(ws_lanc)

        dados_lanc = ws_lanc.get_all_values()
        header = [h.strip() for h in (dados_lanc[0] if dados_lanc else COLS_LANC)]
        body = dados_lanc[1:] if len(dados_lanc) > 1 else []
        df_lanc = pd.DataFrame(body, columns=header) if body else pd.DataFrame(columns=header)

        for c in COLS_LANC:
            if c not in df_lanc.columns:
                df_lanc[c] = ""

        df_lanc = normalize_text_cols(df_lanc, [
            "Projeto", "Categoria", "Descrição", "Envolvidos", "Info Gerais",
            "Parcela", "Abatido", "Lanc_ID", "Grupo_ID", "Orcado_Vinculo", "Criado_Em", "Mês"
        ])
        df_lanc = normalize_tipo(df_lanc)

        df_lanc["Valor_num"] = moeda_to_float_series(df_lanc["Valor"]) if "Valor" in df_lanc.columns else 0.0

        df_lanc = derive_year_from_date(df_lanc)
        df_lanc = ensure_month_consistency(df_lanc)

        df_lanc["Mes_Num"] = df_lanc["Mês"].apply(mes_num)

        df_lanc["Lanc_ID"] = df_lanc["Lanc_ID"].replace({"": np.nan}).fillna(
            df_lanc.apply(lambda _: uuid4(), axis=1)
        )
        df_lanc["Grupo_ID"] = df_lanc["Grupo_ID"].replace({"": np.nan}).fillna("")
        df_lanc["Orcado_Vinculo"] = df_lanc["Orcado_Vinculo"].replace({"": np.nan}).fillna("")

        # cadastros
        ws_cad = get_or_create_worksheet(sh, TAB_CAD, rows=200, cols=2, header=["Tipo", "Nome"])
        ensure_schema_simple(ws_cad, ["Tipo", "Nome"])
        dados_cad = ws_cad.get_all_values()
        df_cad = pd.DataFrame(dados_cad[1:], columns=["Tipo", "Nome"]) if len(dados_cad) > 1 else pd.DataFrame(columns=["Tipo", "Nome"])
        df_cad = normalize_text_cols(df_cad, ["Tipo", "Nome"])

        # envolvidos
        ws_env = get_or_create_worksheet(
            sh, TAB_ENV, rows=1500, cols=8,
            header=["Ano", "Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Observações"]
        )
        ensure_schema_simple(ws_env, ["Ano", "Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Observações"])
        dados_env = ws_env.get_all_values()
        cols_env = ["Ano", "Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Observações"]
        df_env = pd.DataFrame(dados_env[1:], columns=cols_env) if len(dados_env) > 1 else pd.DataFrame(columns=cols_env)
        df_env = normalize_text_cols(df_env, cols_env)

        return df_lanc, df_cad, df_env

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. ESCRITA — APPEND / DELETE / CADASTROS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def invalidate_cache():
    st.session_state.cache_buster = int(st.session_state.get("cache_buster", 0)) + 1


def salvar_lancamentos(linhas: List[List]) -> bool:
    client = conectar_google()
    if not client:
        return False
    try:
        sh = client.open(SHEET_NAME)
        ws = get_ws_lanc(sh)
        if not ws:
            ws = get_or_create_worksheet(sh, TAB_LANC, rows=3000, cols=len(COLS_LANC), header=COLS_LANC)
        ensure_schema_lanc(ws)

        ws.append_rows(linhas, value_input_option="USER_ENTERED")
        log_event(sh, "append_lancamentos", "append_rows", n=len(linhas))
        invalidate_cache()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False


def salvar_envolvido(dados_linha: List[str]) -> bool:
    client = conectar_google()
    if not client:
        return False
    try:
        sh = client.open(SHEET_NAME)
        ws = get_or_create_worksheet(
            sh, TAB_ENV, rows=1500, cols=8,
            header=["Ano", "Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Observações"]
        )
        ensure_schema_simple(ws, ["Ano", "Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Observações"])
        ws.append_row(dados_linha, value_input_option="USER_ENTERED")
        log_event(sh, "append_envolvido", "append_row", n=1)
        invalidate_cache()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar envolvido: {e}")
        return False


def salvar_cadastro_novo(tipo: str, nome: str) -> bool:
    client = conectar_google()
    if not client:
        return False
    try:
        sh = client.open(SHEET_NAME)
        ws = get_or_create_worksheet(sh, TAB_CAD, rows=200, cols=2, header=["Tipo", "Nome"])
        ensure_schema_simple(ws, ["Tipo", "Nome"])

        dados_existentes = ws.get_all_values()
        for row in dados_existentes[1:]:
            if (
                len(row) >= 2
                and row[0].strip().lower() == tipo.strip().lower()
                and row[1].strip().lower() == nome.strip().lower()
            ):
                st.warning(f"'{nome}' já existe em {tipo}.")
                return False

        ws.append_row([tipo, nome], value_input_option="USER_ENTERED")
        log_event(sh, "append_cadastro", f"{tipo}:{nome}", n=1)
        invalidate_cache()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar cadastro: {e}")
        return False


def _group_contiguous(sorted_rows: List[int]) -> List[Tuple[int, int]]:
    if not sorted_rows:
        return []
    groups = []
    start = prev = sorted_rows[0]
    for r in sorted_rows[1:]:
        if r == prev + 1:
            prev = r
        else:
            groups.append((start, prev))
            start = prev = r
    groups.append((start, prev))
    return groups


def excluir_linhas_por_lanc_id(lanc_ids: List[str]) -> bool:
    if not lanc_ids:
        return False

    client = conectar_google()
    if not client:
        return False

    try:
        sh = client.open(SHEET_NAME)
        ws = get_ws_lanc(sh)
        if not ws:
            st.error("Aba de lançamentos não encontrada.")
            return False

        ensure_schema_lanc(ws)
        values = ws.get_all_values()
        if len(values) <= 1:
            return False

        header = [h.strip() for h in values[0]]
        if "Lanc_ID" not in header:
            st.error("Coluna Lanc_ID não existe na planilha.")
            return False

        col_idx = header.index("Lanc_ID")
        target = set(lanc_ids)

        rows_to_delete = []
        for i, row in enumerate(values[1:], start=2):
            row_id = row[col_idx].strip() if len(row) > col_idx else ""
            if row_id in target:
                rows_to_delete.append(i)

        if not rows_to_delete:
            st.warning("Nenhuma linha encontrada para exclusão (IDs não localizados).")
            return False

        rows_to_delete.sort()
        groups = _group_contiguous(rows_to_delete)

        requests = []
        sheet_id = ws._properties.get("sheetId")
        for start, end in reversed(groups):
            requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start - 1,
                        "endIndex": end,
                    }
                }
            })

        sh.batch_update({"requests": requests})
        log_event(sh, "delete_lancamentos", f"by_lanc_id groups={len(groups)}", n=len(rows_to_delete))
        invalidate_cache()
        return True

    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. ORÇADO x REALIZADO — AGREGADO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_orcamentos_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Orc_ID", "Ano", "Mês", "Mes_Num", "Projeto", "Categoria", "Orcado_Total"])

    df_orc = df[df["Tipo"] == "Orçado"].copy()
    if df_orc.empty:
        return pd.DataFrame(columns=["Orc_ID", "Ano", "Mês", "Mes_Num", "Projeto", "Categoria", "Orcado_Total"])

    if "Mes_Num" not in df_orc.columns:
        df_orc["Mes_Num"] = df_orc["Mês"].apply(mes_num)

    df_orc["Orc_ID"] = df_orc["Grupo_ID"].where(
        df_orc["Grupo_ID"].astype(str).str.strip() != "",
        df_orc["Lanc_ID"]
    )

    agg = (
        df_orc.groupby(["Orc_ID", "Ano", "Mês", "Mes_Num", "Projeto", "Categoria"], dropna=False)
        .agg(Orcado_Total=("Valor_num", "sum"))
        .reset_index()
    )
    return agg


def compute_consumo(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    alerts = []

    if df.empty:
        return pd.DataFrame(), pd.DataFrame(columns=["Tipo", "Mensagem"])

    df = df.copy()
    if "Mes_Num" not in df.columns:
        df["Mes_Num"] = df["Mês"].apply(mes_num)

    df_orc = build_orcamentos_table(df)
    df_real = df[df["Tipo"] == "Realizado"].copy()

    if df_orc.empty:
        if not df_real.empty:
            grp = df_real.groupby(["Ano", "Mês", "Projeto", "Categoria"], dropna=False)["Valor_num"].sum().reset_index()
            for _, r in grp.iterrows():
                alerts.append({
                    "Tipo": "Realizado sem Orçado",
                    "Mensagem": f"Realizado {fmt_real(r['Valor_num'])} em {r['Projeto']} / {r['Categoria']} ({r['Mês']} {r['Ano']}) sem orçamento."
                })
        return df_orc, pd.DataFrame(alerts, columns=["Tipo", "Mensagem"])

    if df_real.empty:
        df_orc["Realizado_Total"] = 0.0
        df_orc["Saldo"] = df_orc["Orcado_Total"]
        df_orc["Uso_%"] = df_orc.apply(lambda r: pct(r["Realizado_Total"], r["Orcado_Total"]), axis=1)
        df_orc["Status"] = np.where(df_orc["Saldo"] < 0, "Estouro", "OK")
        return df_orc, pd.DataFrame(alerts, columns=["Tipo", "Mensagem"])

    df_real["Orc_Vinc"] = df_real["Orcado_Vinculo"].astype(str).fillna("").str.strip()

    vinc = df_real[df_real["Orc_Vinc"] != ""]
    consumo_vinc = (
        vinc.groupby("Orc_Vinc")["Valor_num"].sum().reset_index()
        .rename(columns={"Orc_Vinc": "Orc_ID", "Valor_num": "Realizado_Vinculado"})
    )

    sem_vinc = df_real[df_real["Orc_Vinc"] == ""]
    if not sem_vinc.empty:
        sem_vinc_grp = (
            sem_vinc.groupby(["Ano", "Mês", "Projeto", "Categoria"], dropna=False)["Valor_num"].sum().reset_index()
        )

        best_orc_in_group = (
            df_orc.sort_values("Orcado_Total", ascending=False)
            .groupby(["Ano", "Mês", "Projeto", "Categoria"], dropna=False)
            .head(1)[["Orc_ID", "Ano", "Mês", "Projeto", "Categoria"]]
        )

        sem_vinc_mapped = sem_vinc_grp.merge(best_orc_in_group, on=["Ano", "Mês", "Projeto", "Categoria"], how="left")
        consumo_fallback = (
            sem_vinc_mapped.dropna(subset=["Orc_ID"])
            .groupby("Orc_ID")["Valor_num"].sum().reset_index()
            .rename(columns={"Valor_num": "Realizado_Fallback"})
        )

        nao_achou = sem_vinc_mapped[sem_vinc_mapped["Orc_ID"].isna()]
        if not nao_achou.empty:
            for _, r in nao_achou.iterrows():
                alerts.append({
                    "Tipo": "Realizado sem Orçado",
                    "Mensagem": f"Realizado {fmt_real(r['Valor_num'])} em {r['Projeto']} / {r['Categoria']} ({r['Mês']} {r['Ano']}) sem orçamento correspondente."
                })
    else:
        consumo_fallback = pd.DataFrame(columns=["Orc_ID", "Realizado_Fallback"])

    df_orc2 = df_orc.merge(consumo_vinc, on="Orc_ID", how="left")
    df_orc2["Realizado_Vinculado"] = df_orc2.get("Realizado_Vinculado", 0.0).fillna(0.0)

    if not consumo_fallback.empty:
        df_orc2 = df_orc2.merge(consumo_fallback, on="Orc_ID", how="left")
        df_orc2["Realizado_Fallback"] = df_orc2.get("Realizado_Fallback", 0.0).fillna(0.0)
    else:
        df_orc2["Realizado_Fallback"] = 0.0

    if "Mes_Num" not in df_orc2.columns:
        df_orc2["Mes_Num"] = df_orc2["Mês"].apply(mes_num)

    df_orc2["Realizado_Total"] = df_orc2["Realizado_Vinculado"] + df_orc2["Realizado_Fallback"]
    df_orc2["Saldo"] = df_orc2["Orcado_Total"] - df_orc2["Realizado_Total"]
    df_orc2["Uso_%"] = df_orc2.apply(lambda r: pct(r["Realizado_Total"], r["Orcado_Total"]), axis=1)
    df_orc2["Status"] = np.where(df_orc2["Saldo"] < 0, "Estouro", "OK")

    estouros = df_orc2[df_orc2["Saldo"] < 0]
    for _, r in estouros.iterrows():
        alerts.append({
            "Tipo": "Estouro",
            "Mensagem": f"Estouro em {r['Projeto']} / {r['Categoria']} ({r['Mês']} {r['Ano']}): saldo {fmt_real(r['Saldo'])}."
        })

    return df_orc2, pd.DataFrame(alerts, columns=["Tipo", "Mensagem"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. TELAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def tela_resumo(df: pd.DataFrame):
    st.markdown(
        "<h1>Painel Financeiro</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Visão consolidada do seu orçamento</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Sem dados. Acesse **Novo** para criar o primeiro lançamento.")
        return

    anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
    ano_atual = date.today().year
    default_ano = ano_atual if ano_atual in anos_disponiveis else (anos_disponiveis[0] if anos_disponiveis else ano_atual)

    with st.expander("🔍 Filtros", expanded=False):
        with st.form("form_filtros_painel"):
            c1, c2 = st.columns(2)
            ano_sel = c1.selectbox(
                "Ano", anos_disponiveis,
                index=anos_disponiveis.index(default_ano) if default_ano in anos_disponiveis else 0
            )
            meses_disp = sorted(df["Mês"].unique(), key=mes_num)
            meses_sel = c2.multiselect("Meses", meses_disp)

            c3, c4 = st.columns(2)
            proj_sel = c3.multiselect("Projetos", sorted(df["Projeto"].unique()))
            cat_sel = c4.multiselect("Categorias", sorted(df["Categoria"].unique()))

            st.form_submit_button("Aplicar", type="primary", use_container_width=True)

    df_f = df[df["Ano"] == ano_sel].copy()
    if meses_sel:
        df_f = df_f[df_f["Mês"].isin(meses_sel)]
    if proj_sel:
        df_f = df_f[df_f["Projeto"].isin(proj_sel)]
    if cat_sel:
        df_f = df_f[df_f["Categoria"].isin(cat_sel)]

    df_orc_agg, df_alertas = compute_consumo(df_f)

    orcado = df_f[df_f["Tipo"] == "Orçado"]["Valor_num"].sum()
    realizado = df_f[df_f["Tipo"] == "Realizado"]["Valor_num"].sum()
    saldo = orcado - realizado
    pct_uso = pct(realizado, orcado)
    n_proj = df_f["Projeto"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Orçado (linhas)", fmt_real(orcado))
    k2.metric("✅ Realizado", fmt_real(realizado), delta=f"{pct_uso:.1f}% do orçado", delta_color="off")
    k3.metric("📊 Saldo Livre", fmt_real(saldo),
              delta="Disponível" if saldo >= 0 else "Estouro",
              delta_color="normal" if saldo >= 0 else "inverse")
    k4.metric("🏢 Projetos Ativos", n_proj)

    if not df_alertas.empty:
        with st.expander(f"⚠️ Alertas ({len(df_alertas)})", expanded=False):
            st.dataframe(df_alertas, use_container_width=True, hide_index=True)

    render_section_title("Consumo do Orçamento · Geral")
    render_progress_bar(realizado, orcado)

    render_section_title("Consumo por Projeto")
    if not df_orc_agg.empty:
        proj_agg = (
            df_orc_agg.groupby("Projeto")[["Orcado_Total", "Realizado_Total"]]
            .sum().reset_index()
            .sort_values("Orcado_Total", ascending=False)
        )
        rows_html = "".join(
            render_progress_row(r["Projeto"], r["Realizado_Total"], r["Orcado_Total"])
            for _, r in proj_agg.iterrows()
        )
        st.markdown(
            f'<div style="background:#FFFFFF;border:1px solid #F0F0F0;border-radius:14px;padding:6px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.04);margin-bottom:20px;">{rows_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Sem orçamentos para exibir (cadastre ao menos um 'Orçado').")

    render_section_title("Consumo por Categoria")
    if not df_orc_agg.empty:
        cat_agg = (
            df_orc_agg.groupby("Categoria")[["Orcado_Total", "Realizado_Total"]]
            .sum().reset_index()
            .sort_values("Orcado_Total", ascending=False)
        )
        rows_html = "".join(
            render_progress_row(r["Categoria"], r["Realizado_Total"], r["Orcado_Total"])
            for _, r in cat_agg.iterrows()
        )
        st.markdown(
            f'<div style="background:#FFFFFF;border:1px solid #F0F0F0;border-radius:14px;padding:6px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.04);margin-bottom:20px;">{rows_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Sem orçamentos para exibir (cadastre ao menos um 'Orçado').")

    render_section_title("Evolução Mensal")
    df_mes = df_f.groupby(["Mês", "Tipo"])["Valor_num"].sum().reset_index()
    if not df_mes.empty:
        df_mes["Mes_Num"] = df_mes["Mês"].apply(mes_num)
        df_mes = df_mes.sort_values("Mes_Num")

        fig_mes = px.bar(
            df_mes, x="Mês", y="Valor_num", color="Tipo", barmode="group",
            color_discrete_map={"Orçado": CORES["orcado"], "Realizado": CORES["realizado"]},
        )
        fig_mes.update_traces(
            texttemplate="%{y:.2s}", textposition="outside",
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>"
        )
        fig_mes.update_layout(height=360, bargap=0.3, bargroupgap=0.08, **PLOTLY_LAYOUT)
        st.plotly_chart(fig_mes, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("Sem dados mensais para exibir.")

    render_section_title("Fluxo de Caixa · Waterfall")
    total_orcado = df_f[df_f["Tipo"] == "Orçado"]["Valor_num"].sum()
    df_gastos = (
        df_f[df_f["Tipo"] == "Realizado"]
        .groupby("Categoria")["Valor_num"]
        .sum()
        .reset_index()
        .sort_values("Valor_num", ascending=False)
    )

    if total_orcado > 0 or not df_gastos.empty:
        top_n = 6
        measures = ["absolute"]
        x_data = ["Orçamento Total"]
        y_data = [total_orcado]
        text_data = [fmt_real(total_orcado)]
        saldo_wf = total_orcado

        df_top = df_gastos.head(top_n)
        outros_val = df_gastos.iloc[top_n:]["Valor_num"].sum() if len(df_gastos) > top_n else 0

        for _, row in df_top.iterrows():
            measures.append("relative")
            x_data.append(row["Categoria"])
            y_data.append(-row["Valor_num"])
            text_data.append(f"-{fmt_real(row['Valor_num'])}")
            saldo_wf -= row["Valor_num"]

        if outros_val > 0:
            measures.append("relative")
            x_data.append("Outros")
            y_data.append(-outros_val)
            text_data.append(f"-{fmt_real(outros_val)}")
            saldo_wf -= outros_val

        measures.append("total")
        x_data.append("Saldo Final")
        y_data.append(0)
        text_data.append(fmt_real(saldo_wf))

        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=measures, x=x_data,
            textposition="outside", text=text_data, y=y_data,
            connector={"line": {"color": "#E5E5EA", "width": 1, "dash": "dot"}},
            decreasing={"marker": {"color": CORES["alerta"], "line": {"width": 0}}},
            increasing={"marker": {"color": CORES["realizado"], "line": {"width": 0}}},
            totals={"marker": {"color": CORES["primaria"], "line": {"width": 0}}},
            hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>"
        ))
        fig_wf.update_layout(height=400, waterfallgap=0.3, **PLOTLY_LAYOUT)
        st.plotly_chart(fig_wf, use_container_width=True, config=PLOTLY_CONFIG)


def tela_novo(df_lanc: pd.DataFrame, df_cad: pd.DataFrame):
    st.markdown(
        "<h1>Novo Lançamento</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Registre orçamentos e despesas realizadas</p>",
        unsafe_allow_html=True,
    )

    if df_cad.empty:
        st.warning("Nenhum Projeto ou Categoria cadastrado. Acesse **Cadastros** primeiro.")
        lista_proj, lista_cat = [], []
    else:
        lista_proj = sorted(df_cad[df_cad["Tipo"].str.lower() == "projeto"]["Nome"].unique().tolist())
        lista_cat = sorted(df_cad[df_cad["Tipo"].str.lower() == "categoria"]["Nome"].unique().tolist())

    df_orc_agg = build_orcamentos_table(df_lanc) if not df_lanc.empty else pd.DataFrame()

    with st.form("form_novo", clear_on_submit=True):
        render_section_title("Dados Principais")
        c1, c2 = st.columns(2)
        data_inicial = c1.date_input("📅 Data Inicial", date.today())
        tipo = c2.selectbox("🏷️ Tipo / Status", ["Orçado", "Realizado"], help="Orçado = planejado | Realizado = efetivado")

        c3, c4 = st.columns(2)
        proj_sel = c3.selectbox("🏢 Projeto", lista_proj, index=None, placeholder="Selecione...")
        cat_sel = c4.selectbox("📂 Categoria", lista_cat, index=None, placeholder="Selecione...")

        orc_vinc = ""
        if tipo == "Realizado" and proj_sel and cat_sel and not df_orc_agg.empty:
            mes0 = mes_str_from_date(data_inicial)
            ano0 = data_inicial.year
            cand = df_orc_agg[(df_orc_agg["Projeto"] == proj_sel) & (df_orc_agg["Categoria"] == cat_sel)].copy()
            cand["prio"] = np.where((cand["Ano"] == ano0) & (cand["Mês"] == mes0), 0, 1)
            cand = cand.sort_values(["prio", "Ano", "Mes_Num", "Orcado_Total"], ascending=[True, False, False, False]).head(30)

            options = ["(Sem vínculo — automático por grupo)"]
            label_to_id = {"(Sem vínculo — automático por grupo)": ""}

            for _, r in cand.iterrows():
                label = f"{r['Mês']} {r['Ano']} · {r['Projeto']} / {r['Categoria']} · Orçado {fmt_real(r['Orcado_Total'])} · ID {str(r['Orc_ID'])[:8]}"
                options.append(label)
                label_to_id[label] = r["Orc_ID"]

            render_section_title("Vínculo com Orçamento (opcional)")
            sel = st.selectbox("🔗 Vincular este realizado a um orçamento", options, index=0)
            orc_vinc = label_to_id.get(sel, "")

        render_section_title("Valores")
        c5, c6 = st.columns(2)
        valor = c5.number_input("💵 Valor da Parcela (R$)", min_value=0.0, step=100.0, format="%.2f")
        qtd_parcelas = c6.number_input("🔁 Nº Parcelas", min_value=1, value=1, step=1)

        if valor > 0 and qtd_parcelas > 1:
            st.info(f"Total comprometido: **{fmt_real(valor * qtd_parcelas)}** em {qtd_parcelas} meses")

        desc = st.text_input("📝 Descrição", placeholder="Opcional — descreva a natureza do lançamento")

        render_section_title("Informações Complementares")
        c7, c8 = st.columns(2)
        envolvidos = c7.text_input("👥 Envolvidos", placeholder="Ex: João, Fornecedor X")
        info_gerais = c8.text_area("📋 Observações", placeholder="Notas livres...", height=96)

        submitted = st.form_submit_button("💾 Salvar Lançamento", type="primary", use_container_width=True)

        if submitted:
            if proj_sel is None or cat_sel is None:
                st.error("Projeto e Categoria são obrigatórios.")
            elif valor <= 0:
                st.error("Informe um valor maior que zero.")
            else:
                grupo_id = uuid4()
                criado_em = now_iso()
                linhas = []
                for i in range(int(qtd_parcelas)):
                    data_calc = data_inicial + relativedelta(months=i)
                    mes_str = mes_str_from_date(data_calc)
                    lanc_id = uuid4()
                    valor_fmt = fmt_real(valor)
                    orc_vinc_to_save = orc_vinc if (tipo == "Realizado") else ""

                    linhas.append([
                        data_calc.strftime("%d/%m/%Y"),
                        data_calc.year,
                        mes_str,
                        tipo,
                        proj_sel,
                        cat_sel,
                        valor_fmt,
                        desc,
                        f"{i+1} de {qtd_parcelas}",
                        "Não",
                        envolvidos,
                        info_gerais,
                        lanc_id,
                        grupo_id,
                        orc_vinc_to_save,
                        criado_em
                    ])

                with st.spinner("Salvando lançamentos..."):
                    if salvar_lancamentos(linhas):
                        st.toast(f"{qtd_parcelas} lançamento(s) salvo(s)!", icon="✅")
                        st.success("Tudo certo — dados gravados.")
                        st.rerun()


def tela_dados(df: pd.DataFrame):
    st.markdown(
        "<h1>Base de Dados</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Visualize, filtre e gerencie todos os lançamentos</p>",
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("A planilha está vazia.")
        return

    tabs = st.tabs(["📄 Lançamentos (linhas)", "📦 Orçamentos (agregado)"])

    # TAB 1: LANÇAMENTOS
    with tabs[0]:
        with st.form("form_filtros_dados"):
            render_section_title("Filtros de Pesquisa")
            c1, c2 = st.columns(2)
            anos_disp = sorted(df["Ano"].unique(), reverse=True)
            ano_atual = date.today().year
            default_ano = [ano_atual] if ano_atual in anos_disp else ([anos_disp[0]] if anos_disp else [])
            filtro_ano = c1.multiselect("📅 Ano (obrigatório)", anos_disp, default=default_ano)

            meses_disp = sorted(df["Mês"].unique(), key=mes_num)
            filtro_mes = c2.multiselect("🗓️ Mês", meses_disp)

            c3, c4, c5 = st.columns(3)
            filtro_proj = c3.multiselect("🏢 Projeto", sorted(df["Projeto"].unique()))
            filtro_tipo = c4.multiselect("🏷️ Tipo", sorted(df["Tipo"].unique()))
            filtro_cat = c5.multiselect("📂 Categoria", sorted(df["Categoria"].unique()))
            st.form_submit_button("Aplicar Filtros", type="primary", use_container_width=True)

        if not filtro_ano:
            st.warning("Selecione pelo menos um **Ano** para visualizar os dados.")
            return

        df_view = df[df["Ano"].isin(filtro_ano)].copy()
        if filtro_mes:
            df_view = df_view[df_view["Mês"].isin(filtro_mes)]
        if filtro_proj:
            df_view = df_view[df_view["Projeto"].isin(filtro_proj)]
        if filtro_tipo:
            df_view = df_view[df_view["Tipo"].isin(filtro_tipo)]
        if filtro_cat:
            df_view = df_view[df_view["Categoria"].isin(filtro_cat)]

        tot_orc = df_view[df_view["Tipo"] == "Orçado"]["Valor_num"].sum()
        tot_real = df_view[df_view["Tipo"] == "Realizado"]["Valor_num"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Registros", len(df_view))
        m2.metric("💰 Total Orçado", fmt_real(tot_orc))
        m3.metric("✅ Total Realizado", fmt_real(tot_real))
        m4.metric("📊 Saldo", fmt_real(tot_orc - tot_real),
                  delta_color="normal" if tot_orc >= tot_real else "inverse")

        st.markdown("<hr>", unsafe_allow_html=True)

        cols_export = ["Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria", "Valor_num",
                       "Descrição", "Parcela", "Envolvidos", "Info Gerais",
                       "Lanc_ID", "Grupo_ID", "Orcado_Vinculo", "Criado_Em"]
        cols_export = [c for c in cols_export if c in df_view.columns]
        csv = df_view[cols_export].rename(columns={"Valor_num": "Valor"})
        st.download_button(
            "⬇️ Baixar CSV (filtro atual)",
            data=csv.to_csv(index=False).encode("utf-8"),
            file_name="lancamentos_filtrados.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

        tamanho_pagina = 50
        total_paginas = max(1, math.ceil(len(df_view) / tamanho_pagina))
        if total_paginas > 1:
            col_p, col_info = st.columns([1, 3])
            pagina_atual = col_p.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
            col_info.markdown(
                f"<p style='color:#8E8E93; font-size:13px; margin-top:32px;'>"
                f"Página {pagina_atual} de {total_paginas} · {len(df_view)} registros</p>",
                unsafe_allow_html=True,
            )
        else:
            pagina_atual = 1

        inicio = (pagina_atual - 1) * tamanho_pagina
        fim = inicio + tamanho_pagina
        df_paginado = df_view.iloc[inicio:fim].copy()
        df_paginado["Excluir"] = False

        colunas_show = ["Data", "Mês", "Tipo", "Projeto", "Categoria", "Valor_num",
                        "Descrição", "Envolvidos", "Info Gerais", "Parcela", "Excluir"]
        df_show = df_paginado[colunas_show].rename(columns={"Valor_num": "Valor"})

        df_edited = st.data_editor(
            df_show,
            column_config={
                "Excluir": st.column_config.CheckboxColumn("🗑️", width="small", default=False),
                "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            },
            disabled=["Data", "Mês", "Tipo", "Projeto", "Categoria", "Valor", "Descrição", "Envolvidos", "Info Gerais", "Parcela"],
            hide_index=True,
            use_container_width=True,
            key=f"editor_lanc_{pagina_atual}",
        )

        linhas_excluir = df_edited[df_edited["Excluir"] == True]
        if not linhas_excluir.empty:
            st.error(f"⚠️ **{len(linhas_excluir)} registro(s)** marcado(s) para exclusão. Esta ação não pode ser desfeita.")
            if st.button("🗑️ Confirmar Exclusão", type="primary", use_container_width=True):
                ids = df_paginado.loc[linhas_excluir.index, "Lanc_ID"].tolist()
                with st.spinner("Excluindo registros..."):
                    if excluir_linhas_por_lanc_id(ids):
                        st.success("Registros excluídos com sucesso!")
                        st.rerun()

    # TAB 2: ORÇAMENTOS AGREGADOS
    with tabs[1]:
        df_orc_agg, df_alertas = compute_consumo(df)

        if df_orc_agg.empty:
            st.info("Sem orçamentos cadastrados (tipo 'Orçado').")
            return

        with st.form("form_filtros_orc"):
            render_section_title("Filtros (Orçamentos)")
            c1, c2, c3 = st.columns(3)
            anos = sorted(df_orc_agg["Ano"].unique(), reverse=True)
            ano_sel = c1.multiselect("Ano", anos, default=[date.today().year] if date.today().year in anos else [anos[0]])
            meses = sorted(df_orc_agg["Mês"].unique(), key=mes_num)
            mes_sel = c2.multiselect("Mês", meses)
            proj_sel = c3.multiselect("Projeto", sorted(df_orc_agg["Projeto"].unique()))

            c4, c5 = st.columns(2)
            cat_sel = c4.multiselect("Categoria", sorted(df_orc_agg["Categoria"].unique()))
            status_sel = c5.multiselect("Status", sorted(df_orc_agg["Status"].unique()))

            st.form_submit_button("Aplicar", type="primary", use_container_width=True)

        view = df_orc_agg.copy()
        if ano_sel:
            view = view[view["Ano"].isin(ano_sel)]
        if mes_sel:
            view = view[view["Mês"].isin(mes_sel)]
        if proj_sel:
            view = view[view["Projeto"].isin(proj_sel)]
        if cat_sel:
            view = view[view["Categoria"].isin(cat_sel)]
        if status_sel:
            view = view[view["Status"].isin(status_sel)]

        tot_orc = view["Orcado_Total"].sum()
        tot_real = view["Realizado_Total"].sum()
        saldo = tot_orc - tot_real

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("📦 Orçamentos", len(view))
        a2.metric("💰 Orçado (agregado)", fmt_real(tot_orc))
        a3.metric("✅ Realizado (alocado)", fmt_real(tot_real))
        a4.metric("📊 Saldo", fmt_real(saldo), delta_color="normal" if saldo >= 0 else "inverse")

        if not df_alertas.empty:
            with st.expander(f"⚠️ Alertas ({len(df_alertas)})", expanded=False):
                st.dataframe(df_alertas, use_container_width=True, hide_index=True)

        # ✅ Correção do KeyError:
        show_cols = ["Ano", "Mês", "Projeto", "Categoria", "Orcado_Total", "Realizado_Total", "Saldo", "Uso_%", "Status", "Orc_ID"]
        view_sorted = view.sort_values(["Ano", "Mes_Num", "Projeto", "Categoria"], ascending=[False, False, True, True])
        out = view_sorted[show_cols].copy()

        st.dataframe(
            out,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Orcado_Total": st.column_config.NumberColumn("Orçado", format="R$ %.2f"),
                "Realizado_Total": st.column_config.NumberColumn("Realizado", format="R$ %.2f"),
                "Saldo": st.column_config.NumberColumn("Saldo", format="R$ %.2f"),
                "Uso_%": st.column_config.NumberColumn("Uso %", format="%.1f"),
                "Orc_ID": st.column_config.TextColumn("Orc_ID"),
            },
        )


def tela_cadastros(df_cad: pd.DataFrame, df_env: pd.DataFrame):
    st.markdown(
        "<h1>Cadastros</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Gerencie projetos, categorias e equipes do sistema</p>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2, gap="medium")

    with c1:
        render_section_title("🏢 Projetos")
        with st.form("form_proj", clear_on_submit=True):
            novo_proj = st.text_input("Nome do Projeto", placeholder="Ex: Reforma Sede 2025")
            if st.form_submit_button("Adicionar Projeto", type="primary", use_container_width=True):
                if novo_proj.strip():
                    with st.spinner("Salvando..."):
                        if salvar_cadastro_novo("Projeto", novo_proj.strip()):
                            st.success(f"Projeto '{novo_proj}' adicionado!")
                            st.rerun()
                else:
                    st.warning("Digite um nome válido.")
        if not df_cad.empty:
            proj_lista = df_cad[df_cad["Tipo"].str.lower() == "projeto"][["Nome"]].reset_index(drop=True)
            if not proj_lista.empty:
                st.caption(f"{len(proj_lista)} projeto(s) cadastrado(s)")
                st.dataframe(proj_lista, use_container_width=True, hide_index=True)

    with c2:
        render_section_title("📂 Categorias")
        with st.form("form_cat", clear_on_submit=True):
            nova_cat = st.text_input("Nome da Categoria", placeholder="Ex: Marketing Digital")
            if st.form_submit_button("Adicionar Categoria", type="primary", use_container_width=True):
                if nova_cat.strip():
                    with st.spinner("Salvando..."):
                        if salvar_cadastro_novo("Categoria", nova_cat.strip()):
                            st.success(f"Categoria '{nova_cat}' adicionada!")
                            st.rerun()
                else:
                    st.warning("Digite um nome válido.")
        if not df_cad.empty:
            cat_lista = df_cad[df_cad["Tipo"].str.lower() == "categoria"][["Nome"]].reset_index(drop=True)
            if not cat_lista.empty:
                st.caption(f"{len(cat_lista)} categoria(s) cadastrada(s)")
                st.dataframe(cat_lista, use_container_width=True, hide_index=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    render_section_title("👥 Envolvidos por Projeto / Mês")
    st.markdown(
        "<p style='color:#8E8E93; font-size:13px; margin-top:-4px; margin-bottom:16px;'>Cadastre as pessoas alocadas em cada projeto por mês para apuração de centro de custo e mão de obra.</p>",
        unsafe_allow_html=True,
    )

    if not df_cad.empty:
        lista_proj = sorted(df_cad[df_cad["Tipo"].str.lower() == "projeto"]["Nome"].unique().tolist())
    else:
        lista_proj = []

    ano_atual = date.today().year
    meses_opcoes = [f"{m:02d} - {MESES_PT[m]}" for m in range(1, 13)]

    with st.form("form_envolvido", clear_on_submit=True):
        ce1, ce2, ce3 = st.columns(3)
        env_ano = ce1.selectbox("📅 Ano", [ano_atual - 1, ano_atual, ano_atual + 1], index=1)
        env_mes = ce2.selectbox("🗓️ Mês", meses_opcoes)
        env_proj = ce3.selectbox("🏢 Projeto", lista_proj, index=None, placeholder="Selecione...")

        ce4, ce5, ce6 = st.columns(3)
        env_nome = ce4.text_input("👤 Nome do Envolvido", placeholder="Ex: João Silva")
        env_cargo = ce5.text_input("💼 Cargo / Função", placeholder="Ex: Analista de TI")
        env_cc = ce6.text_input("🏦 Centro de Custo", placeholder="Ex: TI-001")

        ce7, ce8 = st.columns(2)
        env_horas = ce7.number_input("⏰ Horas Dedicadas", min_value=0.0, step=1.0, format="%.1f")
        env_obs = ce8.text_input("📝 Observações", placeholder="Opcional")

        if st.form_submit_button("💾 Cadastrar Envolvido", type="primary", use_container_width=True):
            if not env_nome.strip():
                st.error("Informe o nome do envolvido.")
            elif env_proj is None:
                st.error("Selecione um projeto.")
            else:
                linha = [str(env_ano), env_mes, env_proj, env_nome.strip(),
                         env_cargo.strip(), env_cc.strip(), str(env_horas), env_obs.strip()]
                with st.spinner("Salvando envolvido..."):
                    if salvar_envolvido(linha):
                        st.toast(f"{env_nome} cadastrado em {env_proj} ({env_mes})!", icon="✅")
                        st.success("Registro salvo.")
                        st.rerun()

    if not df_env.empty:
        render_section_title("Envolvidos Cadastrados")
        fe1, fe2, fe3 = st.columns(3)
        filtro_env_ano = fe1.selectbox("Filtrar Ano", sorted(df_env["Ano"].unique(), reverse=True), index=0, key="filtro_env_ano")
        df_env_f = df_env[df_env["Ano"] == str(filtro_env_ano)]

        meses_env_disp = sorted(df_env_f["Mês"].unique(), key=mes_num) if not df_env_f.empty else []
        filtro_env_mes = fe2.multiselect("Filtrar Mês", meses_env_disp, key="filtro_env_mes")
        if filtro_env_mes:
            df_env_f = df_env_f[df_env_f["Mês"].isin(filtro_env_mes)]

        proj_env_disp = sorted(df_env_f["Projeto"].unique()) if not df_env_f.empty else []
        filtro_env_proj = fe3.multiselect("Filtrar Projeto", proj_env_disp, key="filtro_env_proj")
        if filtro_env_proj:
            df_env_f = df_env_f[df_env_f["Projeto"].isin(filtro_env_proj)]

        if not df_env_f.empty:
            st.caption(f"{len(df_env_f)} registro(s) encontrado(s)")
            st.dataframe(
                df_env_f[["Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Observações"]],
                use_container_width=True, hide_index=True,
                column_config={"Horas": st.column_config.NumberColumn("Horas", format="%.1f")}
            )
        else:
            st.info("Nenhum envolvido encontrado para os filtros selecionados.")
    else:
        st.info("Nenhum envolvido cadastrado ainda.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 11. MAIN / MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    # ✅ PRIMEIRO: senha (antes de carregar dados e desenhar o app)
    gate_password_screen()

    if "pagina" not in st.session_state:
        st.session_state.pagina = "painel"
    if "cache_buster" not in st.session_state:
        st.session_state.cache_buster = 0

    with st.spinner("Carregando dados..."):
        df_lancamentos, df_cadastros, df_envolvidos = carregar_dados(st.session_state.cache_buster)

    with st.sidebar:
        st.markdown(
            """
        <div style="padding:8px 0 24px 0;">
          <div style="font-size:22px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            🎯 Controle Orçamentário
          </div>
          <div style="font-size:13px; color:#8E8E93; margin-top:2px;">
            Gestão Financeira · v6.2
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        menu_items = [
            {"key": "painel", "icon": "📊", "label": "Painel"},
            {"key": "novo", "icon": "➕", "label": "Novo"},
            {"key": "dados", "icon": "📂", "label": "Dados"},
            {"key": "cadastros", "icon": "⚙️", "label": "Cadastros"},
        ]

        st.markdown(
            """
        <div style="font-size:11px; font-weight:600; color:#8E8E93;
             text-transform:uppercase; letter-spacing:1px; padding:0 0 8px 4px;">
            Navegação
        </div>
        """,
            unsafe_allow_html=True,
        )

        for item in menu_items:
            is_active = st.session_state.pagina == item["key"]
            if is_active:
                st.markdown(
                    f"""
                <div style="
                    display:flex; align-items:center; gap:12px;
                    padding:12px 16px; margin-bottom:4px;
                    background:rgba(0,122,255,0.1); border-radius:12px;
                    color:#007AFF; font-weight:600; font-size:15px;
                ">
                    <span style="font-size:18px; width:24px; text-align:center;">{item['icon']}</span>
                    {item['label']}
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"{item['icon']}  {item['label']}", key=f"nav_{item['key']}", use_container_width=True):
                    st.session_state.pagina = item["key"]
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Logout
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.pop("auth_ok", None)
            st.rerun()

        if st.button("🔄 Atualizar Dados", use_container_width=True):
            invalidate_cache()
            st.rerun()

        st.markdown(
            """
        <div style="margin-top:32px; font-size:11px; color:#C7C7CC; text-align:center;">
            © Controle Orçamentário
        </div>
        """,
            unsafe_allow_html=True,
        )

    if st.session_state.pagina == "painel":
        tela_resumo(df_lancamentos)
    elif st.session_state.pagina == "novo":
        tela_novo(df_lancamentos, df_cadastros)
    elif st.session_state.pagina == "dados":
        tela_dados(df_lancamentos)
    elif st.session_state.pagina == "cadastros":
        tela_cadastros(df_cadastros, df_envolvidos)


if __name__ == "__main__":
    main()
