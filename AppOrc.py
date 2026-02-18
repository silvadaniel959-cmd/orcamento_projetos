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

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(
    page_title="Orçamento",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. DESIGN SYSTEM: APPLE-LIKE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Reset & Base ── */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
                     "Helvetica Neue", Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }

    /* ── Background ── */
    .stApp {
        background-color: #F2F2F7;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0,0,0,0.08);
    }
    [data-testid="stSidebar"] .stRadio label {
        border-radius: 10px;
        padding: 10px 16px;
        cursor: pointer;
        transition: background 0.2s ease;
        display: block;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(0,122,255,0.08);
    }

    /* ── Metric Cards ── */
    div.stMetric {
        background: #FFFFFF;
        border: none;
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div.stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    }
    div.stMetric label {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #8E8E93 !important;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    div.stMetric [data-testid="metric-container"] > div:first-of-type {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #1C1C1E !important;
        letter-spacing: -0.5px;
    }
    [data-testid="metric-delta"] {
        font-size: 12px !important;
        font-weight: 500 !important;
    }

    /* ── Forms ── */
    [data-testid="stForm"] {
        background: #FFFFFF;
        border: none;
        border-radius: 16px;
        padding: 28px 32px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        border-radius: 10px !important;
        border: 1px solid #D1D1D6 !important;
        background: #F9F9FB !important;
        font-size: 15px !important;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #007AFF !important;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.15) !important;
        background: #FFFFFF !important;
    }

    /* ── Buttons ── */
    button[kind="primary"] {
        background: #007AFF !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        letter-spacing: -0.2px;
        box-shadow: 0 2px 8px rgba(0,122,255,0.35) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        background: #0071E3 !important;
        box-shadow: 0 4px 16px rgba(0,122,255,0.4) !important;
        transform: translateY(-1px);
    }
    button[kind="primary"]:active {
        transform: translateY(0px);
    }
    button[kind="secondary"] {
        border-radius: 12px !important;
        font-weight: 500 !important;
    }

    /* ── Data Editor / Tables ── */
    .stDataFrame, [data-testid="stDataEditor"] {
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid rgba(0,0,0,0.06) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    /* ── Headings ── */
    h1 { font-size: 28px !important; font-weight: 700 !important; color: #1C1C1E !important; letter-spacing: -0.5px; }
    h2 { font-size: 22px !important; font-weight: 600 !important; color: #1C1C1E !important; letter-spacing: -0.3px; }
    h3 { font-size: 17px !important; font-weight: 600 !important; color: #1C1C1E !important; }

    /* ── Section Label ── */
    .section-label {
        font-size: 11px;
        font-weight: 600;
        color: #8E8E93;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 12px;
    }

    /* ── Apple-style Card ── */
    .apple-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }

    /* ── Status Badges ── */
    .badge-ok {
        display: inline-flex; align-items: center; gap: 4px;
        background: rgba(52,199,89,0.12); color: #1A7F3C;
        border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 600;
    }
    .badge-estouro {
        display: inline-flex; align-items: center; gap: 4px;
        background: rgba(255,59,48,0.12); color: #C0392B;
        border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 600;
    }

    /* ── Divider ── */
    hr {
        border: none;
        border-top: 1px solid #E5E5EA;
        margin: 1.75rem 0;
    }

    /* ── Multiselect Tags ── */
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(0,122,255,0.1) !important;
        border-radius: 6px !important;
        color: #007AFF !important;
    }

    /* ── Sidebar Title ── */
    .sidebar-title {
        font-size: 20px;
        font-weight: 700;
        color: #1C1C1E;
        letter-spacing: -0.3px;
        margin-bottom: 4px;
    }
    .sidebar-subtitle {
        font-size: 13px;
        color: #8E8E93;
        margin-bottom: 24px;
    }

    /* ── Toast notifications ── */
    [data-testid="stToast"] {
        border-radius: 14px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15) !important;
    }

    /* ── Warning / Info / Error ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        border: none !important;
    }

    /* ── Progress bar ── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #007AFF, #34C759) !important;
        border-radius: 4px !important;
    }

    /* ── KPI Strip ── */
    .kpi-strip {
        display: flex;
        gap: 8px;
        background: rgba(0,122,255,0.06);
        border-radius: 12px;
        padding: 12px 20px;
        margin-bottom: 20px;
        align-items: center;
    }
    .kpi-item { flex: 1; text-align: center; }
    .kpi-value { font-size: 20px; font-weight: 700; color: #1C1C1E; }
    .kpi-key { font-size: 11px; color: #8E8E93; font-weight: 500; }

    /* ── Chart wrapper ── */
    .chart-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06), 0 0 0 1px rgba(0,0,0,0.04);
    }
</style>
""", unsafe_allow_html=True)


# --- 3. CONSTANTES & DESIGN TOKENS ---
CORES = {
    "primaria":   "#007AFF",
    "orcado":     "#C7C7CC",
    "realizado":  "#34C759",
    "alerta":     "#FF3B30",
    "aviso":      "#FF9500",
    "roxo":       "#AF52DE",
    "fundo":      "#F2F2F7",
    "superficie": "#FFFFFF",
    "texto":      "#1C1C1E",
    "texto2":     "#3A3A3C",
    "texto3":     "#8E8E93",
    "separador":  "#E5E5EA",
}

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
    5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
    9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

PLOTLY_LAYOUT_BASE = dict(
    font_family="-apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif",
    font_color=CORES["texto2"],
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=24, b=40),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.22,
        xanchor="center", x=0.5,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color=CORES["texto3"])
    ),
    xaxis=dict(showgrid=False, showline=False, tickfont=dict(size=11, color=CORES["texto3"])),
    yaxis=dict(showgrid=True, gridcolor="#F2F2F7", showline=False, tickfont=dict(size=11, color=CORES["texto3"])),
    hoverlabel=dict(
        bgcolor="white", bordercolor=CORES["separador"],
        font_size=13, font_family="-apple-system, BlinkMacSystemFont",
        font_color=CORES["texto"]
    ),
)


# --- 4. CONEXÃO GOOGLE SHEETS ---
def conectar_google():
    try:
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_json = os.path.join(diretorio_atual, 'credentials.json')

        if os.path.exists(caminho_json):
            return gspread.service_account(filename=caminho_json)
        elif "google_credentials" in st.secrets:
            creds_data = st.secrets["google_credentials"]["content"]
            if isinstance(creds_data, str):
                creds_dict = json.loads(creds_data)
            else:
                creds_dict = dict(creds_data)
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return gspread.service_account_from_dict(creds_dict)
        else:
            st.error("❌ Credenciais não encontradas.")
            return None
    except Exception as e:
        st.error(f"❌ Erro de conexão: {e}")
        return None


def get_worksheet_case_insensitive(sh, nome_procurado):
    for ws in sh.worksheets():
        if ws.title.lower() == nome_procurado.lower():
            return ws
    return None


# --- 5. CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=120)  # ⚡ Aumentado para 2 min: reduz chamadas desnecessárias
def carregar_dados():
    client = conectar_google()
    if not client:
        return pd.DataFrame(), pd.DataFrame()

    try:
        sh = client.open("dados_app_orcamento")

        # Lançamentos
        ws_lanc = get_worksheet_case_insensitive(sh, "lançamentos")
        if not ws_lanc:
            return pd.DataFrame(), pd.DataFrame()

        # ⚡ PERFORMANCE: batch_get retorna múltiplas ranges em UMA chamada
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

        def converter_br(v):
            try:
                if not v: return 0.0
                limpo = str(v).replace("R$", "").replace(" ", "")
                if "," in limpo and "." in limpo:
                    limpo = limpo.replace(".", "").replace(",", ".")
                elif "," in limpo:
                    limpo = limpo.replace(",", ".")
                elif "." in limpo and limpo.count(".") == 1 and len(limpo.split(".")[1]) == 3:
                    limpo = limpo.replace(".", "")
                return float(limpo)
            except:
                return 0.0

        if not df_lanc.empty:
            df_lanc['Valor'] = df_lanc['Valor'].apply(converter_br)
            df_lanc['Ano'] = pd.to_numeric(df_lanc['Ano'], errors='coerce').fillna(date.today().year).astype(int)
            # ⚡ Converter Data uma vez aqui
            df_lanc['Data_dt'] = pd.to_datetime(df_lanc['Data'], format="%d/%m/%Y", errors='coerce')

        # Cadastros
        ws_cad = get_worksheet_case_insensitive(sh, "cadastros")
        if ws_cad:
            dados_cad = ws_cad.get_all_values()
            if len(dados_cad) <= 1:
                df_cad = pd.DataFrame(columns=["Tipo", "Nome"])
            else:
                df_cad = pd.DataFrame(dados_cad[1:], columns=["Tipo", "Nome"])
        else:
            df_cad = pd.DataFrame(columns=["Tipo", "Nome"])

        return df_lanc, df_cad

    except Exception as e:
        st.error(f"⚠️ Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame()


# --- FUNÇÕES DE ESCRITA ---
def salvar_lancamentos(lista_linhas):
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet_case_insensitive(sh, "lançamentos")
            if ws:
                ws.append_rows(lista_linhas, value_input_option='USER_ENTERED')
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
    return False


def excluir_linhas_google(lista_ids):
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet_case_insensitive(sh, "lançamentos")
            if ws:
                for row_id in sorted(lista_ids, reverse=True):
                    ws.delete_rows(row_id)
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")
    return False


def salvar_cadastro_novo(tipo, nome):
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet_case_insensitive(sh, "cadastros")
            if not ws:
                ws = sh.add_worksheet(title="cadastros", rows=100, cols=2)
                ws.append_row(["Tipo", "Nome"])
            ws.append_row([tipo, nome])
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar cadastro: {e}")
    return False


# --- HELPERS ---
def fmt_real(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(realizado, orcado):
    return (realizado / orcado * 100) if orcado else 0


# ── COMPONENTE: Barra de progresso de consumo ──
def render_progress_bar(consumido, orcado):
    p = min(pct(consumido, orcado), 120)
    cor = CORES["realizado"] if p <= 80 else (CORES["aviso"] if p <= 100 else CORES["alerta"])
    st.markdown(f"""
    <div style="background:#F2F2F7; border-radius:4px; height:6px; width:100%; margin-top:6px;">
      <div style="background:{cor}; width:{min(p,100):.0f}%; height:6px; border-radius:4px; transition:width 0.6s ease;"></div>
    </div>
    <div style="display:flex; justify-content:space-between; margin-top:4px;">
      <span style="font-size:11px; color:{CORES['texto3']};">Consumido: {fmt_real(consumido)}</span>
      <span style="font-size:11px; color:{'#C0392B' if p>100 else CORES['texto3']}; font-weight:600;">{p:.0f}%</span>
    </div>
    """, unsafe_allow_html=True)


# --- 6. TELAS ---

def tela_resumo(df):
    # ── Header ──
    st.markdown("""
    <div style="margin-bottom:24px;">
        <h1 style="margin:0; font-size:30px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            Painel Financeiro
        </h1>
        <p style="color:#8E8E93; margin:4px 0 0; font-size:15px;">Visão consolidada do seu orçamento</p>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("📭 Sem dados. Acesse **Novo** para criar o primeiro lançamento.")
        return

    ano_atual = date.today().year
    anos_disponiveis = sorted(df['Ano'].unique(), reverse=True)
    default_ano = ano_atual if ano_atual in anos_disponiveis else (anos_disponiveis[0] if anos_disponiveis else None)

    # ── Filtros ──
    with st.expander("🔍 Filtros", expanded=False):
        with st.form("form_filtros_painel"):
            c1, c2, c3, c4 = st.columns(4)
            ano_sel = c1.selectbox("Ano", anos_disponiveis,
                                   index=anos_disponiveis.index(default_ano) if default_ano else 0)
            meses_disp = sorted(df['Mês'].unique())
            meses_sel = c2.multiselect("Meses", meses_disp)
            proj_sel = c3.multiselect("Projetos", df['Projeto'].unique())
            cat_disp = sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else []
            cat_sel = c4.multiselect("Categorias", cat_disp)
            st.form_submit_button("Aplicar", type="primary")

    df_f = df[df['Ano'] == ano_sel]
    if meses_sel: df_f = df_f[df_f['Mês'].isin(meses_sel)]
    if proj_sel:  df_f = df_f[df_f['Projeto'].isin(proj_sel)]
    if cat_sel:   df_f = df_f[df_f['Categoria'].isin(cat_sel)]

    orcado    = df_f[df_f['Tipo'] == "Orçado"]['Valor'].sum()
    realizado = df_f[df_f['Tipo'] == "Realizado"]['Valor'].sum()
    saldo     = orcado - realizado
    pct_uso   = pct(realizado, orcado)

    # ── KPIs ──
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Orçado",    fmt_real(orcado))
    k2.metric("✅ Realizado",  fmt_real(realizado),
              delta=f"{pct_uso:.1f}% do orçado",
              delta_color="inverse")
    k3.metric("📊 Saldo Livre", fmt_real(saldo),
              delta="✔ No limite" if saldo >= 0 else "⚠ Estouro",
              delta_color="normal" if saldo >= 0 else "inverse")
    
    # ⭐ NOVO KPI: Taxa de comprometimento
    n_proj = df_f['Projeto'].nunique()
    k4.metric("🏢 Projetos Ativos", str(n_proj))

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Barra de consumo global ──
    st.markdown('<p class="section-label">Consumo do Orçamento</p>', unsafe_allow_html=True)
    render_progress_bar(realizado, orcado)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Gráfico 1: Evolução Mensal ──
    st.markdown('<p class="section-label">Evolução Mensal</p>', unsafe_allow_html=True)
    df_mes = df_f.groupby(['Mês', 'Tipo'])['Valor'].sum().reset_index()
    if not df_mes.empty:
        df_mes['Mes_Num'] = df_mes['Mês'].apply(lambda x: int(x.split(' - ')[0]) if ' - ' in x else 0)
        df_mes = df_mes.sort_values('Mes_Num')
        fig_mes = px.bar(
            df_mes, x="Mês", y="Valor", color="Tipo", barmode='group',
            color_discrete_map={"Orçado": CORES['orcado'], "Realizado": CORES['realizado']},
        )
        fig_mes.update_traces(
            texttemplate='%{y:.2s}', textposition='outside',
            marker_line_width=0, selector=dict(type='bar')
        )
        fig_mes.update_layout(height=360, bargap=0.3, bargroupgap=0.08, **PLOTLY_LAYOUT_BASE)
        st.plotly_chart(fig_mes, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Sem dados mensais para exibir.")

    # ── Gráficos 2 + 3 ──
    col_g1, col_g2 = st.columns([1, 1], gap="large")

    with col_g1:
        st.markdown('<p class="section-label">Projetos · Orçado vs Realizado</p>', unsafe_allow_html=True)
        df_proj = (df_f.groupby(['Projeto', 'Tipo'])['Valor'].sum()
                   .unstack(fill_value=0).reset_index())
        if not df_proj.empty:
            if 'Orçado' not in df_proj.columns:    df_proj['Orçado']    = 0.0
            if 'Realizado' not in df_proj.columns: df_proj['Realizado'] = 0.0

            fig_proj = go.Figure()
            fig_proj.add_trace(go.Bar(
                x=df_proj['Projeto'], y=df_proj['Orçado'],
                name='Orçado', marker_color=CORES['orcado'],
                opacity=0.55, width=0.55
            ))
            fig_proj.add_trace(go.Bar(
                x=df_proj['Projeto'], y=df_proj['Realizado'],
                name='Realizado', marker_color=CORES['primaria'],
                width=0.28
            ))
            fig_proj.update_layout(barmode='overlay', height=340, **PLOTLY_LAYOUT_BASE)
            st.plotly_chart(fig_proj, use_container_width=True, config={"displayModeBar": False})

    with col_g2:
        st.markdown('<p class="section-label">Categorias · Top 8 (Bullet)</p>', unsafe_allow_html=True)
        df_cat = (df_f.groupby(['Categoria', 'Tipo'])['Valor'].sum()
                  .unstack(fill_value=0).reset_index())
        if not df_cat.empty:
            if 'Orçado' not in df_cat.columns:    df_cat['Orçado']    = 0.0
            if 'Realizado' not in df_cat.columns: df_cat['Realizado'] = 0.0

            df_cat = df_cat.sort_values('Orçado', ascending=True).tail(8)

            fig_bullet = go.Figure()
            fig_bullet.add_trace(go.Bar(
                y=df_cat['Categoria'], x=df_cat['Orçado'],
                name='Meta', orientation='h',
                marker_color='#E5E7EB', width=0.65
            ))
            fig_bullet.add_trace(go.Bar(
                y=df_cat['Categoria'], x=df_cat['Realizado'],
                name='Realizado', orientation='h',
                marker_color=CORES['realizado'], width=0.3
            ))
            fig_bullet.add_trace(go.Scatter(
                y=df_cat['Categoria'], x=df_cat['Orçado'],
                mode='markers', name='Limite',
                marker=dict(symbol='line-ns-open', size=22, color=CORES['texto'],
                            line=dict(width=2.5))
            ))
            fig_bullet.update_layout(barmode='overlay', height=340, **PLOTLY_LAYOUT_BASE)
            st.plotly_chart(fig_bullet, use_container_width=True, config={"displayModeBar": False})

    # ── Waterfall ──
    st.markdown('<p class="section-label">Fluxo de Caixa · Waterfall</p>', unsafe_allow_html=True)
    total_orcado = df_f[df_f['Tipo'] == 'Orçado']['Valor'].sum()
    df_gastos    = (df_f[df_f['Tipo'] == 'Realizado']
                    .groupby('Categoria')['Valor'].sum()
                    .reset_index().sort_values('Valor', ascending=False))

    if total_orcado > 0 or not df_gastos.empty:
        top_n = 7
        measures  = ["absolute"]; x_data = ["Orçamento"]
        y_data    = [total_orcado]; text_data = [fmt_real(total_orcado)]
        saldo_wf  = total_orcado

        df_top = df_gastos.head(top_n)
        outros_val = df_gastos.iloc[top_n:]['Valor'].sum() if len(df_gastos) > top_n else 0

        for _, row in df_top.iterrows():
            measures.append("relative"); x_data.append(row['Categoria'])
            y_data.append(-row['Valor']); text_data.append(f"−{fmt_real(row['Valor'])}")
            saldo_wf -= row['Valor']

        if outros_val > 0:
            measures.append("relative"); x_data.append("Outros")
            y_data.append(-outros_val); text_data.append(f"−{fmt_real(outros_val)}")
            saldo_wf -= outros_val

        measures.append("total"); x_data.append("Saldo")
        y_data.append(0); text_data.append(fmt_real(saldo_wf))

        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=measures, x=x_data,
            textposition="outside", text=text_data, y=y_data,
            connector={"line": {"color": CORES["separador"], "width": 1, "dash": "dot"}},
            decreasing={"marker": {"color": CORES['alerta'], "line": {"width": 0}}},
            increasing={"marker": {"color": CORES['realizado'], "line": {"width": 0}}},
            totals={"marker": {"color": CORES['primaria'], "line": {"width": 0}}},
        ))
        fig_wf.update_layout(height=420, waterfallgap=0.35, **PLOTLY_LAYOUT_BASE)
        st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": False})


