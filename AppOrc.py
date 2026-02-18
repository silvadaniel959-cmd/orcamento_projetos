"""
Controle Orçamentário v5.0
==========================
Aplicação Streamlit para gestão de orçamentos com integração Google Sheets.
Responsivo para Desktop, iPad e iPhone.
KPIs via st.metric nativo | Menu lateral com botões | Fundo branco.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta
import gspread
import json
import os
import math
import numpy as np


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. CONFIGURAÇÃO GERAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(
    page_title="Controle Orçamentário",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. CSS — FUNDO BRANCO, BOTÕES AZUIS, RESPONSIVO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
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

    /* ══════════ Menu Sidebar — Botões de navegação ══════════ */
    .nav-btn {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;
        padding: 12px 16px;
        border: none;
        border-radius: 12px;
        background: transparent;
        color: #3A3A3C;
        font-size: 15px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
        margin-bottom: 4px;
    }
    .nav-btn:hover {
        background: rgba(0,122,255,0.06);
    }
    .nav-btn-active {
        background: rgba(0,122,255,0.1) !important;
        color: #007AFF !important;
        font-weight: 600 !important;
    }
    .nav-icon {
        font-size: 18px;
        width: 24px;
        text-align: center;
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

    /* ══════════ Multiselect Tags ══════════ */
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(0,122,255,0.1) !important;
        border-radius: 8px !important;
        color: #007AFF !important;
    }

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

    /* ══════════ RESPONSIVE: iPhone SE ══════════ */
    @media screen and (max-width: 390px) {
        .block-container { padding-left: 0.5rem; padding-right: 0.5rem; }
        [data-testid="stMetricValue"] { font-size: 16px !important; }
        h1 { font-size: 20px !important; }
    }

    /* ══════════ Safe area (notch) ══════════ */
    @supports (padding-bottom: env(safe-area-inset-bottom)) {
        .block-container { padding-bottom: calc(5rem + env(safe-area-inset-bottom)); }
    }

    /* ══════════ Touch devices ══════════ */
    @media (hover: none) and (pointer: coarse) {
        div[data-testid="stMetric"]:hover { transform: none; }
        div[data-testid="stMetric"]:active { transform: scale(0.98); }
        button { min-height: 44px !important; min-width: 44px !important; }
    }

    /* ══════════ Print ══════════ */
    @media print {
        [data-testid="stSidebar"] { display: none !important; }
        .stApp { background: white !important; }
    }
</style>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. CONSTANTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORES = {
    "primaria":   "#007AFF",
    "orcado":     "#98989D",
    "realizado":  "#34C759",
    "alerta":     "#FF3B30",
    "aviso":      "#FF9500",
    "roxo":       "#AF52DE",
    "texto":      "#1C1C1E",
    "texto2":     "#3A3A3C",
    "texto3":     "#8E8E93",
}

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. CONEXÃO GOOGLE SHEETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_resource(ttl=300)
def conectar_google():
    """Conexão com Google Sheets via Service Account. Reutilizada por 5 min."""
    try:
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_json = os.path.join(diretorio_atual, 'credentials.json')
        if os.path.exists(caminho_json):
            return gspread.service_account(filename=caminho_json)
        elif "google_credentials" in st.secrets:
            creds_data = st.secrets["google_credentials"]["content"]
            creds_dict = json.loads(creds_data) if isinstance(creds_data, str) else dict(creds_data)
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return gspread.service_account_from_dict(creds_dict)
        else:
            st.error("Credenciais não encontradas.")
            return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None


def get_worksheet(sh, nome_procurado):
    """Busca worksheet ignorando maiúsculas/minúsculas."""
    for ws in sh.worksheets():
        if ws.title.lower() == nome_procurado.lower():
            return ws
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. CARREGAMENTO DE DADOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _converter_moeda_br(series):
    """Converte Series de valores monetários brasileiros para float."""
    def _parse(v):
        try:
            if not v or str(v).strip() == "":
                return 0.0
            limpo = str(v).replace("R$", "").replace(" ", "").strip()
            if "," in limpo and "." in limpo:
                limpo = limpo.replace(".", "").replace(",", ".")
            elif "," in limpo:
                limpo = limpo.replace(",", ".")
            elif "." in limpo and limpo.count(".") == 1 and len(limpo.split(".")[1]) == 3:
                limpo = limpo.replace(".", "")
            return float(limpo)
        except (ValueError, TypeError, AttributeError):
            return 0.0
    return series.map(_parse)


@st.cache_data(ttl=120, show_spinner=False)
def carregar_dados():
    """Carrega lançamentos e cadastros do Google Sheets. Cache de 2 min."""
    client = conectar_google()
    if not client:
        return pd.DataFrame(), pd.DataFrame()
    try:
        sh = client.open("dados_app_orcamento")
        ws_lanc = get_worksheet(sh, "lançamentos")
        if not ws_lanc:
            return pd.DataFrame(), pd.DataFrame()

        dados_lanc = ws_lanc.get_all_values()
        colunas_lanc = [
            "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria",
            "Valor", "Descrição", "Parcela", "Abatido",
            "Envolvidos", "Info Gerais"
        ]
        if len(dados_lanc) <= 1:
            df_lanc = pd.DataFrame(columns=colunas_lanc)
        else:
            linhas = []
            for i, l in enumerate(dados_lanc[1:]):
                if len(l) < len(colunas_lanc):
                    l += [""] * (len(colunas_lanc) - len(l))
                linhas.append(l[:len(colunas_lanc)] + [i + 2])
            df_lanc = pd.DataFrame(linhas, columns=colunas_lanc + ["_row_id"])

        if not df_lanc.empty:
            df_lanc['Valor'] = _converter_moeda_br(df_lanc['Valor'])
            df_lanc['Ano'] = pd.to_numeric(
                df_lanc['Ano'], errors='coerce'
            ).fillna(date.today().year).astype(int)
            df_lanc['Data_dt'] = pd.to_datetime(
                df_lanc['Data'], format="%d/%m/%Y", errors='coerce'
            )

        ws_cad = get_worksheet(sh, "cadastros")
        if ws_cad:
            dados_cad = ws_cad.get_all_values()
            df_cad = pd.DataFrame(dados_cad[1:], columns=["Tipo", "Nome"]) if len(dados_cad) > 1 else pd.DataFrame(columns=["Tipo", "Nome"])
        else:
            df_cad = pd.DataFrame(columns=["Tipo", "Nome"])

        return df_lanc, df_cad
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNÇÕES DE ESCRITA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def salvar_lancamentos(lista_linhas):
    """Salva múltiplos lançamentos via append_rows (batch)."""
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet(sh, "lançamentos")
            if ws:
                ws.append_rows(lista_linhas, value_input_option='USER_ENTERED')
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    return False


def excluir_linhas_google(lista_ids):
    """Exclui linhas do Google Sheets em lote (de baixo para cima)."""
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet(sh, "lançamentos")
            if ws:
                for row_id in sorted(lista_ids, reverse=True):
                    ws.delete_rows(int(row_id))
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")
    return False


def salvar_cadastro_novo(tipo, nome):
    """Salva novo projeto ou categoria, com verificação de duplicatas."""
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet(sh, "cadastros")
            if not ws:
                ws = sh.add_worksheet(title="cadastros", rows=100, cols=2)
                ws.append_row(["Tipo", "Nome"])
            dados_existentes = ws.get_all_values()
            for row in dados_existentes[1:]:
                if (len(row) >= 2
                        and row[0].strip().lower() == tipo.strip().lower()
                        and row[1].strip().lower() == nome.strip().lower()):
                    st.warning(f"'{nome}' já existe em {tipo}.")
                    return False
            ws.append_row([tipo, nome])
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar cadastro: {e}")
    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fmt_real(v):
    """Formata valor numérico para R$ no padrão brasileiro."""
    if v < 0:
        return f"-R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(realizado, orcado):
    """Calcula percentual com proteção contra divisão por zero."""
    return (realizado / orcado * 100) if orcado else 0


def render_section_title(title):
    """Renderiza título de seção."""
    st.markdown(f"""
    <div style="font-size:11px; font-weight:600; color:#8E8E93;
         text-transform:uppercase; letter-spacing:1px; padding:16px 0 8px 0;">
        {title}
    </div>
    """, unsafe_allow_html=True)


def render_progress_bar(consumido, orcado):
    """Barra de progresso de consumo orçamentário."""
    p = min(pct(consumido, orcado), 120)
    if p <= 70:
        cor = CORES["realizado"]
        cor_bg = "rgba(52,199,89,0.12)"
    elif p <= 100:
        cor = CORES["aviso"]
        cor_bg = "rgba(255,149,0,0.12)"
    else:
        cor = CORES["alerta"]
        cor_bg = "rgba(255,59,48,0.12)"

    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #F0F0F0; border-radius:14px;
         padding:18px 20px; box-shadow:0 1px 4px rgba(0,0,0,0.04); margin-bottom:20px;">
      <div style="display:flex; justify-content:space-between; align-items:center;
           margin-bottom:10px; flex-wrap:wrap; gap:4px;">
        <span style="font-size:13px; font-weight:500; color:#3A3A3C;">
          Consumido: <strong>{fmt_real(consumido)}</strong>
        </span>
        <span style="background:{cor_bg}; color:{cor}; padding:4px 12px; border-radius:8px;
              font-size:13px; font-weight:700;">{p:.0f}%</span>
      </div>
      <div style="background:#F5F5F5; border-radius:6px; height:8px; width:100%; overflow:hidden;">
        <div style="background:{cor}; width:{min(p,100):.0f}%; height:8px; border-radius:6px;
             transition:width 0.8s cubic-bezier(0.4,0,0.2,1);"></div>
      </div>
      <div style="display:flex; justify-content:space-between; margin-top:6px;">
        <span style="font-size:11px; color:#C7C7CC;">R$ 0</span>
        <span style="font-size:11px; color:#C7C7CC;">{fmt_real(orcado)}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. TELAS DO SISTEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tela_resumo(df):
    """Tela principal: Painel Financeiro."""
    st.markdown("<h1>Painel Financeiro</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Visão consolidada do seu orçamento</p>", unsafe_allow_html=True)

    if df.empty:
        st.info("Sem dados. Acesse **Novo** para criar o primeiro lançamento.")
        return

    ano_atual = date.today().year
    anos_disponiveis = sorted(df['Ano'].unique(), reverse=True)
    default_ano = ano_atual if ano_atual in anos_disponiveis else (
        anos_disponiveis[0] if anos_disponiveis else None
    )

    # ── Filtros ──
    with st.expander("🔍 Filtros", expanded=False):
        with st.form("form_filtros_painel"):
            c1, c2 = st.columns(2)
            ano_sel = c1.selectbox("Ano", anos_disponiveis,
                                   index=anos_disponiveis.index(default_ano) if default_ano else 0)
            meses_sel = c2.multiselect("Meses", sorted(df['Mês'].unique()))
            c3, c4 = st.columns(2)
            proj_sel = c3.multiselect("Projetos", sorted(df['Projeto'].unique()))
            cat_sel = c4.multiselect("Categorias", sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else [])
            st.form_submit_button("Aplicar", type="primary", use_container_width=True)

    # Aplicar filtros
    df_f = df[df['Ano'] == ano_sel]
    if meses_sel:
        df_f = df_f[df_f['Mês'].isin(meses_sel)]
    if proj_sel:
        df_f = df_f[df_f['Projeto'].isin(proj_sel)]
    if cat_sel:
        df_f = df_f[df_f['Categoria'].isin(cat_sel)]

    # Cálculos
    orcado = df_f[df_f['Tipo'] == "Orçado"]['Valor'].sum()
    realizado = df_f[df_f['Tipo'] == "Realizado"]['Valor'].sum()
    saldo = orcado - realizado
    pct_uso = pct(realizado, orcado)
    n_proj = df_f['Projeto'].nunique()

    # ── KPIs — 4 colunas com st.metric nativo ──
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Orçado", fmt_real(orcado))
    k2.metric("✅ Realizado", fmt_real(realizado), delta=f"{pct_uso:.1f}% do orçado",
              delta_color="off")
    k3.metric("📊 Saldo Livre", fmt_real(saldo),
              delta="Disponível" if saldo >= 0 else "Estouro",
              delta_color="normal" if saldo >= 0 else "inverse")
    k4.metric("🏢 Projetos Ativos", n_proj)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Barra de consumo ──
    render_section_title("Consumo do Orçamento")
    render_progress_bar(realizado, orcado)

    # ── Gráfico: Evolução Mensal ──
    render_section_title("Evolução Mensal")
    df_mes = df_f.groupby(['Mês', 'Tipo'])['Valor'].sum().reset_index()
    if not df_mes.empty:
        df_mes['Mes_Num'] = df_mes['Mês'].apply(
            lambda x: int(x.split(' - ')[0]) if ' - ' in x else 0
        )
        df_mes = df_mes.sort_values('Mes_Num')

        fig_mes = px.bar(
            df_mes, x="Mês", y="Valor", color="Tipo", barmode='group',
            color_discrete_map={"Orçado": CORES['orcado'], "Realizado": CORES['realizado']},
        )
        fig_mes.update_traces(
            texttemplate='%{y:.2s}', textposition='outside',
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>"
        )
        fig_mes.update_layout(height=360, bargap=0.3, bargroupgap=0.08, **PLOTLY_LAYOUT)
        st.plotly_chart(fig_mes, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("Sem dados mensais para exibir.")

    # ── Gráficos lado a lado ──
    col_g1, col_g2 = st.columns(2, gap="medium")

    with col_g1:
        render_section_title("Projetos · Orçado vs Realizado")
        df_proj = (df_f.groupby(['Projeto', 'Tipo'])['Valor'].sum()
                   .unstack(fill_value=0).reset_index())
        if not df_proj.empty:
            if 'Orçado' not in df_proj.columns:
                df_proj['Orçado'] = 0.0
            if 'Realizado' not in df_proj.columns:
                df_proj['Realizado'] = 0.0
            fig_proj = go.Figure()
            fig_proj.add_trace(go.Bar(
                x=df_proj['Projeto'], y=df_proj['Orçado'],
                name='Orçado', marker_color=CORES['orcado'], opacity=0.55, width=0.55,
                hovertemplate="<b>%{x}</b><br>Orçado: R$ %{y:,.2f}<extra></extra>"
            ))
            fig_proj.add_trace(go.Bar(
                x=df_proj['Projeto'], y=df_proj['Realizado'],
                name='Realizado', marker_color=CORES['primaria'], width=0.28,
                hovertemplate="<b>%{x}</b><br>Realizado: R$ %{y:,.2f}<extra></extra>"
            ))
            fig_proj.update_layout(barmode='overlay', height=360, **PLOTLY_LAYOUT)
            st.plotly_chart(fig_proj, use_container_width=True, config=PLOTLY_CONFIG)

    with col_g2:
        render_section_title("Categorias · Top 10 (Bullet)")
        df_cat = (df_f.groupby(['Categoria', 'Tipo'])['Valor'].sum()
                  .unstack(fill_value=0).reset_index())
        if not df_cat.empty:
            if 'Orçado' not in df_cat.columns:
                df_cat['Orçado'] = 0.0
            if 'Realizado' not in df_cat.columns:
                df_cat['Realizado'] = 0.0
            df_cat = df_cat.sort_values('Orçado', ascending=True).tail(10)
            fig_bullet = go.Figure()
            fig_bullet.add_trace(go.Bar(
                y=df_cat['Categoria'], x=df_cat['Orçado'],
                name='Meta', orientation='h', marker_color='#E5E7EB', width=0.65,
                hovertemplate="<b>%{y}</b><br>Meta: R$ %{x:,.2f}<extra></extra>"
            ))
            fig_bullet.add_trace(go.Bar(
                y=df_cat['Categoria'], x=df_cat['Realizado'],
                name='Realizado', orientation='h', marker_color=CORES['realizado'], width=0.3,
                hovertemplate="<b>%{y}</b><br>Realizado: R$ %{x:,.2f}<extra></extra>"
            ))
            fig_bullet.add_trace(go.Scatter(
                y=df_cat['Categoria'], x=df_cat['Orçado'],
                mode='markers', name='Limite',
                marker=dict(symbol='line-ns-open', size=22, color=CORES['texto'], line=dict(width=2.5)),
                hovertemplate="<b>%{y}</b><br>Limite: R$ %{x:,.2f}<extra></extra>"
            ))
            fig_bullet.update_layout(barmode='overlay', height=360, **PLOTLY_LAYOUT)
            st.plotly_chart(fig_bullet, use_container_width=True, config=PLOTLY_CONFIG)

    # ── Waterfall ──
    render_section_title("Fluxo de Caixa · Waterfall")
    total_orcado = df_f[df_f['Tipo'] == 'Orçado']['Valor'].sum()
    df_gastos = (df_f[df_f['Tipo'] == 'Realizado']
                 .groupby('Categoria')['Valor'].sum()
                 .reset_index().sort_values('Valor', ascending=False))

    if total_orcado > 0 or not df_gastos.empty:
        top_n = 6
        measures = ["absolute"]
        x_data = ["Orçamento Total"]
        y_data = [total_orcado]
        text_data = [fmt_real(total_orcado)]
        saldo_wf = total_orcado

        df_top = df_gastos.head(top_n)
        outros_val = df_gastos.iloc[top_n:]['Valor'].sum() if len(df_gastos) > top_n else 0

        for _, row in df_top.iterrows():
            measures.append("relative")
            x_data.append(row['Categoria'])
            y_data.append(-row['Valor'])
            text_data.append(f"-{fmt_real(row['Valor'])}")
            saldo_wf -= row['Valor']

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
            decreasing={"marker": {"color": CORES['alerta'], "line": {"width": 0}}},
            increasing={"marker": {"color": CORES['realizado'], "line": {"width": 0}}},
            totals={"marker": {"color": CORES['primaria'], "line": {"width": 0}}},
            hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>"
        ))
        fig_wf.update_layout(height=400, waterfallgap=0.3, **PLOTLY_LAYOUT)
        st.plotly_chart(fig_wf, use_container_width=True, config=PLOTLY_CONFIG)


def tela_novo(df_lanc, df_cad):
    """Tela de criação de novos lançamentos."""
    st.markdown("<h1>Novo Lançamento</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Registre orçamentos e despesas realizadas</p>", unsafe_allow_html=True)

    if not df_cad.empty:
        lista_proj = sorted(df_cad[df_cad['Tipo'] == 'Projeto']['Nome'].unique().tolist())
        lista_cat = sorted(df_cad[df_cad['Tipo'] == 'Categoria']['Nome'].unique().tolist())
    else:
        st.warning("Nenhum Projeto ou Categoria cadastrado. Acesse **Cadastros** primeiro.")
        lista_proj, lista_cat = [], []

    with st.form("form_novo", clear_on_submit=True):
        render_section_title("Dados Principais")
        c1, c2 = st.columns(2)
        data_inicial = c1.date_input("📅 Data Inicial", date.today())
        tipo = c2.selectbox("🏷️ Tipo / Status", ["Orçado", "Realizado"],
                            help="Orçado = planejado | Realizado = efetivado")
        c3, c4 = st.columns(2)
        proj_sel = c3.selectbox("🏢 Projeto", lista_proj, index=None, placeholder="Selecione...")
        cat_sel = c4.selectbox("📂 Categoria", lista_cat, index=None, placeholder="Selecione...")

        render_section_title("Valores")
        c5, c6 = st.columns(2)
        valor = c5.number_input("💵 Valor da Parcela (R$)", min_value=0.0, step=100.0, format="%.2f")
        qtd_parcelas = c6.number_input("🔁 Nº Parcelas", min_value=1, value=1, step=1,
                                       help="Lançamentos mensais consecutivos")

        if valor > 0 and qtd_parcelas > 1:
            st.info(f"Total comprometido: **{fmt_real(valor * qtd_parcelas)}** em {qtd_parcelas} meses")

        desc = st.text_input("📝 Descrição", placeholder="Opcional — descreva a natureza do lançamento")

        render_section_title("Informações Complementares")
        c7, c8 = st.columns(2)
        envolvidos = c7.text_input("👥 Envolvidos", placeholder="Ex: João, Fornecedor X")
        info_gerais = c8.text_area("📋 Observações", placeholder="Notas livres...", height=96)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Salvar Lançamento", type="primary", use_container_width=True)

        if submitted:
            if proj_sel is None or cat_sel is None:
                st.error("Projeto e Categoria são obrigatórios.")
            elif valor == 0:
                st.error("Informe um valor maior que zero.")
            else:
                linhas = []
                for i in range(qtd_parcelas):
                    data_calc = data_inicial + relativedelta(months=i)
                    mes_str = f"{data_calc.month:02d} - {MESES_PT[data_calc.month]}"
                    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    linhas.append([
                        data_calc.strftime("%d/%m/%Y"), data_calc.year, mes_str,
                        tipo, proj_sel, cat_sel, valor_fmt, desc,
                        f"{i+1} de {qtd_parcelas}", "Não",
                        envolvidos, info_gerais
                    ])
                with st.spinner("Salvando lançamentos..."):
                    if salvar_lancamentos(linhas):
                        st.toast(f"{qtd_parcelas} lançamento(s) salvos com sucesso!", icon="✅")
                        st.balloons()


def tela_dados(df):
    """Tela de visualização, filtragem e exclusão de dados."""
    st.markdown("<h1>Base de Dados</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Visualize, filtre e gerencie todos os lançamentos</p>", unsafe_allow_html=True)

    if df.empty:
        st.info("A planilha está vazia.")
        return

    # ── Filtros ──
    with st.form("form_filtros_dados"):
        render_section_title("Filtros de Pesquisa")
        c1, c2 = st.columns(2)
        anos_disp = sorted(df['Ano'].unique(), reverse=True) if 'Ano' in df.columns else []
        ano_atual = date.today().year
        default_ano = [ano_atual] if ano_atual in anos_disp else []
        filtro_ano = c1.multiselect("📅 Ano (obrigatório)", anos_disp, default=default_ano)
        filtro_mes = c2.multiselect("🗓️ Mês", sorted(df['Mês'].unique()) if 'Mês' in df.columns else [])
        c3, c4, c5 = st.columns(3)
        filtro_proj = c3.multiselect("🏢 Projeto", sorted(df['Projeto'].unique()) if 'Projeto' in df.columns else [])
        filtro_tipo = c4.multiselect("🏷️ Tipo", sorted(df['Tipo'].unique()) if 'Tipo' in df.columns else [])
        filtro_cat = c5.multiselect("📂 Categoria", sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else [])
        st.form_submit_button("Aplicar Filtros", type="primary", use_container_width=True)

    if not filtro_ano:
        st.warning("Selecione pelo menos um **Ano** para visualizar os dados.")
        return

    # Aplicar filtros
    df_view = df.copy()
    if filtro_ano:
        df_view = df_view[df_view['Ano'].isin(filtro_ano)]
    if filtro_mes:
        df_view = df_view[df_view['Mês'].isin(filtro_mes)]
    if filtro_proj:
        df_view = df_view[df_view['Projeto'].isin(filtro_proj)]
    if filtro_tipo:
        df_view = df_view[df_view['Tipo'].isin(filtro_tipo)]
    if filtro_cat:
        df_view = df_view[df_view['Categoria'].isin(filtro_cat)]

    # ── Cálculos de consumo ──
    df_consumo = (df_view[df_view['Tipo'] == 'Realizado']
                  .groupby(['Ano', 'Mês', 'Projeto', 'Categoria'])['Valor'].sum()
                  .reset_index().rename(columns={'Valor': 'Valor_Consumido_Calc'}))
    df_final = pd.merge(df_view, df_consumo, on=['Ano', 'Mês', 'Projeto', 'Categoria'], how='left')
    df_final['Valor_Consumido_Calc'] = df_final['Valor_Consumido_Calc'].fillna(0)

    cond_orc = df_final['Tipo'] == 'Orçado'
    cond_real = df_final['Tipo'] == 'Realizado'
    df_final.loc[cond_orc, 'Valor Consumido'] = df_final.loc[cond_orc, 'Valor_Consumido_Calc']
    df_final.loc[cond_orc, 'Diferença'] = df_final.loc[cond_orc, 'Valor'] - df_final.loc[cond_orc, 'Valor Consumido']
    df_final.loc[cond_orc, 'Status'] = np.where(df_final.loc[cond_orc, 'Diferença'] < 0, "Estouro", "OK")
    df_final.loc[cond_real, 'Abatido'] = "Sim"
    df_final.loc[cond_real, 'Valor Consumido'] = None
    df_final.loc[cond_real, 'Diferença'] = None
    df_final.loc[cond_real, 'Status'] = None

    # ── Resumo — 4 colunas com st.metric nativo ──
    tot_orc = df_final[df_final['Tipo'] == 'Orçado']['Valor'].sum()
    tot_real = df_final[df_final['Tipo'] == 'Realizado']['Valor'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Registros", len(df_final))
    m2.metric("💰 Total Orçado", fmt_real(tot_orc))
    m3.metric("✅ Total Realizado", fmt_real(tot_real))
    m4.metric("📊 Saldo", fmt_real(tot_orc - tot_real),
              delta_color="normal" if tot_orc >= tot_real else "inverse")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Paginação ──
    tamanho_pagina = 50
    total_paginas = max(1, math.ceil(len(df_final) / tamanho_pagina))
    if total_paginas > 1:
        col_p, col_info = st.columns([1, 3])
        pagina_atual = col_p.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
        col_info.markdown(
            f"<p style='color:#8E8E93; font-size:13px; margin-top:32px;'>"
            f"Página {pagina_atual} de {total_paginas} · {len(df_final)} registros</p>",
            unsafe_allow_html=True)
    else:
        pagina_atual = 1

    inicio = (pagina_atual - 1) * tamanho_pagina
    fim = inicio + tamanho_pagina
    df_paginado = df_final.iloc[inicio:fim].copy()
    df_paginado["Excluir"] = False

    colunas_show = [
        "Data", "Mês", "Tipo", "Projeto", "Categoria",
        "Valor", "Valor Consumido", "Diferença", "Status",
        "Descrição", "Envolvidos", "Info Gerais", "Parcela", "Excluir"
    ]
    cols_show = [c for c in colunas_show if c in df_paginado.columns]

    df_edited = st.data_editor(
        df_paginado[cols_show],
        column_config={
            "Excluir": st.column_config.CheckboxColumn("🗑️", width="small", default=False),
            "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "Valor Consumido": st.column_config.NumberColumn("Consumido", format="R$ %.2f", disabled=True),
            "Diferença": st.column_config.NumberColumn("Diferença", format="R$ %.2f", disabled=True),
            "Status": st.column_config.TextColumn("Status", disabled=True),
        },
        disabled=["Data", "Mês", "Tipo", "Projeto", "Categoria",
                  "Valor", "Descrição", "Parcela", "Envolvidos", "Info Gerais"],
        hide_index=True, use_container_width=True,
        key=f"editor_{pagina_atual}"
    )

    # ── Exclusão ──
    linhas_excluir = df_edited[df_edited["Excluir"] == True]
    if not linhas_excluir.empty:
        st.error(f"⚠️ **{len(linhas_excluir)} registro(s)** marcado(s) para exclusão. Esta ação não pode ser desfeita.")
        if st.button("🗑️ Confirmar Exclusão", type="primary", use_container_width=True):
            if "_row_id" in df_view.columns:
                ids_reais = df_paginado.loc[linhas_excluir.index, "_row_id"].tolist()
                with st.spinner("Excluindo registros..."):
                    if excluir_linhas_google(ids_reais):
                        st.success("Registros excluídos com sucesso!")
                        st.rerun()


def tela_cadastros(df_cad):
    """Tela de gerenciamento de projetos e categorias."""
    st.markdown("<h1>Cadastros</h1><p style='color:#8E8E93; margin-top:-8px; margin-bottom:20px;'>Gerencie projetos e categorias do sistema</p>", unsafe_allow_html=True)

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
            proj_lista = df_cad[df_cad['Tipo'] == 'Projeto'][['Nome']].reset_index(drop=True)
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
            cat_lista = df_cad[df_cad['Tipo'] == 'Categoria'][['Nome']].reset_index(drop=True)
            if not cat_lista.empty:
                st.caption(f"{len(cat_lista)} categoria(s) cadastrada(s)")
                st.dataframe(cat_lista, use_container_width=True, hide_index=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. MENU PRINCIPAL — BOTÕES NA SIDEBAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    """Ponto de entrada principal da aplicação."""

    # Inicializar estado da navegação
    if "pagina" not in st.session_state:
        st.session_state.pagina = "painel"

    with st.spinner("Carregando dados..."):
        df_lancamentos, df_cadastros = carregar_dados()

    # ── Sidebar com botões ──
    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 24px 0;">
          <div style="font-size:22px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            🎯 Controle Orçamentário
          </div>
          <div style="font-size:13px; color:#8E8E93; margin-top:2px;">
            Gestão Financeira
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Definição dos itens do menu
        menu_items = [
            {"key": "painel",    "icon": "📊", "label": "Painel"},
            {"key": "novo",      "icon": "➕", "label": "Novo"},
            {"key": "dados",     "icon": "📂", "label": "Dados"},
            {"key": "cadastros", "icon": "⚙️", "label": "Cadastros"},
        ]

        st.markdown("""
        <div style="font-size:11px; font-weight:600; color:#8E8E93;
             text-transform:uppercase; letter-spacing:1px; padding:0 0 8px 4px;">
            Navegação
        </div>
        """, unsafe_allow_html=True)

        for item in menu_items:
            is_active = st.session_state.pagina == item["key"]

            if is_active:
                # Botão ativo — estilo destacado
                st.markdown(f"""
                <div style="
                    display:flex; align-items:center; gap:12px;
                    padding:12px 16px; margin-bottom:4px;
                    background:rgba(0,122,255,0.1); border-radius:12px;
                    color:#007AFF; font-weight:600; font-size:15px;
                ">
                    <span style="font-size:18px; width:24px; text-align:center;">{item['icon']}</span>
                    {item['label']}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Botão inativo — clicável
                if st.button(
                    f"{item['icon']}  {item['label']}",
                    key=f"nav_{item['key']}",
                    use_container_width=True
                ):
                    st.session_state.pagina = item["key"]
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Mini resumo na sidebar ──
        if not df_lancamentos.empty:
            ano_atual = date.today().year
            df_ano = df_lancamentos[df_lancamentos['Ano'] == ano_atual]
            tot_orc = df_ano[df_ano['Tipo'] == 'Orçado']['Valor'].sum()
            tot_real = df_ano[df_ano['Tipo'] == 'Realizado']['Valor'].sum()
            uso_pct = pct(tot_real, tot_orc)

            if uso_pct <= 85:
                cor_sb = CORES['realizado']
            elif uso_pct <= 100:
                cor_sb = CORES['aviso']
            else:
                cor_sb = CORES['alerta']

            st.markdown(f"""
            <div style="background:#F5F5F5; border:1px solid #EBEBEB; border-radius:12px;
                 padding:14px 16px; margin-bottom:16px;">
              <div style="font-size:11px; font-weight:600; color:#8E8E93; text-transform:uppercase;
                   letter-spacing:0.8px; margin-bottom:8px;">
                {ano_atual} · Resumo
              </div>
              <div style="font-size:15px; font-weight:700; color:#1C1C1E;">{fmt_real(tot_real)}</div>
              <div style="font-size:12px; color:#8E8E93; margin-top:2px;">
                de {fmt_real(tot_orc)} orçados
              </div>
              <div style="background:#E5E5E5; border-radius:4px; height:5px; margin-top:10px; overflow:hidden;">
                <div style="background:{cor_sb}; width:{min(uso_pct,100):.0f}%; height:5px;
                     border-radius:4px; transition:width 0.6s ease;"></div>
              </div>
              <div style="font-size:11px; color:{cor_sb}; font-weight:600; margin-top:4px;">
                {uso_pct:.0f}% consumido
              </div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("""
        <div style="margin-top:32px; font-size:11px; color:#C7C7CC; text-align:center;">
            v5.0 · Responsivo
        </div>
        """, unsafe_allow_html=True)

    # ── Roteamento de telas ──
    if st.session_state.pagina == "painel":
        tela_resumo(df_lancamentos)
    elif st.session_state.pagina == "novo":
        tela_novo(df_lancamentos, df_cadastros)
    elif st.session_state.pagina == "dados":
        tela_dados(df_lancamentos)
    elif st.session_state.pagina == "cadastros":
        tela_cadastros(df_cadastros)


if __name__ == "__main__":
    main()
