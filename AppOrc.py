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

# =========================
# 1) CONFIG GERAL
# =========================
APP_TITLE = "Controle Orçamentário"
SHEET_NAME = "dados_app_orcamento"
WS_LANC = "lançamentos"
WS_CAD = "cadastros"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# 2) DESIGN (APP-LIKE CSS)
# =========================
st.markdown(
    """
<style>
html, body, [class*="css"]  { font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial; }
.stApp { background: radial-gradient(1200px 600px at 20% 0%, #eef6ff 0%, #f7f8fc 45%, #f6f7fb 100%); }

.block-container { padding-top: 1.25rem; padding-bottom: 4rem; max-width: 1400px; }

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.card {
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(229,231,235,.9);
  border-radius: 18px;
  padding: 18px 18px 12px 18px;
  box-shadow: 0 10px 30px rgba(17, 24, 39, .06);
  backdrop-filter: blur(8px);
}
.card:hover { border-color: rgba(59,130,246,.25); }

div.stMetric {
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(229,231,235,.9);
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 10px 30px rgba(17, 24, 39, .06);
  backdrop-filter: blur(8px);
}

[data-testid="stForm"] {
  border: 1px solid rgba(229,231,235,.9);
  padding: 18px;
  border-radius: 18px;
  background: rgba(255,255,255,.72);
  box-shadow: 0 10px 30px rgba(17, 24, 39, .05);
  backdrop-filter: blur(8px);
}

button[kind="primary"] {
  border-radius: 14px !important;
  font-weight: 700 !important;
}
button { border-radius: 14px !important; }

hr { margin: 1.25rem 0; border-color: rgba(229,231,235,.9); }

[data-testid="stSegmentedControl"] {
  background: rgba(255,255,255,.75);
  border: 1px solid rgba(229,231,235,.9);
  border-radius: 16px;
  padding: 6px 8px;
  box-shadow: 0 10px 30px rgba(17, 24, 39, .05);
  backdrop-filter: blur(8px);
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# 3) CONSTANTES
# =========================
CORES = {
    "primaria": "#007AFF",
    "orcado": "#9CA3AF",
    "realizado": "#10B981",
    "alerta": "#EF4444",
}

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

COLUNAS_LANC = [
    "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria",
    "Valor", "Descrição", "Parcela", "Abatido",
    "Envolvidos", "Info Gerais"
]

# =========================
# 4) HELPERS
# =========================
def fmt_real(v: float) -> str:
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def parse_real_br(v) -> float:
    try:
        if v is None or v == "":
            return 0.0
        limpo = str(v).replace("R$", "").replace(" ", "")
        if "," in limpo and "." in limpo:
            limpo = limpo.replace(".", "").replace(",", ".")
        elif "," in limpo:
            limpo = limpo.replace(",", ".")
        elif "." in limpo and limpo.count(".") == 1 and len(limpo.split(".")[1]) == 3:
            limpo = limpo.replace(".", "")
        return float(limpo)
    except Exception:
        return 0.0

def _get_local_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return os.getcwd()

def _has_credentials_configured():
    # No Cloud normalmente você terá st.secrets; esse check é leve (não conecta no Google)
    try:
        if "google_credentials" in st.secrets:
            return True
    except Exception:
        pass
    # fallback dev local
    caminho_json = os.path.join(_get_local_dir(), "credentials.json")
    return os.path.exists(caminho_json)

# =========================
# 5) CONEXÃO GOOGLE SHEETS
# =========================
def conectar_google():
    try:
        diretorio_atual = _get_local_dir()
        caminho_json = os.path.join(diretorio_atual, "credentials.json")

        # dev local
        if os.path.exists(caminho_json):
            return gspread.service_account(filename=caminho_json)

        # Streamlit Cloud (secrets)
        if "google_credentials" in st.secrets:
            creds_data = st.secrets["google_credentials"]["content"]
            creds_dict = json.loads(creds_data) if isinstance(creds_data, str) else dict(creds_data)

            if "private_key" in creds_dict and isinstance(creds_dict["private_key"], str):
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            return gspread.service_account_from_dict(creds_dict)

        st.error("❌ Credenciais não encontradas (Secrets).")
        return None

    except Exception as e:
        st.error(f"❌ Erro de conexão: {e}")
        return None

def get_worksheet_case_insensitive(sh, nome_procurado: str):
    for ws in sh.worksheets():
        if ws.title.strip().lower() == nome_procurado.strip().lower():
            return ws
    return None

# =========================
# 6) DADOS (CACHE)
# =========================
@st.cache_data(ttl=20, show_spinner=False)
def carregar_dados():
    client = conectar_google()
    if not client:
        return pd.DataFrame(columns=COLUNAS_LANC + ["_row_id"]), pd.DataFrame(columns=["Tipo", "Nome"])

    try:
        sh = client.open(SHEET_NAME)

        ws_lanc = get_worksheet_case_insensitive(sh, WS_LANC)
        if not ws_lanc:
            return pd.DataFrame(columns=COLUNAS_LANC + ["_row_id"]), pd.DataFrame(columns=["Tipo", "Nome"])

        dados_lanc = ws_lanc.get_all_values()

        if len(dados_lanc) <= 1:
            df_lanc = pd.DataFrame(columns=COLUNAS_LANC + ["_row_id"])
        else:
            linhas = []
            for i, row in enumerate(dados_lanc[1:]):
                if len(row) < len(COLUNAS_LANC):
                    row += [""] * (len(COLUNAS_LANC) - len(row))
                linhas.append(row[:len(COLUNAS_LANC)] + [i + 2])  # _row_id real do sheets
            df_lanc = pd.DataFrame(linhas, columns=COLUNAS_LANC + ["_row_id"])

        if not df_lanc.empty:
            df_lanc["Valor"] = df_lanc["Valor"].apply(parse_real_br)
            df_lanc["Ano"] = pd.to_numeric(df_lanc["Ano"], errors="coerce").fillna(date.today().year).astype(int)

        ws_cad = get_worksheet_case_insensitive(sh, WS_CAD)
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
        st.error(f"⚠️ Erro ao ler planilha: {e}")
        return pd.DataFrame(columns=COLUNAS_LANC + ["_row_id"]), pd.DataFrame(columns=["Tipo", "Nome"])

# =========================
# 7) ESCRITA NO SHEETS
# =========================
def salvar_lancamentos(lista_linhas):
    client = conectar_google()
    if not client:
        return False
    try:
        sh = client.open(SHEET_NAME)
        ws = get_worksheet_case_insensitive(sh, WS_LANC)
        if not ws:
            st.error("A aba 'lançamentos' não foi encontrada.")
            return False
        ws.append_rows(lista_linhas)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def excluir_linhas_google(lista_ids):
    client = conectar_google()
    if not client:
        return False
    try:
        sh = client.open(SHEET_NAME)
        ws = get_worksheet_case_insensitive(sh, WS_LANC)
        if not ws:
            st.error("A aba 'lançamentos' não foi encontrada.")
            return False

        for row_id in sorted(lista_ids, reverse=True):
            ws.delete_rows(row_id)

        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False

def salvar_cadastro_novo(tipo, nome):
    client = conectar_google()
    if not client:
        return False
    try:
        sh = client.open(SHEET_NAME)
        ws = get_worksheet_case_insensitive(sh, WS_CAD)
        if not ws:
            ws = sh.add_worksheet(title=WS_CAD, rows=200, cols=2)
            ws.append_row(["Tipo", "Nome"])

        ws.append_row([tipo, nome])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar cadastro: {e}")
        return False

# =========================
# 8) TELAS
# =========================
def tela_resumo(df):
    st.subheader("📊 Painel")

    if df.empty:
        st.info("Sem dados. Cadastre em 'Novo'.")
        return

    ano_atual = date.today().year
    anos_disp = sorted(df["Ano"].unique(), reverse=True)
    default_ano = ano_atual if ano_atual in anos_disp else anos_disp[0]

    with st.expander("🔎 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        ano_sel = c1.selectbox("Ano", anos_disp, index=anos_disp.index(default_ano))
        meses_disp = sorted(df["Mês"].dropna().unique())
        meses_sel = c2.multiselect("Meses", meses_disp)
        proj_sel = c3.multiselect("Projetos", sorted(df["Projeto"].dropna().unique()))
        cat_disp = sorted(df["Categoria"].dropna().unique())
        cat_sel = c4.multiselect("Categorias", cat_disp)

    df_f = df[df["Ano"] == ano_sel].copy()
    if meses_sel:
        df_f = df_f[df_f["Mês"].isin(meses_sel)]
    if proj_sel:
        df_f = df_f[df_f["Projeto"].isin(proj_sel)]
    if cat_sel:
        df_f = df_f[df_f["Categoria"].isin(cat_sel)]

    orcado = df_f[df_f["Tipo"] == "Orçado"]["Valor"].sum()
    realizado = df_f[df_f["Tipo"] == "Realizado"]["Valor"].sum()
    saldo = orcado - realizado

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Orçado", fmt_real(orcado))
    k2.metric("Realizado", fmt_real(realizado), delta=f"{(realizado / orcado * 100 if orcado else 0):.0f}%", delta_color="inverse")
    k3.metric("Saldo", fmt_real(saldo), delta="Dentro" if saldo >= 0 else "Estouro", delta_color="normal" if saldo >= 0 else "inverse")
    k4.metric("Projetos", f"{df_f['Projeto'].nunique()}")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📅 Mensal", "🏢 Projetos", "🏷️ Categorias"])

    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### Evolução Mensal (Orçado vs Realizado)")

        df_mes = df_f.groupby(["Mês", "Tipo"])["Valor"].sum().reset_index()
        if not df_mes.empty:
            df_mes["Mes_Num"] = df_mes["Mês"].apply(lambda x: int(str(x).split(" - ")[0]) if " - " in str(x) else 0)
            df_mes = df_mes.sort_values("Mes_Num")

            fig = px.bar(
                df_mes,
                x="Mês",
                y="Valor",
                color="Tipo",
                barmode="group",
                color_discrete_map={"Orçado": CORES["orcado"], "Realizado": CORES["realizado"]},
                text_auto=".2s",
            )
            fig.update_layout(
                height=420,
                margin=dict(l=20, r=20, t=10, b=70),
                xaxis_title=None,
                yaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados mensais.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("### 🌊 Fluxo de Caixa (Waterfall)")
        total_orcado = df_f[df_f["Tipo"] == "Orçado"]["Valor"].sum()
        df_gastos = (
            df_f[df_f["Tipo"] == "Realizado"]
            .groupby("Categoria")["Valor"]
            .sum()
            .reset_index()
            .sort_values("Valor", ascending=False)
        )

        if total_orcado > 0 or not df_gastos.empty:
            measures = ["absolute"]
            x_data = ["Orçamento Total"]
            y_data = [total_orcado]
            text_data = [fmt_real(total_orcado)]
            saldo_temp = total_orcado
            top_n = 6

            if len(df_gastos) > top_n:
                top = df_gastos.head(top_n)
                outros = df_gastos.iloc[top_n:]["Valor"].sum()

                for _, r in top.iterrows():
                    measures.append("relative")
                    x_data.append(r["Categoria"])
                    y_data.append(-r["Valor"])
                    text_data.append(f"-{fmt_real(r['Valor'])}")
                    saldo_temp -= r["Valor"]

                if outros > 0:
                    measures.append("relative")
                    x_data.append("Outros")
                    y_data.append(-outros)
                    text_data.append(f"-{fmt_real(outros)}")
                    saldo_temp -= outros
            else:
                for _, r in df_gastos.iterrows():
                    measures.append("relative")
                    x_data.append(r["Categoria"])
                    y_data.append(-r["Valor"])
                    text_data.append(f"-{fmt_real(r['Valor'])}")
                    saldo_temp -= r["Valor"]

            measures.append("total")
            x_data.append("Saldo Final")
            y_data.append(0)
            text_data.append(fmt_real(saldo_temp))

            fig_w = go.Figure(
                go.Waterfall(
                    name="Orçamento",
                    orientation="v",
                    measure=measures,
                    x=x_data,
                    textposition="outside",
                    text=text_data,
                    y=y_data,
                    connector={"line": {"color": "rgb(80, 80, 80)"}},
                    decreasing={"marker": {"color": CORES["alerta"]}},
                    totals={"marker": {"color": CORES["primaria"]}},
                )
            )
            fig_w.update_layout(height=430, margin=dict(l=20, r=20, t=10, b=50), waterfallgap=0.3)
            st.plotly_chart(fig_w, use_container_width=True)

    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### Orçado vs Realizado por Projeto")

        df_proj = df_f.groupby(["Projeto", "Tipo"])["Valor"].sum().unstack(fill_value=0).reset_index()
        if not df_proj.empty:
            if "Orçado" not in df_proj.columns:
                df_proj["Orçado"] = 0.0
            if "Realizado" not in df_proj.columns:
                df_proj["Realizado"] = 0.0

            df_proj = df_proj.sort_values("Orçado", ascending=False)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_proj["Projeto"], y=df_proj["Orçado"], name="Orçado", marker_color=CORES["orcado"], opacity=0.7))
            fig.add_trace(go.Bar(x=df_proj["Projeto"], y=df_proj["Realizado"], name="Realizado", marker_color=CORES["primaria"]))
            fig.update_layout(
                barmode="group",
                height=430,
                margin=dict(l=20, r=20, t=10, b=90),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados por projeto.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### Categorias (Top 10)")

        df_cat = df_f.groupby(["Categoria", "Tipo"])["Valor"].sum().unstack(fill_value=0).reset_index()
        if not df_cat.empty:
            if "Orçado" not in df_cat.columns:
                df_cat["Orçado"] = 0.0
            if "Realizado" not in df_cat.columns:
                df_cat["Realizado"] = 0.0

            df_cat = df_cat.sort_values("Orçado", ascending=False).head(10).sort_values("Orçado", ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(y=df_cat["Categoria"], x=df_cat["Orçado"], name="Meta", orientation="h", marker_color="#E5E7EB", width=0.75))
            fig.add_trace(go.Bar(y=df_cat["Categoria"], x=df_cat["Realizado"], name="Realizado", orientation="h", marker_color=CORES["realizado"], width=0.35))
            fig.update_layout(
                barmode="overlay",
                height=430,
                margin=dict(l=20, r=20, t=10, b=70),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados por categoria.")
        st.markdown("</div>", unsafe_allow_html=True)

def tela_novo(df_lanc, df_cad):
    st.subheader("➕ Novo Lançamento")

    if not df_cad.empty:
        lista_proj = sorted(df_cad[df_cad["Tipo"] == "Projeto"]["Nome"].dropna().unique().tolist())
        lista_cat = sorted(df_cad[df_cad["Tipo"] == "Categoria"]["Nome"].dropna().unique().tolist())
    else:
        st.warning("⚠️ Nenhum Projeto ou Categoria cadastrado.")
        lista_proj, lista_cat = [], []

    with st.form("form_novo", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.1, 1, 1])
        data_inicial = c1.date_input("Data Inicial", date.today())
        tipo = c2.selectbox("Tipo / Status", ["Orçado", "Realizado"])
        qtd_parcelas = c3.number_input("Nº Parcelas", min_value=1, value=1, step=1)

        c4, c5 = st.columns(2)
        proj_sel = c4.selectbox("Projeto", lista_proj, index=None, placeholder="Selecione...")
        cat_sel = c5.selectbox("Categoria", lista_cat, index=None, placeholder="Selecione...")

        c6, c7 = st.columns(2)
        valor = c6.number_input("Valor da Parcela (R$)", min_value=0.0, step=100.0)
        desc = c7.text_input("Descrição", placeholder="Opcional")

        c8, c9 = st.columns(2)
        envolvidos = c8.text_input("Envolvidos", placeholder="Ex: João, Maria, Fornecedor X")
        info_gerais = c9.text_area("Info gerais", placeholder="Observações livres...", height=90)

        submitted = st.form_submit_button("💾 Salvar", type="primary")

    # spinner + rerun (processamento fora do form)
    if submitted:
        if proj_sel is None or cat_sel is None:
            st.error("⚠️ Projeto e Categoria são obrigatórios.")
            return
        if valor == 0:
            st.error("⚠️ Valor não pode ser zero.")
            return

        linhas = []
        for i in range(int(qtd_parcelas)):
            data_calc = data_inicial + relativedelta(months=i)
            mes_str = f"{data_calc.month:02d} - {MESES_PT[data_calc.month]}"
            valor_fmt = fmt_real(valor)

            linhas.append([
                data_calc.strftime("%d/%m/%Y"),
                data_calc.year,
                mes_str,
                tipo,
                proj_sel,
                cat_sel,
                valor_fmt,
                desc,
                f"{i+1} de {int(qtd_parcelas)}",
                "Não",
                envolvidos,
                info_gerais,
            ])

        with st.spinner("Salvando lançamentos..."):
            ok = salvar_lancamentos(linhas)

        if ok:
            st.toast(f"✅ {int(qtd_parcelas)} lançamento(s) salvo(s)", icon="✅")
            st.rerun()
        else:
            st.error("❌ Erro ao salvar. Tente novamente.")

def tela_dados(df):
    st.subheader("📂 Base de Dados")

    if df.empty:
        st.info("A planilha está vazia.")
        return

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)

        anos_disp = sorted(df["Ano"].unique(), reverse=True)
        ano_atual = date.today().year
        default_ano = [ano_atual] if ano_atual in anos_disp else (anos_disp[:1] if anos_disp else [])
        filtro_ano = c1.multiselect("Ano (obrig.)", anos_disp, default=default_ano)

        meses_disp = sorted(df["Mês"].dropna().unique())
        filtro_mes = c2.multiselect("Mês", meses_disp)

        proj_disp = sorted(df["Projeto"].dropna().unique())
        filtro_proj = c3.multiselect("Projeto", proj_disp)

        tipo_disp = sorted(df["Tipo"].dropna().unique())
        filtro_tipo = c4.multiselect("Tipo", tipo_disp)

        cat_disp = sorted(df["Categoria"].dropna().unique())
        filtro_cat = c5.multiselect("Categoria", cat_disp)

    if not filtro_ano:
        st.warning("⚠️ Selecione pelo menos um ANO para visualizar os dados.")
        return

    df_view = df.copy()
    df_view = df_view[df_view["Ano"].isin(filtro_ano)]
    if filtro_mes:
        df_view = df_view[df_view["Mês"].isin(filtro_mes)]
    if filtro_proj:
        df_view = df_view[df_view["Projeto"].isin(filtro_proj)]
    if filtro_tipo:
        df_view = df_view[df_view["Tipo"].isin(filtro_tipo)]
    if filtro_cat:
        df_view = df_view[df_view["Categoria"].isin(filtro_cat)]

    # cálculos
    df_realizado = df_view[df_view["Tipo"] == "Realizado"].copy()
    df_consumo = df_realizado.groupby(["Ano", "Mês", "Projeto", "Categoria"])["Valor"].sum().reset_index()
    df_consumo.rename(columns={"Valor": "Valor_Consumido_Calc"}, inplace=True)

    df_final = pd.merge(df_view, df_consumo, on=["Ano", "Mês", "Projeto", "Categoria"], how="left")
    df_final["Valor_Consumido_Calc"] = df_final["Valor_Consumido_Calc"].fillna(0)

    cond_orcado = df_final["Tipo"] == "Orçado"
    df_final.loc[cond_orcado, "Valor Consumido"] = df_final.loc[cond_orcado, "Valor_Consumido_Calc"]
    df_final.loc[cond_orcado, "Diferença"] = df_final.loc[cond_orcado, "Valor"] - df_final.loc[cond_orcado, "Valor Consumido"]
    df_final.loc[cond_orcado, "Status"] = np.where(df_final.loc[cond_orcado, "Diferença"] < 0, "Estouro", "OK")

    cond_realizado = df_final["Tipo"] == "Realizado"
    df_final.loc[cond_realizado, "Abatido"] = "Sim"
    df_final.loc[cond_realizado, "Valor Consumido"] = None
    df_final.loc[cond_realizado, "Diferença"] = None
    df_final.loc[cond_realizado, "Status"] = None

    # topo: indicadores + download CSV
    ctop1, ctop2, ctop3 = st.columns([1.2, 1.2, 2])
    ctop1.metric("Registros", len(df_final))
    ctop2.metric("Total (filtrado)", fmt_real(df_final["Valor"].sum()))
    with ctop3:
        csv = df_final.drop(columns=["Valor_Consumido_Calc"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV (filtrado)", data=csv, file_name="orcamento_filtrado.csv", mime="text/csv")

    st.markdown("---")

    # paginação
    tamanho_pagina = 50
    total_paginas = max(1, math.ceil(len(df_final) / tamanho_pagina))
    if total_paginas > 1:
        col_pag, _ = st.columns([1, 4])
        pagina_atual = col_pag.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
    else:
        pagina_atual = 1

    inicio = (pagina_atual - 1) * tamanho_pagina
    fim = inicio + tamanho_pagina
    df_paginado = df_final.iloc[inicio:fim].copy()

    df_paginado["Excluir"] = False

    colunas_ordenadas = [
        "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria",
        "Valor", "Valor Consumido", "Diferença", "Status",
        "Descrição", "Envolvidos", "Info Gerais", "Parcela"
    ]
    cols_show = [c for c in colunas_ordenadas if c in df_paginado.columns] + ["Excluir"]

    df_edited = st.data_editor(
        df_paginado[cols_show],
        column_config={
            "Excluir": st.column_config.CheckboxColumn("🗑️", width="small", default=False),
            "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "Valor Consumido": st.column_config.NumberColumn("Consumido", format="R$ %.2f", disabled=True),
            "Diferença": st.column_config.NumberColumn("Diferença", format="R$ %.2f", disabled=True),
            "Status": st.column_config.TextColumn("Status", disabled=True),
        },
        disabled=[
            "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria", "Valor",
            "Descrição", "Parcela", "Envolvidos", "Info Gerais"
        ],
        hide_index=True,
        use_container_width=True,
        key=f"editor_dados_pag_{pagina_atual}",
    )

    linhas_para_excluir = df_edited[df_edited["Excluir"] == True]
    if not linhas_para_excluir.empty:
        st.warning(f"⚠️ {len(linhas_para_excluir)} registro(s) marcado(s) para exclusão.")

        @st.dialog("Confirmar exclusão")
        def confirmar_exclusao(ids_reais):
            st.write(f"Tem certeza que deseja excluir {len(ids_reais)} registro(s)?")
            c1, c2 = st.columns(2)
            if c1.button("Cancelar"):
                st.rerun()
            if c2.button("Sim, excluir", type="primary"):
                with st.spinner("Excluindo..."):
                    ok = excluir_linhas_google(ids_reais)
                if ok:
                    st.success("✅ Registros excluídos.")
                    st.rerun()
                else:
                    st.error("❌ Falha ao excluir. Tente novamente.")

        if st.button("🗑️ Excluir selecionados", type="primary"):
            idx = linhas_para_excluir.index
            if "_row_id" in df_paginado.columns:
                ids_reais = df_paginado.loc[idx, "_row_id"].tolist()
                confirmar_exclusao(ids_reais)
            else:
                st.error("Não encontrei _row_id para mapear exclusão.")

def tela_cadastros(df_cad):
    st.subheader("⚙️ Cadastros")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### 🏢 Projetos")
        with st.form("form_add_proj", clear_on_submit=True):
            novo_proj = st.text_input("Novo Projeto", placeholder="Ex: Obra X / Cliente Y")
            submitted = st.form_submit_button("Adicionar", type="primary")
        if submitted and novo_proj:
            with st.spinner("Salvando..."):
                ok = salvar_cadastro_novo("Projeto", novo_proj)
            if ok:
                st.toast("✅ Projeto salvo", icon="✅")
                st.rerun()

        if not df_cad.empty:
            st.dataframe(
                df_cad[df_cad["Tipo"] == "Projeto"][["Nome"]].sort_values("Nome"),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write("### 🏷️ Categorias")
        with st.form("form_add_cat", clear_on_submit=True):
            nova_cat = st.text_input("Nova Categoria", placeholder="Ex: Materiais / Mão de obra")
            submitted2 = st.form_submit_button("Adicionar", type="primary")
        if submitted2 and nova_cat:
            with st.spinner("Salvando..."):
                ok = salvar_cadastro_novo("Categoria", nova_cat)
            if ok:
                st.toast("✅ Categoria salva", icon="✅")
                st.rerun()

        if not df_cad.empty:
            st.dataframe(
                df_cad[df_cad["Tipo"] == "Categoria"][["Nome"]].sort_values("Nome"),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

# =========================
# 9) APP (NAVEGAÇÃO APP-LIKE)
# =========================
def main():
    df_lancamentos, df_cadastros = carregar_dados()

    # header do app
    c1, c2, c3 = st.columns([3, 1.3, 1.2])
    with c1:
        st.title(f"💰 {APP_TITLE}")
        st.caption("orçado x realizado, por projeto e categoria")
    with c2:
        ok = _has_credentials_configured()
        st.markdown(
            f"<div class='card' style='padding:10px 12px; text-align:center;'>"
            f"{'✅ credenciais ok' if ok else '⚠️ sem credenciais'}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("🔄 Atualizar", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()

    # navegação estilo app
    opcoes = ["📊 Painel", "➕ Novo", "📂 Dados", "⚙️ Cadastros"]
    try:
        escolha = st.segmented_control(
            "Navegação",
            options=opcoes,
            default="📊 Painel",
            label_visibility="collapsed",
        )
    except Exception:
        escolha = st.radio("Navegação", opcoes, horizontal=True, label_visibility="collapsed")

    st.markdown("---")

    if escolha == "📊 Painel":
        tela_resumo(df_lancamentos)
    elif escolha == "➕ Novo":
        tela_novo(df_lancamentos, df_cadastros)
    elif escolha == "📂 Dados":
        tela_dados(df_lancamentos)
    elif escolha == "⚙️ Cadastros":
        tela_cadastros(df_cadastros)

if __name__ == "__main__":
    main()
