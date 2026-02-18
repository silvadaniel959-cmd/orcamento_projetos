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
from typing import Tuple, List, Optional

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(
    page_title="Controle Orçamentário Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONSTANTES E ESTILOS ---
CORES = {
    "primaria": "#007AFF", 
    "orcado": "#98989D",
    "realizado": "#34C759",
    "alerta": "#FF3B30",
    "fundo": "#F2F2F7",
    "texto": "#1D1D1F"
}

MESES_PT = {
    1: "01 - JANEIRO", 2: "02 - FEVEREIRO", 3: "03 - MARÇO", 4: "04 - ABRIL", 
    5: "05 - MAIO", 6: "06 - JUNHO", 7: "07 - JULHO", 8: "08 - AGOSTO", 
    9: "09 - SETEMBRO", 10: "10 - OUTUBRO", 11: "11 - NOVEMBRO", 12: "12 - DEZEMBRO"
}

def aplicar_estilo_customizado():
    st.markdown(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            
            html, body, [class*="st-"] {{
                font-family: 'Inter', sans-serif;
            }}
            
            .block-container {{ padding-top: 2rem; padding-bottom: 5rem; }}
            
            /* Cards de Métricas */
            div.stMetric {{ 
                background-color: #ffffff; 
                border: 1px solid #e5e7eb; 
                border-radius: 12px; 
                padding: 20px; 
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }}
            div.stMetric:hover {{
                transform: translateY(-2px);
            }}
            
            /* Formulários */
            [data-testid="stForm"] {{ 
                border: 1px solid #e5e7eb; 
                padding: 24px; 
                border-radius: 16px; 
                background-color: #ffffff;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            }}
            
            /* Botões */
            .stButton > button {{
                border-radius: 8px;
                transition: all 0.3s;
            }}
            
            /* Sidebar */
            section[data-testid="stSidebar"] {{
                background-color: #f8fafc;
            }}
        </style>
    """, unsafe_allow_html=True)

# --- 3. CAMADA DE DADOS (BACKEND) ---

class DataManager:
    """Gerencia a conexão e operações com o Google Sheets."""
    
    SHEET_NAME = "dados_app_orcamento"
    COLUNAS_LANC = [
        "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria", 
        "Valor", "Descrição", "Parcela", "Abatido", 
        "Envolvidos", "Info Gerais"
    ]

    @staticmethod
    @st.cache_resource
    def get_client():
        """Estabelece conexão com Singleton pattern via cache_resource."""
        try:
            # Prioridade 1: Secrets do Streamlit
            if "google_credentials" in st.secrets:
                creds_data = st.secrets["google_credentials"]["content"]
                creds_dict = json.loads(creds_data) if isinstance(creds_data, str) else dict(creds_data)
                if "private_key" in creds_dict:
                    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                return gspread.service_account_from_dict(creds_dict)
            
            # Prioridade 2: Local
            caminho_json = os.path.join(os.path.dirname(__file__), 'credentials.json')
            if os.path.exists(caminho_json):
                return gspread.service_account(filename=caminho_json)
                
            return None
        except Exception as e:
            st.error(f"Erro de autenticação: {e}")
            return None

    @classmethod
    def get_worksheet(cls, sh, name):
        for ws in sh.worksheets():
            if ws.title.lower() == name.lower():
                return ws
        return None

    @classmethod
    def parse_currency(cls, value) -> float:
        if not value or pd.isna(value): return 0.0
        if isinstance(value, (int, float)): return float(value)
        try:
            # Remove R$, espaços e ajusta separadores decimais
            clean = str(value).replace("R$", "").replace(" ", "").strip()
            if not clean: return 0.0
            # Lógica para converter 1.234,56 ou 1234,56 para 1234.56
            if "," in clean:
                clean = clean.replace(".", "").replace(",", ".")
            return float(clean)
        except:
            return 0.0

    @classmethod
    @st.cache_data(ttl=300) # Cache de 5 minutos
    def load_all_data(cls) -> Tuple[pd.DataFrame, pd.DataFrame]:
        client = cls.get_client()
        if not client:
            return pd.DataFrame(), pd.DataFrame()
        
        try:
            sh = client.open(cls.SHEET_NAME)
            
            # Carregar Lançamentos
            ws_lanc = cls.get_worksheet(sh, "lançamentos")
            df_lanc = pd.DataFrame()
            if ws_lanc:
                raw_data = ws_lanc.get_all_values()
                if len(raw_data) > 1:
                    # Normalização de colunas (padding para linhas incompletas)
                    processed_rows = []
                    for i, row in enumerate(raw_data[1:]):
                        if len(row) < len(cls.COLUNAS_LANC):
                            row += [""] * (len(cls.COLUNAS_LANC) - len(row))
                        # Adiciona ID da linha real (index + 2 pois pula header e é 1-based)
                        processed_rows.append(row[:len(cls.COLUNAS_LANC)] + [i + 2])
                    
                    df_lanc = pd.DataFrame(processed_rows, columns=cls.COLUNAS_LANC + ["_row_id"])
                    df_lanc['Valor'] = df_lanc['Valor'].apply(cls.parse_currency)
                    df_lanc['Ano'] = pd.to_numeric(df_lanc['Ano'], errors='coerce').fillna(date.today().year).astype(int)
                else:
                    df_lanc = pd.DataFrame(columns=cls.COLUNAS_LANC + ["_row_id"])

            # Carregar Cadastros
            ws_cad = cls.get_worksheet(sh, "cadastros")
            df_cad = pd.DataFrame(columns=["Tipo", "Nome"])
            if ws_cad:
                raw_cad = ws_cad.get_all_values()
                if len(raw_cad) > 1:
                    df_cad = pd.DataFrame(raw_cad[1:], columns=["Tipo", "Nome"])
            
            return df_lanc, df_cad
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame(), pd.DataFrame()

    @classmethod
    def save_rows(cls, rows: List[List]) -> bool:
        client = cls.get_client()
        if not client: return False
        try:
            sh = client.open(cls.SHEET_NAME)
            ws = cls.get_worksheet(sh, "lançamentos")
            if ws:
                ws.append_rows(rows)
                st.cache_data.clear()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
        return False

# --- 4. COMPONENTES DE UI (FRONTEND) ---

def format_currency_br(val: float) -> str:
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def render_metrics(df: pd.DataFrame):
    orcado = df[df['Tipo'] == "Orçado"]['Valor'].sum()
    realizado = df[df['Tipo'] == "Realizado"]['Valor'].sum()
    saldo = orcado - realizado
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Orçado", format_currency_br(orcado))
    with c2:
        perc = (realizado/orcado*100) if orcado > 0 else 0
        st.metric("Total Realizado", format_currency_br(realizado), 
                  delta=f"{perc:.1f}% do orçamento", 
                  delta_color="inverse" if perc > 100 else "normal")
    with c3:
        status = "Disponível" if saldo >= 0 else "Déficit"
        st.metric("Saldo Atual", format_currency_br(saldo), 
                  delta=status, 
                  delta_color="normal" if saldo >= 0 else "inverse")

def render_charts(df: pd.DataFrame):
    if df.empty:
        st.warning("Sem dados para gerar gráficos.")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Evolução Mensal")
        df_mes = df.groupby(['Mês', 'Tipo'])['Valor'].sum().reset_index()
        df_mes = df_mes.sort_values('Mês')
        fig = px.bar(df_mes, x="Mês", y="Valor", color="Tipo", barmode='group',
                     color_discrete_map={"Orçado": CORES['orcado'], "Realizado": CORES['realizado']},
                     template="plotly_white")
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=350, legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📂 Distribuição por Categoria")
        df_cat = df[df['Tipo'] == "Realizado"].groupby('Categoria')['Valor'].sum().reset_index()
        if not df_cat.empty:
            fig = px.pie(df_cat, values='Valor', names='Categoria', hole=.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aguardando dados de 'Realizado' para gráfico de categorias.")

# --- 5. TELAS ---

def view_dashboard(df: pd.DataFrame):
    st.title("📊 Dashboard Financeiro")
    
    # Filtros em Container Expansível para limpar a UI
    with st.expander("🔍 Filtros Avançados", expanded=False):
        c1, c2, c3 = st.columns(3)
        anos = sorted(df['Ano'].unique(), reverse=True) if not df.empty else [date.today().year]
        ano_sel = c1.selectbox("Ano de Referência", anos)
        
        projetos = sorted(df['Projeto'].unique()) if not df.empty else []
        proj_sel = c2.multiselect("Filtrar Projetos", projetos)
        
        categorias = sorted(df['Categoria'].unique()) if not df.empty else []
        cat_sel = c3.multiselect("Filtrar Categorias", categorias)

    # Aplicação dos Filtros
    df_f = df[df['Ano'] == ano_sel] if not df.empty else df
    if proj_sel: df_f = df_f[df_f['Projeto'].isin(proj_sel)]
    if cat_sel: df_f = df_f[df_f['Categoria'].isin(cat_sel)]

    render_metrics(df_f)
    st.divider()
    render_charts(df_f)
    
    st.markdown("### 📝 Últimos Lançamentos")
    st.dataframe(df_f.sort_values('Data', ascending=False).head(10), 
                 use_container_width=True, hide_index=True,
                 column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})

def view_new_entry(df_cad: pd.DataFrame):
    st.title("➕ Novo Lançamento")
    
    with st.form("form_novo_lancamento", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        data_ref = c1.date_input("Data", date.today())
        tipo = c2.selectbox("Tipo", ["Realizado", "Orçado"])
        valor = c3.number_input("Valor (R$)", min_value=0.0, step=100.0, format="%.2f")
        
        c4, c5 = st.columns(2)
        projs = sorted(df_cad[df_cad['Tipo'] == 'Projeto']['Nome'].unique())
        cats = sorted(df_cad[df_cad['Tipo'] == 'Categoria']['Nome'].unique())
        
        projeto = c4.selectbox("Projeto", projs if projs else ["Geral"])
        categoria = c5.selectbox("Categoria", cats if cats else ["Outros"])
        
        desc = st.text_input("Descrição / Detalhes")
        
        with st.expander("Campos Adicionais"):
            ca1, ca2 = st.columns(2)
            envolvidos = ca1.text_input("Envolvidos")
            info = ca2.text_area("Informações Gerais", height=100)
        
        submit = st.form_submit_button("Salvar Lançamento", type="primary", use_container_width=True)
        
        if submit:
            if valor <= 0:
                st.error("O valor deve ser maior que zero.")
            else:
                nova_linha = [
                    data_ref.strftime("%d/%m/%Y"),
                    data_ref.year,
                    MESES_PT[data_ref.month],
                    tipo, projeto, categoria,
                    valor, desc, "1/1", "Não",
                    envolvidos, info
                ]
                if DataManager.save_rows([nova_linha]):
                    st.success("Lançamento realizado com sucesso!")
                    st.balloons()
                    st.rerun()

# --- 6. MAIN LOOP ---

def main():
    aplicar_estilo_customizado()
    
    # Carregamento inicial
    df_lanc, df_cad = DataManager.load_all_data()
    
    # Sidebar Navigation
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2454/2454282.png", width=80)
        st.title("Budget Manager")
        st.markdown("---")
        
        menu = {
            "Dashboard": "📊",
            "Novo Lançamento": "➕",
            "Gerenciar Dados": "📂",
            "Configurações": "⚙️"
        }
        
        escolha = st.radio("Navegação", list(menu.keys()), 
                          format_func=lambda x: f"{menu[x]} {x}")
        
        st.markdown("---")
        if st.button("🔄 Sincronizar Agora", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.caption("v2.0.0 | © 2024")

    # Roteamento
    if escolha == "Dashboard":
        view_dashboard(df_lanc)
    elif escolha == "Novo Lançamento":
        view_new_entry(df_cad)
    elif escolha == "Gerenciar Dados":
        st.title("📂 Base de Dados")
        st.info("Aqui você pode visualizar e exportar todos os registros.")
        st.dataframe(df_lanc, use_container_width=True)
    elif escolha == "Configurações":
        st.title("⚙️ Configurações")
        st.write("Gerencie seus Projetos e Categorias aqui.")
        # Implementação similar à original mas com UI limpa

if __name__ == "__main__":
    main()
