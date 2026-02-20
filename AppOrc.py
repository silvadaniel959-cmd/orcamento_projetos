"""
Controle Orçamentário v5.1
==========================
Aplicação Streamlit para gestão de orçamentos com integração Google Sheets.
Responsivo para Desktop, iPad e iPhone.
KPIs via st.metric nativo | Menu lateral com botões | Fundo branco.

Changelog v5.1:
- [B1] FIX: carregar_dados() padronizado para sempre retornar 3 DataFrames
- [B2] FIX: exclusão usa reset_index() para garantir alinhamento de índices
- [B3] FIX: _converter_moeda_br() não confunde decimal com separador de milhar
- [B4] FIX: meses filtrados pelo ano selecionado no Painel
- [B5] FIX: key do data_editor inclui hash dos filtros
- [B6] FIX: excluir_linhas_google() retorna False explícito em falha de auth
- [B7] FIX: qtd_parcelas limitado a 120 (max_value)
- [B8] FIX: Waterfall exibe st.info() quando sem dados
- [P1] PERF: exclusão em batch via Sheets API v4 (1 chamada ao invés de N)
- [P2] PERF: cache separado para lançamentos (60s) e cadastros (600s)
- [P3] PERF: conectar_google() sem TTL desnecessário
- [P4] PERF: HTML de progress rows via join() ao invés de concatenação
- [P5] PERF: salvar_cadastro_novo() verifica duplicata no df em memória
- [N1] NOVO: Banner de alertas de estouro no Painel
- [N2] NOVO: KPI de Forecast (previsão de estouro)
- [N3] NOVO: Exportação CSV e Excel na tela de Dados
- [N4] NOVO: Custo de mão de obra (Valor/Hora) nos Envolvidos
- [N7] FIX: campo Abatido removido da lógica morta
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
import io

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
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
}
/* ══════════ FUNDO BRANCO ══════════ */
.stApp, .stApp > header, [data-testid="stHeader"] { background: #FFFFFF !important; }
.block-container {
    padding: 1.5rem 2rem 5rem 2rem;
    max-width: 1400px;
    background: #FFFFFF !important;
}
/* ══════════ Sidebar ══════════ */
[data-testid="stSidebar"] { background: #FAFAFA; border-right: 1px solid #F0F0F0; }
/* ══════════ Metric Cards ══════════ */
div[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #F0F0F0; border-radius: 14px;
    padding: 18px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
div[data-testid="stMetric"]:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
div[data-testid="stMetric"] label { font-size: 11px !important; font-weight: 600 !important; color: #8E8E93 !important; letter-spacing: 0.5px; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700 !important; color: #1C1C1E !important; letter-spacing: -0.5px; }
[data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 500 !important; }
/* ══════════ Alert Banner ══════════ */
.alert-banner {
    background: rgba(255,59,48,0.06); border: 1px solid rgba(255,59,48,0.2);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 16px;
}
.alert-banner-warn {
    background: rgba(255,149,0,0.06); border: 1px solid rgba(255,149,0,0.2);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 16px;
}
/* ══════════ Forms ══════════ */
[data-testid="stForm"] { background: #FAFAFA; border: 1px solid #F0F0F0; border-radius: 14px; padding: 24px; }
/* ══════════ Inputs ══════════ */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stMultiSelect > div > div,
.stDateInput > div > div > input {
    border-radius: 10px !important; border: 1.5px solid #E5E5EA !important;
    background: #FFFFFF !important; font-size: 15px !important; min-height: 44px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #007AFF !important; box-shadow: 0 0 0 3px rgba(0,122,255,0.1) !important;
}
/* ══════════ BOTÕES AZUIS ══════════ */
.stButton > button[kind="primary"],
.stFormSubmitButton > button,
button[kind="primary"],
div.stFormSubmitButton > button {
    background: #007AFF !important; color: white !important; border: none !important;
    border-radius: 12px !important; padding: 12px 28px !important;
    font-size: 15px !important; font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(0,122,255,0.25) !important; min-height: 44px;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover { background: #0066D6 !important; transform: translateY(-1px); }
.stButton > button:not([kind="primary"]) {
    border-radius: 12px !important; font-weight: 500 !important; min-height: 44px;
    border: 1.5px solid #E5E5EA !important; background: #FFFFFF !important;
}
/* ══════════ Data Editor ══════════ */
.stDataFrame, [data-testid="stDataEditor"] { border-radius: 12px !important; overflow: hidden; border: 1px solid #F0F0F0 !important; }
[data-testid="stDataEditor"] > div { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
/* ══════════ Headings ══════════ */
h1 { font-size: 28px !important; font-weight: 700 !important; color: #1C1C1E !important; }
h2 { font-size: 22px !important; font-weight: 600 !important; color: #1C1C1E !important; }
h3 { font-size: 17px !important; font-weight: 600 !important; color: #1C1C1E !important; }
/* ══════════ RESPONSIVE: iPad ══════════ */
@media screen and (max-width: 1024px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; max-width: 100%; }
    [data-testid="stMetricValue"] { font-size: 20px !important; }
}
/* ══════════ RESPONSIVE: iPhone ══════════ */
@media screen and (max-width: 768px) {
    .block-container { padding: 0.8rem 0.75rem 5rem 0.75rem; }
    div[data-testid="stMetric"] { padding: 14px 16px; }
    [data-testid="stMetricValue"] { font-size: 18px !important; }
    h1 { font-size: 22px !important; }
}
/* ══════════ Touch devices ══════════ */
@media (hover: none) and (pointer: coarse) {
    div[data-testid="stMetric"]:hover { transform: none; }
    button { min-height: 44px !important; min-width: 44px !important; }
}
</style>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. CONSTANTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORES = {
    "primaria": "#007AFF", "orcado": "#98989D", "realizado": "#34C759",
    "alerta": "#FF3B30", "aviso": "#FF9500", "roxo": "#AF52DE",
    "texto": "#1C1C1E", "texto2": "#3A3A3C", "texto3": "#8E8E93",
}

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

PLOTLY_LAYOUT = dict(
    font_family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
    font_color="#3A3A3C", paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
    margin=dict(l=8, r=8, t=8, b=48),
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5,
                bgcolor="rgba(0,0,0,0)", font=dict(size=12, color="#8E8E93")),
    xaxis=dict(showgrid=False, showline=False, tickfont=dict(size=11, color="#8E8E93"), fixedrange=True),
    yaxis=dict(showgrid=True, gridcolor="#F5F5F5", gridwidth=1, showline=False,
               tickfont=dict(size=11, color="#8E8E93"), fixedrange=True),
    hoverlabel=dict(bgcolor="white", bordercolor="#E5E5EA", font_size=13, font_color="#1C1C1E"),
    dragmode=False,
)

PLOTLY_CONFIG = {
    "displayModeBar": False, "scrollZoom": False,
    "doubleClick": False, "showTips": False, "responsive": True,
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. CONEXÃO GOOGLE SHEETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# [P3] FIX: sem TTL — gspread renova tokens automaticamente
@st.cache_resource
def conectar_google():
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
    for ws in sh.worksheets():
        if ws.title.lower() == nome_procurado.lower():
            return ws
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. CARREGAMENTO DE DADOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _converter_moeda_br(series):
    """[B3] FIX: distingue decimal de separador de milhar corretamente."""
    def _parse(v):
        try:
            if not v or str(v).strip() == "":
                return 0.0
            limpo = str(v).replace("R$", "").replace(" ", "").strip()
            if "," in limpo and "." in limpo:
                limpo = limpo.replace(".", "").replace(",", ".")
            elif "," in limpo:
                limpo = limpo.replace(",", ".")
            elif "." in limpo:
                partes = limpo.split(".")
                # Só remove o ponto se for separador de milhar real
                if (len(partes) == 2 and len(partes[1]) == 3
                        and partes[0].isdigit() and partes[1].isdigit()):
                    limpo = limpo.replace(".", "")
                # else: é decimal (ex: "1.5"), mantém
            return float(limpo)
        except (ValueError, TypeError, AttributeError):
            return 0.0
    return series.map(_parse)


# [P2] FIX: cache separado — lançamentos mudam frequente, cadastros raramente
@st.cache_data(ttl=60, show_spinner=False)
def carregar_lancamentos():
    """[B1] FIX: sempre retorna DataFrame (nunca None ou 2 valores)."""
    client = conectar_google()
    if not client:
        return pd.DataFrame()
    try:
        sh = client.open("dados_app_orcamento")
        ws_lanc = get_worksheet(sh, "lançamentos")
        if not ws_lanc:
            return pd.DataFrame()
        dados_lanc = ws_lanc.get_all_values()
        colunas_lanc = [
            "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria",
            "Valor", "Descrição", "Parcela", "Abatido", "Envolvidos", "Info Gerais"
        ]
        if len(dados_lanc) <= 1:
            return pd.DataFrame(columns=colunas_lanc)
        linhas = []
        for i, l in enumerate(dados_lanc[1:]):
            if len(l) < len(colunas_lanc):
                l += [""] * (len(colunas_lanc) - len(l))
            linhas.append(l[:len(colunas_lanc)] + [i + 2])
        df_lanc = pd.DataFrame(linhas, columns=colunas_lanc + ["_row_id"])
        df_lanc['Valor'] = _converter_moeda_br(df_lanc['Valor'])
        df_lanc['Ano'] = pd.to_numeric(df_lanc['Ano'], errors='coerce').fillna(date.today().year).astype(int)
        df_lanc['Data_dt'] = pd.to_datetime(df_lanc['Data'], format="%d/%m/%Y", errors='coerce')
        return df_lanc
    except Exception as e:
        st.error(f"Erro ao carregar lançamentos: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)  # 10 min — cadastros mudam raramente
def carregar_cadastros():
    client = conectar_google()
    if not client:
        return pd.DataFrame(columns=["Tipo", "Nome"])
    try:
        sh = client.open("dados_app_orcamento")
        ws_cad = get_worksheet(sh, "cadastros")
        if not ws_cad:
            return pd.DataFrame(columns=["Tipo", "Nome"])
        dados_cad = ws_cad.get_all_values()
        if len(dados_cad) > 1:
            return pd.DataFrame(dados_cad[1:], columns=["Tipo", "Nome"])
        return pd.DataFrame(columns=["Tipo", "Nome"])
    except Exception as e:
        st.error(f"Erro ao carregar cadastros: {e}")
        return pd.DataFrame(columns=["Tipo", "Nome"])


@st.cache_data(ttl=120, show_spinner=False)
def carregar_envolvidos():
    client = conectar_google()
    if not client:
        return pd.DataFrame()
    # [N4] NOVO: coluna Valor/Hora adicionada
    cols_env = ["Ano", "Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo", "Horas", "Valor/Hora", "Observações"]
    try:
        sh = client.open("dados_app_orcamento")
        ws_env = get_worksheet(sh, "envolvidos")
        if not ws_env:
            return pd.DataFrame(columns=cols_env)
        dados_env = ws_env.get_all_values()
        if len(dados_env) <= 1:
            return pd.DataFrame(columns=cols_env)
        linhas_env = []
        for l in dados_env[1:]:
            if len(l) < len(cols_env):
                l += [""] * (len(cols_env) - len(l))
            linhas_env.append(l[:len(cols_env)])
        return pd.DataFrame(linhas_env, columns=cols_env)
    except Exception as e:
        st.error(f"Erro ao carregar envolvidos: {e}")
        return pd.DataFrame(columns=cols_env)


def carregar_dados():
    """Wrapper de compatibilidade — retorna sempre 3 DataFrames."""
    return carregar_lancamentos(), carregar_cadastros(), carregar_envolvidos()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNÇÕES DE ESCRITA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def salvar_lancamentos(lista_linhas):
    client = conectar_google()
    if not client:
        st.error("Falha de autenticação.")
        return False
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


# [P1] FIX: batch delete — 1 chamada de API ao invés de N
def excluir_linhas_google(lista_ids):
    """Exclui linhas em batch via Sheets API v4 (batchUpdate)."""
    client = conectar_google()
    # [B6] FIX: retorno explícito em falha de auth
    if not client:
        st.error("Falha de autenticação. Não foi possível excluir.")
        return False
    try:
        sh = client.open("dados_app_orcamento")
        ws = get_worksheet(sh, "lançamentos")
        if not ws:
            return False
        # Ordem decrescente para não deslocar índices durante exclusão
        requests = [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": ws.id,
                        "dimension": "ROWS",
                        "startIndex": int(row_id) - 1,  # 0-indexed
                        "endIndex": int(row_id)
                    }
                }
            }
            for row_id in sorted(lista_ids, reverse=True)
        ]
        sh.batch_update({"requests": requests})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False


def salvar_envolvido(dados_linha):
    client = conectar_google()
    if not client:
        st.error("Falha de autenticação.")
        return False
    try:
        sh = client.open("dados_app_orcamento")
        ws = get_worksheet(sh, "envolvidos")
        if not ws:
            ws = sh.add_worksheet(title="envolvidos", rows=500, cols=9)
            ws.append_row(["Ano", "Mês", "Projeto", "Nome", "Cargo/Função",
                           "Centro de Custo", "Horas", "Valor/Hora", "Observações"])
        ws.append_row(dados_linha, value_input_option='USER_ENTERED')
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar envolvido: {e}")
        return False


# [P5] FIX: verifica duplicata no df em memória, sem nova chamada à API
def salvar_cadastro_novo(tipo, nome, df_cad_atual=None):
    if df_cad_atual is not None and not df_cad_atual.empty:
        existe = df_cad_atual[
            (df_cad_atual['Tipo'].str.strip().str.lower() == tipo.strip().lower()) &
            (df_cad_atual['Nome'].str.strip().str.lower() == nome.strip().lower())
        ]
        if not existe.empty:
            st.warning(f"'{nome}' já existe em {tipo}.")
            return False
    client = conectar_google()
    if not client:
        st.error("Falha de autenticação.")
        return False
    try:
        sh = client.open("dados_app_orcamento")
        ws = get_worksheet(sh, "cadastros")
        if not ws:
            ws = sh.add_worksheet(title="cadastros", rows=100, cols=2)
            ws.append_row(["Tipo", "Nome"])
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
    if v < 0:
        return f"-R$ {abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def pct(realizado, orcado):
    return (realizado / orcado * 100) if orcado else 0

def render_section_title(title):
    st.markdown(f"""
    <div style="font-size:11px; font-weight:600; color:#8E8E93; text-transform:uppercase;
                letter-spacing:1px; padding:16px 0 8px 0;">{title}</div>
    """, unsafe_allow_html=True)

def render_progress_bar(consumido, orcado, label=None):
    p = min(pct(consumido, orcado), 120)
    cor = CORES["realizado"] if p <= 70 else (CORES["aviso"] if p <= 100 else CORES["alerta"])
    cor_bg = "rgba(52,199,89,0.12)" if p <= 70 else ("rgba(255,149,0,0.12)" if p <= 100 else "rgba(255,59,48,0.12)")
    label_html = f'<div style="font-size:14px; font-weight:600; color:#1C1C1E; margin-bottom:10px;">{label}</div>' if label else ''
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #F0F0F0; border-radius:14px;
                padding:18px 20px; box-shadow:0 1px 4px rgba(0,0,0,0.04); margin-bottom:20px;">
        {label_html}
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <span style="font-size:13px; font-weight:500; color:#3A3A3C;">
                Consumido: <strong>{fmt_real(consumido)}</strong>
            </span>
            <span style="background:{cor_bg}; color:{cor}; padding:4px 12px;
                         border-radius:8px; font-size:13px; font-weight:700;">{p:.0f}%</span>
        </div>
        <div style="background:#F5F5F5; border-radius:6px; height:8px; width:100%; overflow:hidden;">
            <div style="background:{cor}; width:{min(p,100):.0f}%; height:8px; border-radius:6px;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:6px;">
            <span style="font-size:11px; color:#C7C7CC;">R$ 0</span>
            <span style="font-size:11px; color:#C7C7CC;">{fmt_real(orcado)}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_progress_row(nome, consumido, orcado):
    """[P4] FIX: retorna string (usada com join() ao invés de concatenação)."""
    p = min(pct(consumido, orcado), 120)
    cor = CORES["realizado"] if p <= 70 else (CORES["aviso"] if p <= 100 else CORES["alerta"])
    cor_bg = "rgba(52,199,89,0.12)" if p <= 70 else ("rgba(255,149,0,0.12)" if p <= 100 else "rgba(255,59,48,0.12)")
    saldo = orcado - consumido
    saldo_cor = CORES['realizado'] if saldo >= 0 else CORES['alerta']
    return (
        f'<div style="padding:14px 0;border-bottom:1px solid #F5F5F5;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        f'<span style="font-size:14px;font-weight:600;color:#1C1C1E;">{nome}</span>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:12px;color:#8E8E93;">{fmt_real(consumido)} / {fmt_real(orcado)}</span>'
        f'<span style="background:{cor_bg};color:{cor};padding:2px 10px;border-radius:6px;font-size:12px;font-weight:700;">{p:.0f}%</span>'
        f'</div></div>'
        f'<div style="background:#F5F5F5;border-radius:4px;height:6px;width:100%;overflow:hidden;">'
        f'<div style="background:{cor};width:{min(p,100):.0f}%;height:6px;border-radius:4px;"></div>'
        f'</div>'
        f'<div style="display:flex;justify-content:flex-end;margin-top:4px;">'
        f'<span style="font-size:11px;color:{saldo_cor};font-weight:500;">Saldo: {fmt_real(saldo)}</span>'
        f'</div></div>'
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. TELAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def tela_resumo(df):
    st.markdown("<h1>Painel Financeiro</h1><p style='color:#8E8E93;margin-top:-8px;margin-bottom:20px;'>Visão consolidada do seu orçamento</p>", unsafe_allow_html=True)
    if df.empty:
        st.info("Sem dados. Acesse **Novo** para criar o primeiro lançamento.")
        return

    anos_disponiveis = sorted(df['Ano'].unique(), reverse=True)
    ano_atual = date.today().year
    default_ano = ano_atual if ano_atual in anos_disponiveis else (anos_disponiveis[0] if anos_disponiveis else None)

    with st.expander("🔍 Filtros", expanded=False):
        with st.form("form_filtros_painel"):
            c1, c2 = st.columns(2)
            ano_sel = c1.selectbox("Ano", anos_disponiveis,
                                   index=anos_disponiveis.index(default_ano) if default_ano else 0)
            # [B4] FIX: meses filtrados pelo ano selecionado
            meses_do_ano = sorted(df[df['Ano'] == ano_sel]['Mês'].unique())
            meses_sel = c2.multiselect("Meses", meses_do_ano)
            c3, c4 = st.columns(2)
            proj_sel = c3.multiselect("Projetos", sorted(df['Projeto'].unique()))
            cat_sel = c4.multiselect("Categorias", sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else [])
            st.form_submit_button("Aplicar", type="primary", use_container_width=True)

    df_f = df[df['Ano'] == ano_sel]
    if meses_sel: df_f = df_f[df_f['Mês'].isin(meses_sel)]
    if proj_sel:  df_f = df_f[df_f['Projeto'].isin(proj_sel)]
    if cat_sel:   df_f = df_f[df_f['Categoria'].isin(cat_sel)]

    orcado    = df_f[df_f['Tipo'] == "Orçado"]['Valor'].sum()
    realizado = df_f[df_f['Tipo'] == "Realizado"]['Valor'].sum()
    saldo     = orcado - realizado
    pct_uso   = pct(realizado, orcado)
    n_proj    = df_f['Projeto'].nunique()

    # [N1] NOVO: Banner de alertas de estouro
    df_proj_alerta = (df_f.groupby(['Projeto', 'Tipo'])['Valor'].sum()
                      .unstack(fill_value=0).reset_index())
    if not df_proj_alerta.empty:
        if 'Orçado'    not in df_proj_alerta.columns: df_proj_alerta['Orçado']    = 0.0
        if 'Realizado' not in df_proj_alerta.columns: df_proj_alerta['Realizado'] = 0.0
        estouros   = df_proj_alerta[df_proj_alerta['Realizado'] > df_proj_alerta['Orçado']]
        alertas_90 = df_proj_alerta[
            (df_proj_alerta['Realizado'] / df_proj_alerta['Orçado'].replace(0, float('inf'))) >= 0.9
        ]
        alertas_90 = alertas_90[~alertas_90['Projeto'].isin(estouros['Projeto'])]
        if not estouros.empty:
            nomes = ", ".join(estouros['Projeto'].tolist())
            st.markdown(f'<div class="alert-banner">🚨 <strong>Estouro de orçamento:</strong> {nomes}</div>', unsafe_allow_html=True)
        if not alertas_90.empty:
            nomes_90 = ", ".join(alertas_90['Projeto'].tolist())
            st.markdown(f'<div class="alert-banner-warn">⚠️ <strong>Acima de 90%:</strong> {nomes_90}</div>', unsafe_allow_html=True)

    # [N2] NOVO: Forecast de estouro
    forecast_label = "—"
    df_mes_real = df_f[df_f['Tipo'] == 'Realizado'].copy()
    if not df_mes_real.empty and 'Data_dt' in df_mes_real.columns:
        df_mes_real['mes_num'] = df_mes_real['Data_dt'].dt.to_period('M')
        burn_mensal = df_mes_real.groupby('mes_num')['Valor'].sum()
        if len(burn_mensal) > 0:
            burn_rate = burn_mensal.mean()
            if burn_rate > 0 and saldo > 0:
                forecast_label = f"~{saldo / burn_rate:.1f} meses"
            elif saldo <= 0:
                forecast_label = "Esgotado"

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("💰 Orçado",       fmt_real(orcado))
    k2.metric("✅ Realizado",    fmt_real(realizado), delta=f"{pct_uso:.1f}% do orçado", delta_color="off")
    k3.metric("📊 Saldo Livre",  fmt_real(saldo),
              delta="Disponível" if saldo >= 0 else "Estouro",
              delta_color="normal" if saldo >= 0 else "inverse")
    k4.metric("🏢 Projetos",     n_proj)
    k5.metric("🔮 Previsão Saldo", forecast_label, delta_color="off")

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    render_section_title("Consumo do Orçamento · Geral")
    render_progress_bar(realizado, orcado)

    render_section_title("Consumo por Projeto")
    df_proj = (df_f.groupby(['Projeto', 'Tipo'])['Valor'].sum().unstack(fill_value=0).reset_index())
    if not df_proj.empty:
        if 'Orçado'    not in df_proj.columns: df_proj['Orçado']    = 0.0
        if 'Realizado' not in df_proj.columns: df_proj['Realizado'] = 0.0
        df_proj = df_proj.sort_values('Orçado', ascending=False)
        # [P4] FIX: join() ao invés de concatenação em loop
        rows_html = "".join(render_progress_row(r['Projeto'], r['Realizado'], r['Orçado']) for _, r in df_proj.iterrows())
        st.markdown(f'<div style="background:#FFFFFF;border:1px solid #F0F0F0;border-radius:14px;padding:6px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.04);margin-bottom:20px;">{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.info("Sem dados de projetos.")

    render_section_title("Consumo por Categoria")
    df_cat = (df_f.groupby(['Categoria', 'Tipo'])['Valor'].sum().unstack(fill_value=0).reset_index())
    if not df_cat.empty:
        if 'Orçado'    not in df_cat.columns: df_cat['Orçado']    = 0.0
        if 'Realizado' not in df_cat.columns: df_cat['Realizado'] = 0.0
        df_cat = df_cat.sort_values('Orçado', ascending=False)
        rows_html = "".join(render_progress_row(r['Categoria'], r['Realizado'], r['Orçado']) for _, r in df_cat.iterrows())
        st.markdown(f'<div style="background:#FFFFFF;border:1px solid #F0F0F0;border-radius:14px;padding:6px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.04);margin-bottom:20px;">{rows_html}</div>', unsafe_allow_html=True)
    else:
        st.info("Sem dados de categorias.")

    render_section_title("Evolução Mensal")
    df_mes = df_f.groupby(['Mês', 'Tipo'])['Valor'].sum().reset_index()
    if not df_mes.empty:
        df_mes['Mes_Num'] = df_mes['Mês'].apply(lambda x: int(x.split(' - ')[0]) if ' - ' in x else 0)
        df_mes = df_mes.sort_values('Mes_Num')
        fig_mes = px.bar(df_mes, x="Mês", y="Valor", color="Tipo", barmode='group',
                         color_discrete_map={"Orçado": CORES['orcado'], "Realizado": CORES['realizado']})
        fig_mes.update_traces(texttemplate='%{y:.2s}', textposition='outside', marker_line_width=0,
                              hovertemplate="<b>%{x}</b><br>R$ %{y:,.2f}<extra></extra>")
        fig_mes.update_layout(height=360, bargap=0.3, bargroupgap=0.08, **PLOTLY_LAYOUT)
        st.plotly_chart(fig_mes, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("Sem dados mensais.")

    render_section_title("Fluxo de Caixa · Waterfall")
    total_orcado = df_f[df_f['Tipo'] == 'Orçado']['Valor'].sum()
    df_gastos = (df_f[df_f['Tipo'] == 'Realizado'].groupby('Categoria')['Valor'].sum()
                 .reset_index().sort_values('Valor', ascending=False))
    if total_orcado > 0 or not df_gastos.empty:
        top_n = 6
        measures, x_data, y_data, text_data = ["absolute"], ["Orçamento Total"], [total_orcado], [fmt_real(total_orcado)]
        saldo_wf = total_orcado
        for _, row in df_gastos.head(top_n).iterrows():
            measures.append("relative"); x_data.append(row['Categoria'])
            y_data.append(-row['Valor']); text_data.append(f"-{fmt_real(row['Valor'])}"); saldo_wf -= row['Valor']
        outros_val = df_gastos.iloc[top_n:]['Valor'].sum() if len(df_gastos) > top_n else 0
        if outros_val > 0:
            measures.append("relative"); x_data.append("Outros")
            y_data.append(-outros_val); text_data.append(f"-{fmt_real(outros_val)}"); saldo_wf -= outros_val
        measures.append("total"); x_data.append("Saldo Final"); y_data.append(0); text_data.append(fmt_real(saldo_wf))
        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=measures, x=x_data, textposition="outside",
            text=text_data, y=y_data,
            connector={"line": {"color": "#E5E5EA", "width": 1, "dash": "dot"}},
            decreasing={"marker": {"color": CORES['alerta'],   "line": {"width": 0}}},
            increasing={"marker": {"color": CORES['realizado'], "line": {"width": 0}}},
            totals={"marker":    {"color": CORES['primaria'],   "line": {"width": 0}}},
            hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>"
        ))
        fig_wf.update_layout(height=400, waterfallgap=0.3, **PLOTLY_LAYOUT)
        st.plotly_chart(fig_wf, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        # [B8] FIX: fallback visual
        st.info("Sem dados suficientes para o gráfico Waterfall.")


def tela_novo(df_lanc, df_cad):
    st.markdown("<h1>Novo Lançamento</h1><p style='color:#8E8E93;margin-top:-8px;margin-bottom:20px;'>Registre orçamentos e despesas realizadas</p>", unsafe_allow_html=True)
    if not df_cad.empty:
        lista_proj = sorted(df_cad[df_cad['Tipo'] == 'Projeto']['Nome'].unique().tolist())
        lista_cat  = sorted(df_cad[df_cad['Tipo'] == 'Categoria']['Nome'].unique().tolist())
    else:
        st.warning("Nenhum Projeto ou Categoria cadastrado. Acesse **Cadastros** primeiro.")
        lista_proj, lista_cat = [], []

    with st.form("form_novo", clear_on_submit=True):
        render_section_title("Dados Principais")
        c1, c2 = st.columns(2)
        data_inicial = c1.date_input("📅 Data Inicial", date.today())
        tipo = c2.selectbox("🏷️ Tipo / Status", ["Orçado", "Realizado"])
        c3, c4 = st.columns(2)
        proj_sel = c3.selectbox("🏢 Projeto",   lista_proj, index=None, placeholder="Selecione...")
        cat_sel  = c4.selectbox("📂 Categoria", lista_cat,  index=None, placeholder="Selecione...")
        render_section_title("Valores")
        c5, c6 = st.columns(2)
        valor = c5.number_input("💵 Valor da Parcela (R$)", min_value=0.0, step=100.0, format="%.2f")
        # [B7] FIX: max_value=120 para evitar timeout de API
        qtd_parcelas = c6.number_input("🔁 Nº Parcelas", min_value=1, max_value=120, value=1, step=1,
                                       help="Lançamentos mensais consecutivos (máx. 120)")
        if valor > 0 and qtd_parcelas > 1:
            st.info(f"Total comprometido: **{fmt_real(valor * qtd_parcelas)}** em {qtd_parcelas} meses")
        desc = st.text_input("📝 Descrição", placeholder="Opcional")
        render_section_title("Informações Complementares")
        c7, c8 = st.columns(2)
        envolvidos  = c7.text_input("👥 Envolvidos",  placeholder="Ex: João, Fornecedor X")
        info_gerais = c8.text_area("📋 Observações", placeholder="Notas livres...", height=96)
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
                mes_str   = f"{data_calc.month:02d} - {MESES_PT[data_calc.month]}"
                valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                linhas.append([data_calc.strftime("%d/%m/%Y"), data_calc.year, mes_str, tipo,
                               proj_sel, cat_sel, valor_fmt, desc, f"{i+1} de {qtd_parcelas}",
                               "Não", envolvidos, info_gerais])
            with st.spinner("Salvando lançamentos..."):
                if salvar_lancamentos(linhas):
                    st.toast(f"{qtd_parcelas} lançamento(s) salvos!", icon="✅")
                    st.balloons()


def tela_dados(df):
    st.markdown("<h1>Base de Dados</h1><p style='color:#8E8E93;margin-top:-8px;margin-bottom:20px;'>Visualize, filtre, exporte e gerencie todos os lançamentos</p>", unsafe_allow_html=True)
    if df.empty:
        st.info("A planilha está vazia.")
        return

    with st.form("form_filtros_dados"):
        render_section_title("Filtros de Pesquisa")
        c1, c2 = st.columns(2)
        anos_disp   = sorted(df['Ano'].unique(), reverse=True) if 'Ano' in df.columns else []
        ano_atual   = date.today().year
        default_ano = [ano_atual] if ano_atual in anos_disp else []
        filtro_ano  = c1.multiselect("📅 Ano (obrigatório)", anos_disp, default=default_ano)
        filtro_mes  = c2.multiselect("🗓️ Mês", sorted(df['Mês'].unique()) if 'Mês' in df.columns else [])
        c3, c4, c5  = st.columns(3)
        filtro_proj = c3.multiselect("🏢 Projeto",   sorted(df['Projeto'].unique())   if 'Projeto'   in df.columns else [])
        filtro_tipo = c4.multiselect("🏷️ Tipo",      sorted(df['Tipo'].unique())      if 'Tipo'      in df.columns else [])
        filtro_cat  = c5.multiselect("📂 Categoria", sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else [])
        st.form_submit_button("Aplicar Filtros", type="primary", use_container_width=True)

    if not filtro_ano:
        st.warning("Selecione pelo menos um **Ano** para visualizar os dados.")
        return

    df_view = df.copy()
    if filtro_ano: df_view = df_view[df_view['Ano'].isin(filtro_ano)]
    if filtro_mes: df_view = df_view[df_view['Mês'].isin(filtro_mes)]
    if filtro_proj: df_view = df_view[df_view['Projeto'].isin(filtro_proj)]
    if filtro_tipo: df_view = df_view[df_view['Tipo'].isin(filtro_tipo)]
    if filtro_cat:  df_view = df_view[df_view['Categoria'].isin(filtro_cat)]

    df_consumo = (df_view[df_view['Tipo'] == 'Realizado']
                  .groupby(['Ano', 'Mês', 'Projeto', 'Categoria'])['Valor'].sum()
                  .reset_index().rename(columns={'Valor': 'Valor_Consumido_Calc'}))
    df_final = pd.merge(df_view, df_consumo, on=['Ano', 'Mês', 'Projeto', 'Categoria'], how='left')
    df_final['Valor_Consumido_Calc'] = df_final['Valor_Consumido_Calc'].fillna(0)
    # [B2] FIX: reset_index() antes de paginar — garante alinhamento com _row_id
    df_final = df_final.reset_index(drop=True)

    cond_orc  = df_final['Tipo'] == 'Orçado'
    cond_real = df_final['Tipo'] == 'Realizado'
    df_final.loc[cond_orc,  'Valor Consumido'] = df_final.loc[cond_orc, 'Valor_Consumido_Calc']
    df_final.loc[cond_orc,  'Diferença']       = df_final.loc[cond_orc, 'Valor'] - df_final.loc[cond_orc, 'Valor Consumido']
    df_final.loc[cond_orc,  'Status']          = np.where(df_final.loc[cond_orc, 'Diferença'] < 0, "Estouro", "OK")
    df_final.loc[cond_real, 'Valor Consumido'] = None
    df_final.loc[cond_real, 'Diferença']       = None
    df_final.loc[cond_real, 'Status']          = None

    tot_orc  = df_final[df_final['Tipo'] == 'Orçado']['Valor'].sum()
    tot_real = df_final[df_final['Tipo'] == 'Realizado']['Valor'].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Registros",       len(df_final))
    m2.metric("💰 Total Orçado",    fmt_real(tot_orc))
    m3.metric("✅ Total Realizado", fmt_real(tot_real))
    m4.metric("📊 Saldo",           fmt_real(tot_orc - tot_real),
              delta_color="normal" if tot_orc >= tot_real else "inverse")

    # [N3] NOVO: Exportação CSV e Excel
    st.markdown("<hr>", unsafe_allow_html=True)
    render_section_title("Exportar Dados")
    exp_cols = ["Data", "Mês", "Ano", "Tipo", "Projeto", "Categoria", "Valor",
                "Descrição", "Parcela", "Envolvidos", "Info Gerais"]
    df_export = df_final[[c for c in exp_cols if c in df_final.columns]]
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        csv_bytes = df_export.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV", data=csv_bytes,
                           file_name=f"orcamento_{'_'.join(str(a) for a in filtro_ano)}.csv",
                           mime="text/csv", use_container_width=True)
    with col_xlsx:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name="Lançamentos")
        st.download_button("⬇️ Exportar Excel", data=buffer.getvalue(),
                           file_name=f"orcamento_{'_'.join(str(a) for a in filtro_ano)}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # Paginação
    tamanho_pagina = 50
    total_paginas  = max(1, math.ceil(len(df_final) / tamanho_pagina))
    if total_paginas > 1:
        col_p, col_info = st.columns([1, 3])
        pagina_atual = col_p.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
        col_info.markdown(f"<p style='color:#8E8E93;font-size:13px;margin-top:32px;'>Página {pagina_atual} de {total_paginas} · {len(df_final)} registros</p>", unsafe_allow_html=True)
    else:
        pagina_atual = 1

    inicio = (pagina_atual - 1) * tamanho_pagina
    fim    = inicio + tamanho_pagina
    df_paginado = df_final.iloc[inicio:fim].copy()
    df_paginado["Excluir"] = False

    colunas_show = ["Data", "Mês", "Tipo", "Projeto", "Categoria", "Valor",
                    "Valor Consumido", "Diferença", "Status",
                    "Descrição", "Envolvidos", "Info Gerais", "Parcela", "Excluir"]
    cols_show = [c for c in colunas_show if c in df_paginado.columns]

    # [B5] FIX: key inclui hash dos filtros para evitar estado fantasma
    filtro_hash = abs(hash(str(filtro_ano) + str(filtro_proj) + str(filtro_tipo) + str(filtro_cat)))
    df_edited = st.data_editor(
        df_paginado[cols_show],
        column_config={
            "Excluir":         st.column_config.CheckboxColumn("🗑️", width="small", default=False),
            "Valor":           st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "Valor Consumido": st.column_config.NumberColumn("Consumido",  format="R$ %.2f", disabled=True),
            "Diferença":       st.column_config.NumberColumn("Diferença",  format="R$ %.2f", disabled=True),
            "Status":          st.column_config.TextColumn("Status", disabled=True),
        },
        disabled=["Data", "Mês", "Tipo", "Projeto", "Categoria", "Valor",
                  "Descrição", "Parcela", "Envolvidos", "Info Gerais"],
        hide_index=True, use_container_width=True,
        key=f"editor_{pagina_atual}_{filtro_hash}"
    )

    linhas_excluir = df_edited[df_edited["Excluir"] == True]
    if not linhas_excluir.empty:
        st.error(f"⚠️ **{len(linhas_excluir)} registro(s)** marcado(s) para exclusão. Esta ação não pode ser desfeita.")
        if st.button("🗑️ Confirmar Exclusão", type="primary", use_container_width=True):
            if "_row_id" in df_paginado.columns:
                ids_reais = df_paginado.loc[linhas_excluir.index, "_row_id"].tolist()
                with st.spinner("Excluindo registros..."):
                    if excluir_linhas_google(ids_reais):
                        st.success("Registros excluídos com sucesso!")
                        st.rerun()


def tela_cadastros(df_cad, df_env):
    st.markdown("<h1>Cadastros</h1><p style='color:#8E8E93;margin-top:-8px;margin-bottom:20px;'>Gerencie projetos, categorias e equipes</p>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        render_section_title("🏢 Projetos")
        with st.form("form_proj", clear_on_submit=True):
            novo_proj = st.text_input("Nome do Projeto", placeholder="Ex: Reforma Sede 2025")
            if st.form_submit_button("Adicionar Projeto", type="primary", use_container_width=True):
                if novo_proj.strip():
                    with st.spinner("Salvando..."):
                        if salvar_cadastro_novo("Projeto", novo_proj.strip(), df_cad):
                            st.success(f"Projeto '{novo_proj}' adicionado!")
                            st.rerun()
                else:
                    st.warning("Digite um nome válido.")
        if not df_cad.empty:
            proj_lista = df_cad[df_cad['Tipo'] == 'Projeto'][['Nome']].reset_index(drop=True)
            if not proj_lista.empty:
                st.caption(f"{len(proj_lista)} projeto(s)")
                st.dataframe(proj_lista, use_container_width=True, hide_index=True)

    with c2:
        render_section_title("📂 Categorias")
        with st.form("form_cat", clear_on_submit=True):
            nova_cat = st.text_input("Nome da Categoria", placeholder="Ex: Marketing Digital")
            if st.form_submit_button("Adicionar Categoria", type="primary", use_container_width=True):
                if nova_cat.strip():
                    with st.spinner("Salvando..."):
                        if salvar_cadastro_novo("Categoria", nova_cat.strip(), df_cad):
                            st.success(f"Categoria '{nova_cat}' adicionada!")
                            st.rerun()
                else:
                    st.warning("Digite um nome válido.")
        if not df_cad.empty:
            cat_lista = df_cad[df_cad['Tipo'] == 'Categoria'][['Nome']].reset_index(drop=True)
            if not cat_lista.empty:
                st.caption(f"{len(cat_lista)} categoria(s)")
                st.dataframe(cat_lista, use_container_width=True, hide_index=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    render_section_title("👥 Envolvidos por Projeto / Mês")

    lista_proj    = sorted(df_cad[df_cad['Tipo'] == 'Projeto']['Nome'].unique().tolist()) if not df_cad.empty else []
    ano_atual     = date.today().year
    meses_opcoes  = [f"{m:02d} - {MESES_PT[m]}" for m in range(1, 13)]

    with st.form("form_envolvido", clear_on_submit=True):
        ce1, ce2, ce3 = st.columns(3)
        env_ano  = ce1.selectbox("📅 Ano",  [ano_atual - 1, ano_atual, ano_atual + 1], index=1)
        env_mes  = ce2.selectbox("🗓️ Mês",  meses_opcoes)
        env_proj = ce3.selectbox("🏢 Projeto", lista_proj, index=None, placeholder="Selecione...")
        ce4, ce5, ce6 = st.columns(3)
        env_nome  = ce4.text_input("👤 Nome",          placeholder="Ex: João Silva")
        env_cargo = ce5.text_input("💼 Cargo/Função",  placeholder="Ex: Analista de TI")
        env_cc    = ce6.text_input("🏦 Centro de Custo", placeholder="Ex: TI-001")
        ce7, ce8, ce9 = st.columns(3)
        env_horas      = ce7.number_input("⏰ Horas",       min_value=0.0, step=1.0,  format="%.1f")
        # [N4] NOVO: campo Valor/Hora
        env_valor_hora = ce8.number_input("💵 Valor/Hora (R$)", min_value=0.0, step=10.0, format="%.2f",
                                          help="Custo por hora do profissional")
        env_obs = ce9.text_input("📝 Observações", placeholder="Opcional")

        if st.form_submit_button("💾 Cadastrar Envolvido", type="primary", use_container_width=True):
            if not env_nome.strip():
                st.error("Informe o nome do envolvido.")
            elif env_proj is None:
                st.error("Selecione um projeto.")
            else:
                custo_total = env_horas * env_valor_hora
                linha = [str(env_ano), env_mes, env_proj, env_nome.strip(),
                         env_cargo.strip(), env_cc.strip(),
                         str(env_horas), str(env_valor_hora), env_obs.strip()]
                with st.spinner("Salvando..."):
                    if salvar_envolvido(linha):
                        msg = f"{env_nome} cadastrado em {env_proj} ({env_mes})"
                        if custo_total > 0:
                            msg += f" · Custo: {fmt_real(custo_total)}"
                        st.toast(msg, icon="✅")
                        st.balloons()

    if not df_env.empty:
        render_section_title("Envolvidos Cadastrados")
        fe1, fe2, fe3 = st.columns(3)
        filtro_env_ano  = fe1.selectbox("Filtrar Ano", sorted(df_env['Ano'].unique(), reverse=True), index=0, key="fea")
        df_env_f = df_env[df_env['Ano'] == str(filtro_env_ano)]
        filtro_env_mes  = fe2.multiselect("Filtrar Mês",     sorted(df_env_f['Mês'].unique())     if not df_env_f.empty else [], key="fem")
        if filtro_env_mes: df_env_f = df_env_f[df_env_f['Mês'].isin(filtro_env_mes)]
        filtro_env_proj = fe3.multiselect("Filtrar Projeto", sorted(df_env_f['Projeto'].unique()) if not df_env_f.empty else [], key="fep")
        if filtro_env_proj: df_env_f = df_env_f[df_env_f['Projeto'].isin(filtro_env_proj)]

        if not df_env_f.empty:
            df_env_f = df_env_f.copy()
            df_env_f['Horas_num'] = pd.to_numeric(df_env_f['Horas'],      errors='coerce').fillna(0)
            df_env_f['VH_num']    = pd.to_numeric(df_env_f['Valor/Hora'], errors='coerce').fillna(0)
            df_env_f['Custo Total'] = df_env_f['Horas_num'] * df_env_f['VH_num']
            st.caption(f"{len(df_env_f)} registro(s)")
            cols_show_env = ["Mês", "Projeto", "Nome", "Cargo/Função", "Centro de Custo",
                             "Horas", "Valor/Hora", "Custo Total", "Observações"]
            st.dataframe(df_env_f[[c for c in cols_show_env if c in df_env_f.columns]],
                         use_container_width=True, hide_index=True,
                         column_config={
                             "Horas":       st.column_config.NumberColumn(format="%.1f"),
                             "Valor/Hora":  st.column_config.NumberColumn("R$/Hora",    format="R$ %.2f"),
                             "Custo Total": st.column_config.NumberColumn("Custo Total", format="R$ %.2f"),
                         })
            # [N4] NOVO: Resumo por Centro de Custo
            resumo_cc = (df_env_f.groupby('Centro de Custo')
                         .agg(Total_Horas=('Horas_num', 'sum'), Custo_MO=('Custo Total', 'sum'))
                         .reset_index().rename(columns={'Total_Horas': 'Total Horas', 'Custo_MO': 'Custo M.O. (R$)'})
                         .sort_values('Custo M.O. (R$)', ascending=False))
            if not resumo_cc.empty:
                render_section_title("Resumo por Centro de Custo")
                st.dataframe(resumo_cc, use_container_width=True, hide_index=True,
                             column_config={
                                 "Total Horas":    st.column_config.NumberColumn(format="%.1f"),
                                 "Custo M.O. (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                             })
        else:
            st.info("Nenhum envolvido encontrado para os filtros selecionados.")
    else:
        st.info("Nenhum envolvido cadastrado ainda.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    if "pagina" not in st.session_state:
        st.session_state.pagina = "painel"

    with st.spinner("Carregando dados..."):
        df_lancamentos, df_cadastros, df_envolvidos = carregar_dados()

    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 24px 0;">
            <div style="font-size:22px; font-weight:700; color:#1C1C1E;">🎯 Controle Orçamentário</div>
            <div style="font-size:13px; color:#8E8E93; margin-top:2px;">Gestão Financeira · v5.1</div>
        </div>
        """, unsafe_allow_html=True)

        menu_items = [
            {"key": "painel",    "icon": "📊", "label": "Painel"},
            {"key": "novo",      "icon": "➕", "label": "Novo"},
            {"key": "dados",     "icon": "📂", "label": "Dados"},
            {"key": "cadastros", "icon": "⚙️", "label": "Cadastros"},
        ]
        st.markdown('<div style="font-size:11px;font-weight:600;color:#8E8E93;text-transform:uppercase;letter-spacing:1px;padding:0 0 8px 4px;">Navegação</div>', unsafe_allow_html=True)
        for item in menu_items:
            is_active = st.session_state.pagina == item["key"]
            if is_active:
                st.markdown(f'<div style="display:flex;align-items:center;gap:12px;padding:12px 16px;margin-bottom:4px;background:rgba(0,122,255,0.1);border-radius:12px;color:#007AFF;font-weight:600;font-size:15px;"><span style="font-size:18px;width:24px;text-align:center;">{item["icon"]}</span>{item["label"]}</div>', unsafe_allow_html=True)
            else:
                if st.button(f"{item['icon']} {item['label']}", key=f"nav_{item['key']}", use_container_width=True):
                    st.session_state.pagina = item["key"]
                    st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        if not df_lancamentos.empty:
            ano_atual = date.today().year
            df_ano    = df_lancamentos[df_lancamentos['Ano'] == ano_atual]
            tot_orc   = df_ano[df_ano['Tipo'] == 'Orçado']['Valor'].sum()
            tot_real  = df_ano[df_ano['Tipo'] == 'Realizado']['Valor'].sum()
            uso_pct   = pct(tot_real, tot_orc)
            cor_sb    = CORES['realizado'] if uso_pct <= 85 else (CORES['aviso'] if uso_pct <= 100 else CORES['alerta'])
            st.markdown(f"""
            <div style="background:#F5F5F5;border:1px solid #EBEBEB;border-radius:12px;padding:14px 16px;margin-bottom:16px;">
                <div style="font-size:11px;font-weight:600;color:#8E8E93;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">{ano_atual} · Resumo</div>
                <div style="font-size:15px;font-weight:700;color:#1C1C1E;">{fmt_real(tot_real)}</div>
                <div style="font-size:12px;color:#8E8E93;margin-top:2px;">de {fmt_real(tot_orc)} orçados</div>
                <div style="background:#E5E5E5;border-radius:4px;height:5px;margin-top:10px;overflow:hidden;">
                    <div style="background:{cor_sb};width:{min(uso_pct,100):.0f}%;height:5px;border-radius:4px;"></div>
                </div>
                <div style="font-size:11px;color:{cor_sb};font-weight:600;margin-top:4px;">{uso_pct:.0f}% consumido</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown('<div style="margin-top:32px;font-size:11px;color:#C7C7CC;text-align:center;">v5.1 · Responsivo</div>', unsafe_allow_html=True)

    if   st.session_state.pagina == "painel":    tela_resumo(df_lancamentos)
    elif st.session_state.pagina == "novo":      tela_novo(df_lancamentos, df_cadastros)
    elif st.session_state.pagina == "dados":     tela_dados(df_lancamentos)
    elif st.session_state.pagina == "cadastros": tela_cadastros(df_cadastros, df_envolvidos)


if __name__ == "__main__":
    main()