def tela_novo(df_lanc, df_cad):
    st.markdown("""
    <div style="margin-bottom:24px;">
        <h1 style="margin:0; font-size:30px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            Novo Lançamento
        </h1>
        <p style="color:#8E8E93; margin:4px 0 0; font-size:15px;">Registre orçamentos e despesas realizadas</p>
    </div>
    """, unsafe_allow_html=True)

    if not df_cad.empty:
        lista_proj = sorted(df_cad[df_cad['Tipo'] == 'Projeto']['Nome'].unique().tolist())
        lista_cat  = sorted(df_cad[df_cad['Tipo'] == 'Categoria']['Nome'].unique().tolist())
    else:
        st.warning("⚠️ Nenhum Projeto ou Categoria cadastrado. Acesse **Cadastros** primeiro.")
        lista_proj, lista_cat = [], []

    with st.form("form_novo", clear_on_submit=True):
        st.markdown('<p class="section-label">Dados Principais</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        data_inicial   = c1.date_input("📅 Data Inicial", date.today())
        tipo           = c2.selectbox("🏷️ Tipo", ["Orçado", "Realizado"],
                                      help="Orçado = planejado | Realizado = efetivado")

        c3, c4 = st.columns(2)
        proj_sel = c3.selectbox("🏢 Projeto", lista_proj, index=None, placeholder="Selecione...")
        cat_sel  = c4.selectbox("📂 Categoria", lista_cat, index=None, placeholder="Selecione...")

        st.markdown('<p class="section-label" style="margin-top:12px;">Valores</p>',
                    unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        valor         = c5.number_input("💵 Valor da Parcela (R$)", min_value=0.0, step=100.0,
                                         format="%.2f")
        qtd_parcelas  = c6.number_input("🔁 Número de Parcelas", min_value=1, value=1, step=1,
                                         help="Lançamentos mensais consecutivos")

        # ⭐ Preview do total
        if valor > 0 and qtd_parcelas > 1:
            st.markdown(f"""
            <div style="background:rgba(0,122,255,0.06); border-radius:10px; padding:10px 16px; margin:8px 0;">
              <span style="font-size:13px; color:#8E8E93;">Total comprometido: </span>
              <span style="font-size:16px; font-weight:700; color:#007AFF;">{fmt_real(valor * qtd_parcelas)}</span>
              <span style="font-size:13px; color:#8E8E93;"> em {qtd_parcelas} meses</span>
            </div>
            """, unsafe_allow_html=True)

        desc = st.text_input("📝 Descrição", placeholder="Opcional — descreva a natureza do lançamento")

        st.markdown('<p class="section-label" style="margin-top:12px;">Informações Complementares</p>',
                    unsafe_allow_html=True)
        c7, c8 = st.columns(2)
        envolvidos  = c7.text_input("👥 Envolvidos", placeholder="Ex: João, Fornecedor X")
        info_gerais = c8.text_area("📋 Observações", placeholder="Notas livres...", height=96)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Salvar Lançamento", type="primary",
                                          use_container_width=True)

        if submitted:
            if proj_sel is None or cat_sel is None:
                st.error("⚠️ Projeto e Categoria são obrigatórios.")
            elif valor == 0:
                st.error("⚠️ Informe um valor maior que zero.")
            else:
                linhas = []
                for i in range(qtd_parcelas):
                    data_calc = data_inicial + relativedelta(months=i)
                    mes_str   = f"{data_calc.month:02d} - {MESES_PT[data_calc.month]}"
                    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    linhas.append([
                        data_calc.strftime("%d/%m/%Y"), data_calc.year, mes_str,
                        tipo, proj_sel, cat_sel, valor_fmt, desc,
                        f"{i+1} de {qtd_parcelas}", "Não",
                        envolvidos, info_gerais
                    ])

                if salvar_lancamentos(linhas):
                    st.toast(f"✅ {qtd_parcelas} lançamento(s) salvos com sucesso!", icon="✅")


def tela_dados(df):
    st.markdown("""
    <div style="margin-bottom:24px;">
        <h1 style="margin:0; font-size:30px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            Base de Dados
        </h1>
        <p style="color:#8E8E93; margin:4px 0 0; font-size:15px;">Visualize, filtre e gerencie todos os lançamentos</p>
    </div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("📭 A planilha está vazia.")
        return

    with st.form("form_filtros_dados"):
        st.markdown('<p class="section-label">Filtros de Pesquisa</p>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)

        anos_disp  = sorted(df['Ano'].unique(), reverse=True) if 'Ano' in df.columns else []
        ano_atual  = date.today().year
        default_ano = [ano_atual] if ano_atual in anos_disp else []

        filtro_ano  = c1.multiselect("📅 Ano",       anos_disp, default=default_ano)
        meses_disp  = sorted(df['Mês'].unique()) if 'Mês' in df.columns else []
        filtro_mes  = c2.multiselect("🗓️ Mês",       meses_disp)
        proj_disp   = sorted(df['Projeto'].unique()) if 'Projeto' in df.columns else []
        filtro_proj = c3.multiselect("🏢 Projeto",   proj_disp)
        tipo_disp   = sorted(df['Tipo'].unique()) if 'Tipo' in df.columns else []
        filtro_tipo = c4.multiselect("🏷️ Tipo",      tipo_disp)
        cat_disp    = sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else []
        filtro_cat  = c5.multiselect("📂 Categoria", cat_disp)

        st.form_submit_button("Aplicar Filtros", type="primary")

    if not filtro_ano:
        st.warning("⚠️ Selecione pelo menos um **Ano** para exibir os dados.")
        return

    df_view = df.copy()
    if filtro_ano:  df_view = df_view[df_view['Ano'].isin(filtro_ano)]
    if filtro_mes:  df_view = df_view[df_view['Mês'].isin(filtro_mes)]
    if filtro_proj: df_view = df_view[df_view['Projeto'].isin(filtro_proj)]
    if filtro_tipo: df_view = df_view[df_view['Tipo'].isin(filtro_tipo)]
    if filtro_cat:  df_view = df_view[df_view['Categoria'].isin(filtro_cat)]

    # ── Cálculo de consumo ──
    df_consumo = (df_view[df_view['Tipo'] == 'Realizado']
                  .groupby(['Ano', 'Mês', 'Projeto', 'Categoria'])['Valor'].sum()
                  .reset_index().rename(columns={'Valor': 'Valor_Consumido_Calc'}))

    df_final = pd.merge(df_view, df_consumo, on=['Ano', 'Mês', 'Projeto', 'Categoria'], how='left')
    df_final['Valor_Consumido_Calc'] = df_final['Valor_Consumido_Calc'].fillna(0)

    cond_orc  = df_final['Tipo'] == 'Orçado'
    cond_real = df_final['Tipo'] == 'Realizado'

    df_final.loc[cond_orc, 'Valor Consumido'] = df_final.loc[cond_orc, 'Valor_Consumido_Calc']
    df_final.loc[cond_orc, 'Diferença']       = df_final.loc[cond_orc, 'Valor'] - df_final.loc[cond_orc, 'Valor Consumido']
    df_final.loc[cond_orc, 'Status']          = np.where(df_final.loc[cond_orc, 'Diferença'] < 0, "⚠️ Estouro", "✅ OK")
    df_final.loc[cond_real, 'Status']         = "💸 Realizado"

    # ── Resumo rápido acima da tabela ──
    tot_orc  = df_final[df_final['Tipo'] == 'Orçado']['Valor'].sum()
    tot_real = df_final[df_final['Tipo'] == 'Realizado']['Valor'].sum()
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Registros",     str(len(df_final)))
    r2.metric("Total Orçado",  fmt_real(tot_orc))
    r3.metric("Total Realizado", fmt_real(tot_real))
    r4.metric("Saldo",         fmt_real(tot_orc - tot_real),
              delta_color="normal" if tot_orc >= tot_real else "inverse")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Paginação ──
    tamanho_pagina = 50
    total_paginas  = max(1, math.ceil(len(df_final) / tamanho_pagina))

    if total_paginas > 1:
        col_p, col_info, _ = st.columns([1, 2, 4])
        pagina_atual = col_p.number_input("Página", min_value=1, max_value=total_paginas,
                                           value=1, step=1)
        col_info.markdown(
            f"<p style='color:#8E8E93; font-size:13px; margin-top:32px;'>"
            f"Página {pagina_atual} de {total_paginas} · {len(df_final)} registros</p>",
            unsafe_allow_html=True
        )
    else:
        pagina_atual = 1

    inicio     = (pagina_atual - 1) * tamanho_pagina
    fim        = inicio + tamanho_pagina
    df_paginado = df_final.iloc[inicio:fim].copy()
    df_paginado["Excluir"] = False

    colunas_show = ["Data", "Mês", "Tipo", "Projeto", "Categoria",
                    "Valor", "Valor Consumido", "Diferença", "Status",
                    "Descrição", "Envolvidos", "Info Gerais", "Parcela", "Excluir"]
    cols_show = [c for c in colunas_show if c in df_paginado.columns]

    df_edited = st.data_editor(
        df_paginado[cols_show],
        column_config={
            "Excluir":          st.column_config.CheckboxColumn("🗑️", width="small", default=False),
            "Valor":            st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "Valor Consumido":  st.column_config.NumberColumn("Consumido",  format="R$ %.2f", disabled=True),
            "Diferença":        st.column_config.NumberColumn("Diferença",  format="R$ %.2f", disabled=True),
            "Status":           st.column_config.TextColumn("Status", disabled=True),
        },
        disabled=["Data", "Mês", "Tipo", "Projeto", "Categoria",
                  "Valor", "Descrição", "Parcela", "Envolvidos", "Info Gerais"],
        hide_index=True,
        use_container_width=True,
        key=f"editor_{pagina_atual}"
    )

    linhas_excluir = df_edited[df_edited["Excluir"] == True]
    if not linhas_excluir.empty:
        st.error(f"⚠️ {len(linhas_excluir)} registro(s) marcado(s) para exclusão.")
        col_btn, _ = st.columns([1, 3])
        if col_btn.button("🗑️ Confirmar Exclusão", type="primary"):
            if "_row_id" in df_view.columns:
                ids_reais = df_paginado.loc[linhas_excluir.index, "_row_id"].tolist()
                if excluir_linhas_google(ids_reais):
                    st.success("Registros excluídos com sucesso!")
                    st.rerun()


def tela_cadastros(df_cad):
    st.markdown("""
    <div style="margin-bottom:24px;">
        <h1 style="margin:0; font-size:30px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            Cadastros
        </h1>
        <p style="color:#8E8E93; margin:4px 0 0; font-size:15px;">Gerencie projetos e categorias do sistema</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<p class="section-label">🏢 Projetos</p>', unsafe_allow_html=True)
        with st.form("form_proj", clear_on_submit=True):
            novo_proj = st.text_input("Nome do Projeto", placeholder="Ex: Reforma Sede 2025")
            if st.form_submit_button("Adicionar Projeto", type="primary", use_container_width=True):
                if novo_proj.strip():
                    if salvar_cadastro_novo("Projeto", novo_proj.strip()):
                        st.success(f"✅ Projeto '{novo_proj}' adicionado!"); st.rerun()
                else:
                    st.warning("Digite um nome válido.")

        if not df_cad.empty:
            proj_lista = df_cad[df_cad['Tipo'] == 'Projeto'][['Nome']].reset_index(drop=True)
            if not proj_lista.empty:
                st.markdown(f"<p style='color:#8E8E93; font-size:13px;'>{len(proj_lista)} projeto(s) cadastrado(s)</p>",
                            unsafe_allow_html=True)
                st.dataframe(proj_lista, use_container_width=True, hide_index=True)

    with c2:
        st.markdown('<p class="section-label">📂 Categorias</p>', unsafe_allow_html=True)
        with st.form("form_cat", clear_on_submit=True):
            nova_cat = st.text_input("Nome da Categoria", placeholder="Ex: Marketing Digital")
            if st.form_submit_button("Adicionar Categoria", type="primary", use_container_width=True):
                if nova_cat.strip():
                    if salvar_cadastro_novo("Categoria", nova_cat.strip()):
                        st.success(f"✅ Categoria '{nova_cat}' adicionada!"); st.rerun()
                else:
                    st.warning("Digite um nome válido.")

        if not df_cad.empty:
            cat_lista = df_cad[df_cad['Tipo'] == 'Categoria'][['Nome']].reset_index(drop=True)
            if not cat_lista.empty:
                st.markdown(f"<p style='color:#8E8E93; font-size:13px;'>{len(cat_lista)} categoria(s) cadastrada(s)</p>",
                            unsafe_allow_html=True)
                st.dataframe(cat_lista, use_container_width=True, hide_index=True)


# --- 7. MENU PRINCIPAL ---
def main():
    df_lancamentos, df_cadastros = carregar_dados()

    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 20px 0;">
          <div style="font-size:22px; font-weight:700; color:#1C1C1E; letter-spacing:-0.5px;">
            💎 Orçamento
          </div>
          <div style="font-size:13px; color:#8E8E93; margin-top:2px;">
            Controle Financeiro
          </div>
        </div>
        """, unsafe_allow_html=True)

        menu    = ["📊 Painel", "➕ Novo", "📂 Dados", "⚙️ Cadastros"]
        escolha = st.radio("Navegação", menu, label_visibility="collapsed")

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Mini resumo na sidebar ──
        if not df_lancamentos.empty:
            ano_atual  = date.today().year
            df_ano     = df_lancamentos[df_lancamentos['Ano'] == ano_atual]
            tot_orc    = df_ano[df_ano['Tipo'] == 'Orçado']['Valor'].sum()
            tot_real   = df_ano[df_ano['Tipo'] == 'Realizado']['Valor'].sum()
            uso_pct    = pct(tot_real, tot_orc)
            cor_sb     = CORES['realizado'] if uso_pct <= 85 else (CORES['aviso'] if uso_pct <= 100 else CORES['alerta'])

            st.markdown(f"""
            <div style="background:#F2F2F7; border-radius:12px; padding:14px 16px; margin-bottom:16px;">
              <div style="font-size:11px; font-weight:600; color:#8E8E93; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;">
                {ano_atual} · Resumo
              </div>
              <div style="font-size:15px; font-weight:700; color:#1C1C1E;">{fmt_real(tot_real)}</div>
              <div style="font-size:12px; color:#8E8E93; margin-top:2px;">de {fmt_real(tot_orc)} orçados</div>
              <div style="background:#E5E5EA; border-radius:3px; height:4px; margin-top:10px;">
                <div style="background:{cor_sb}; width:{min(uso_pct,100):.0f}%; height:4px; border-radius:3px;"></div>
              </div>
              <div style="font-size:11px; color:{cor_sb}; font-weight:600; margin-top:4px;">{uso_pct:.0f}% consumido</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear(); st.rerun()

        st.markdown("""
        <div style="position:absolute; bottom:24px; left:16px; right:16px;
                    font-size:11px; color:#C7C7CC; text-align:center;">
            v2.0 · Design System Apple
        </div>
        """, unsafe_allow_html=True)

    if escolha == "📊 Painel":     tela_resumo(df_lancamentos)
    elif escolha == "➕ Novo":      tela_novo(df_lancamentos, df_cadastros)
    elif escolha == "📂 Dados":     tela_dados(df_lancamentos)
    elif escolha == "⚙️ Cadastros": tela_cadastros(df_cadastros)


if __name__ == "__main__":
    main()
