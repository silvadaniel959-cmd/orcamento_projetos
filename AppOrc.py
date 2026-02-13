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
    page_title="Controle Orçamentário",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILO CSS (UI/UX OTIMIZADO) ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 5rem; }
        div.stMetric { 
            background-color: #ffffff; 
            border: 1px solid #e5e7eb; 
            border-radius: 10px; 
            padding: 15px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
        }
        [data-testid="stForm"] { 
            border: 1px solid #e5e7eb; 
            padding: 24px; 
            border-radius: 12px; 
            background-color: #f9fafb;
            box-shadow: none;
        }
        button[kind="primary"] {
            border-radius: 8px;
            font-weight: 600;
        }
        hr { margin-top: 2rem; margin-bottom: 2rem; border-color: #e5e7eb; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONSTANTES ---
CORES = {
    "primaria": "#007AFF", 
    "orcado": "#98989D",
    "realizado": "#34C759",
    "alerta": "#FF3B30",
    "fundo": "#F2F2F7"
}

MESES_PT = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}

# --- 4. CONEXÃO ---
def conectar_google():
    try:
        # Tenta local primeiro (VS Code)
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_json = os.path.join(diretorio_atual, 'credentials.json')

        if os.path.exists(caminho_json):
            return gspread.service_account(filename=caminho_json)
        
        # Se não houver arquivo, usa os Secrets (Streamlit Cloud)
        elif "google_credentials" in st.secrets:
            # Pega o conteúdo do campo 'content' que você colou
            creds_data = st.secrets["google_credentials"]["content"]
            
            # Se o Streamlit entregar como texto, transforma em dicionário
            if isinstance(creds_data, str):
                creds_dict = json.loads(creds_data)
            else:
                # Se já vier como objeto, converte para dicionário puro
                creds_dict = dict(creds_data)
            
            # --- CURA PARA O ERRO DE PEM ---
            # Garante que as quebras de linha da chave privada sejam reais
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                
            return gspread.service_account_from_dict(creds_dict)
            
        else:
            st.error("❌ Credenciais não encontradas nos Segredos ou localmente.")
            return None
    except Exception as e:
        st.error(f"❌ Erro de conexão detalhado: {e}")
        return None

def get_worksheet_case_insensitive(sh, nome_procurado):
    for ws in sh.worksheets():
        if ws.title.lower() == nome_procurado.lower():
            return ws
    return None

# --- 5. CARREGAMENTO DE DADOS (CACHEADO) ---
@st.cache_data(ttl=60)
def carregar_dados():
    client = conectar_google()
    if not client: return pd.DataFrame(), pd.DataFrame()
    
    try:
        sh = client.open("dados_app_orcamento")
        
        # 1. Carrega Lançamentos
        ws_lanc = get_worksheet_case_insensitive(sh, "lançamentos")
        if not ws_lanc:
            return pd.DataFrame(), pd.DataFrame()

        dados_lanc = ws_lanc.get_all_values()
        
        # ATUALIZADO: Incluindo novas colunas na estrutura de leitura
        colunas_lanc = [
            "Data", "Ano", "Mês", "Tipo", "Projeto", "Categoria", 
            "Valor", "Descrição", "Parcela", "Abatido", 
            "Envolvidos", "Info Gerais" # NOVOS CAMPOS
        ]
        
        if len(dados_lanc) <= 1:
            df_lanc = pd.DataFrame(columns=colunas_lanc)
        else:
            linhas = []
            for i, l in enumerate(dados_lanc[1:]):
                # Padding: Se a linha antiga for menor que as novas colunas, completa com vazio
                if len(l) < len(colunas_lanc): l += [""] * (len(colunas_lanc) - len(l))
                
                linha_com_id = l[:len(colunas_lanc)] + [i + 2] 
                linhas.append(linha_com_id)
            
            df_lanc = pd.DataFrame(linhas, columns=colunas_lanc + ["_row_id"])

        def converter_br(v):
            try:
                if not v: return 0.0
                limpo = str(v).replace("R$", "").replace(" ", "")
                if "," in limpo and "." in limpo: limpo = limpo.replace(".", "").replace(",", ".")
                elif "," in limpo: limpo = limpo.replace(",", ".")
                elif "." in limpo and limpo.count(".") == 1 and len(limpo.split(".")[1]) == 3: limpo = limpo.replace(".", "")
                return float(limpo)
            except: return 0.0

        if not df_lanc.empty:
            df_lanc['Valor'] = df_lanc['Valor'].apply(converter_br)
            df_lanc['Ano'] = pd.to_numeric(df_lanc['Ano'], errors='coerce').fillna(date.today().year).astype(int)

        # 2. Carrega Cadastros
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
        st.error(f"⚠️ Erro crítico ao ler planilha: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- FUNÇÕES DE ESCRITA ---
def salvar_lancamentos(lista_linhas):
    client = conectar_google()
    if client:
        try:
            sh = client.open("dados_app_orcamento")
            ws = get_worksheet_case_insensitive(sh, "lançamentos")
            if ws:
                ws.append_rows(lista_linhas) 
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

# --- 6. TELAS DO SISTEMA ---

def tela_resumo(df):
    st.subheader("📊 Painel")
    
    if df.empty:
        st.info("Sem dados. Cadastre em 'Novo'.")
        return

    ano_atual = date.today().year
    anos_disponiveis = sorted(df['Ano'].unique(), reverse=True)
    default_ano = ano_atual if ano_atual in anos_disponiveis else (anos_disponiveis[0] if anos_disponiveis else None)

    with st.form("form_filtros_painel"):
        st.write("Configuração de Visualização")
        c1, c2, c3, c4 = st.columns(4)
        ano_sel = c1.selectbox("Ano", anos_disponiveis, index=anos_disponiveis.index(default_ano) if default_ano else 0)
        meses_disp = sorted(df['Mês'].unique()) 
        meses_sel = c2.multiselect("Meses", meses_disp)
        proj_sel = c3.multiselect("Projetos", df['Projeto'].unique())
        cat_disp = sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else []
        cat_sel = c4.multiselect("Categorias", cat_disp)
        submitted = st.form_submit_button("Aplicar Filtros", type="primary")

    df_f = df[df['Ano'] == ano_sel]
    if meses_sel: df_f = df_f[df_f['Mês'].isin(meses_sel)]
    if proj_sel: df_f = df_f[df_f['Projeto'].isin(proj_sel)]
    if cat_sel: df_f = df_f[df_f['Categoria'].isin(cat_sel)] 

    orcado = df_f[df_f['Tipo'] == "Orçado"]['Valor'].sum()
    realizado = df_f[df_f['Tipo'] == "Realizado"]['Valor'].sum()
    saldo = orcado - realizado

    def fmt_real(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    k1, k2, k3 = st.columns(3)
    k1.metric("Orçado", fmt_real(orcado))
    k2.metric("Realizado", fmt_real(realizado), delta=f"{(realizado/orcado*100 if orcado else 0):.0f}%", delta_color="inverse")
    k3.metric("Saldo", fmt_real(saldo), delta="Disp." if saldo >= 0 else "Estouro", delta_color="normal" if saldo >= 0 else "inverse")

    st.markdown("---")

    # Gráfico 1: Mês a Mês
    st.write("### 📅 Evolução Mensal")
    df_mes = df_f.groupby(['Mês', 'Tipo'])['Valor'].sum().reset_index()
    if not df_mes.empty:
        df_mes['Mes_Num'] = df_mes['Mês'].apply(lambda x: int(x.split(' - ')[0]) if ' - ' in x else 0)
        df_mes = df_mes.sort_values('Mes_Num')
        fig_mes = px.bar(df_mes, x="Mês", y="Valor", color="Tipo", barmode='group',
            color_discrete_map={"Orçado": CORES['orcado'], "Realizado": CORES['realizado']}, text_auto='.2s')
        
        fig_mes.update_layout(
            height=400, 
            margin=dict(l=20, r=20, t=10, b=50),
            xaxis_title=None, 
            yaxis_title=None,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_mes, use_container_width=True)
    else:
        st.info("Sem dados mensais.")

    c_g1, c_g2 = st.columns(2)

    with c_g1:
        st.write("### 🏢 Projetos: Orçado vs Realizado")
        df_proj = df_f.groupby(['Projeto', 'Tipo'])['Valor'].sum().unstack(fill_value=0).reset_index()
        if not df_proj.empty:
            if 'Orçado' not in df_proj.columns: df_proj['Orçado'] = 0.0
            if 'Realizado' not in df_proj.columns: df_proj['Realizado'] = 0.0
            
            fig_bib = go.Figure()
            fig_bib.add_trace(go.Bar(x=df_proj['Projeto'], y=df_proj['Orçado'], name='Orçado', marker_color=CORES['orcado'], opacity=0.6, width=0.6))
            fig_bib.add_trace(go.Bar(x=df_proj['Projeto'], y=df_proj['Realizado'], name='Realizado', marker_color=CORES['primaria'], width=0.3))
            
            fig_bib.update_layout(
                barmode='overlay', height=350, margin=dict(l=20, r=20, t=10, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_bib, use_container_width=True)

    with c_g2:
        st.write("### 🏷️ Categorias (Bullet Graph)")
        df_cat = df_f.groupby(['Categoria', 'Tipo'])['Valor'].sum().unstack(fill_value=0).reset_index()
        if not df_cat.empty:
            if 'Orçado' not in df_cat.columns: df_cat['Orçado'] = 0.0
            if 'Realizado' not in df_cat.columns: df_cat['Realizado'] = 0.0
            
            df_cat = df_cat.sort_values('Orçado', ascending=True).tail(10)
            
            fig_bullet = go.Figure()
            fig_bullet.add_trace(go.Bar(y=df_cat['Categoria'], x=df_cat['Orçado'], name='Meta', orientation='h', marker_color='#E5E7EB', width=0.7))
            fig_bullet.add_trace(go.Bar(y=df_cat['Categoria'], x=df_cat['Realizado'], name='Realizado', orientation='h', marker_color=CORES['realizado'], width=0.3))
            fig_bullet.add_trace(go.Scatter(y=df_cat['Categoria'], x=df_cat['Orçado'], mode='markers', name='Limite', marker=dict(symbol='line-ns-open', size=25, color='black', line=dict(width=2))))
            
            fig_bullet.update_layout(
                barmode='overlay', height=350, margin=dict(l=20, r=20, t=10, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_bullet, use_container_width=True)

    st.write("### 🌊 Fluxo de Caixa (Waterfall)")
    total_orcado = df_f[df_f['Tipo'] == 'Orçado']['Valor'].sum()
    df_gastos = df_f[df_f['Tipo'] == 'Realizado'].groupby('Categoria')['Valor'].sum().reset_index().sort_values('Valor', ascending=False)
    
    if total_orcado > 0 or not df_gastos.empty:
        measures = ["absolute"]; x_data = ["Orçamento Total"]; y_data = [total_orcado]; text_data = [fmt_real(total_orcado)]
        saldo_temp = total_orcado
        top_n = 6
        
        if len(df_gastos) > top_n:
            top_gastos = df_gastos.head(top_n)
            outros_val = df_gastos.iloc[top_n:]['Valor'].sum()
            for _, row in top_gastos.iterrows():
                measures.append("relative"); x_data.append(row['Categoria']); y_data.append(-row['Valor']); text_data.append(f"-{fmt_real(row['Valor'])}"); saldo_temp -= row['Valor']
            if outros_val > 0:
                measures.append("relative"); x_data.append("Outros"); y_data.append(-outros_val); text_data.append(f"-{fmt_real(outros_val)}"); saldo_temp -= outros_val
        else:
            for _, row in df_gastos.iterrows():
                measures.append("relative"); x_data.append(row['Categoria']); y_data.append(-row['Valor']); text_data.append(f"-{fmt_real(row['Valor'])}"); saldo_temp -= row['Valor']
        
        measures.append("total"); x_data.append("Saldo Final"); y_data.append(0); text_data.append(fmt_real(saldo_temp))
        
        fig_water = go.Figure(go.Waterfall(
            name="Orçamento", orientation="v", measure=measures, x=x_data, textposition="outside", text=text_data, y=y_data,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": CORES['alerta']}}, increasing={"marker": {"color": CORES['realizado']}}, totals={"marker": {"color": CORES['primaria']}}
        ))
        fig_water.update_layout(height=400, margin=dict(l=20, r=20, t=10, b=50), waterfallgap=0.3)
        st.plotly_chart(fig_water, use_container_width=True)

def tela_novo(df_lanc, df_cad):
    st.subheader("➕ Novo Lançamento")

    if not df_cad.empty:
        lista_proj = sorted(df_cad[df_cad['Tipo'] == 'Projeto']['Nome'].unique().tolist())
        lista_cat = sorted(df_cad[df_cad['Tipo'] == 'Categoria']['Nome'].unique().tolist())
    else:
        st.warning("⚠️ Nenhum Projeto ou Categoria cadastrado.")
        lista_proj = []; lista_cat = []

    with st.form("form_novo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        data_inicial = c1.date_input("Data Inicial", date.today())
        tipo = c2.selectbox("Tipo / Status", ["Orçado", "Realizado"])
        proj_sel = st.selectbox("Projeto", lista_proj, index=None, placeholder="Selecione..."); cat_sel = st.selectbox("Categoria", lista_cat, index=None, placeholder="Selecione...")
        c3, c4 = st.columns(2)
        valor = c3.number_input("Valor da Parcela (R$)", min_value=0.0, step=100.0); qtd_parcelas = c4.number_input("Nº Parcelas", min_value=1, value=1, step=1)
        desc = st.text_input("Descrição", placeholder="Opcional")
        
        # --- NOVOS CAMPOS AQUI ---
        c5, c6 = st.columns(2)
        envolvidos = c5.text_input("Envolvidos no Projeto", placeholder="Ex: João, Maria, Fornecedor X")
        info_gerais = c6.text_area("Informações Gerais", placeholder="Observações livres...", height=100)
        
        if st.form_submit_button("💾 Salvar", type="primary"):
            if proj_sel is None or cat_sel is None: st.error("⚠️ Projeto e Categoria são obrigatórios.")
            elif valor == 0: st.error("⚠️ Valor não pode ser zero.")
            else:
                linhas = []
                for i in range(qtd_parcelas):
                    data_calc = data_inicial + relativedelta(months=i)
                    mes_str = f"{data_calc.month:02d} - {MESES_PT[data_calc.month]}"
                    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    # Incluindo os novos campos na lista para salvar
                    nova_linha = [
                        data_calc.strftime("%d/%m/%Y"), data_calc.year, mes_str, 
                        tipo, proj_sel, cat_sel, valor_fmt, desc, 
                        f"{i+1} de {qtd_parcelas}", "Não",
                        envolvidos, info_gerais # Adicionados
                    ]
                    linhas.append(nova_linha)
                if salvar_lancamentos(linhas): st.toast(f"Sucesso! {qtd_parcelas} lançamentos gerados.", icon="✅")

def tela_dados(df):
    st.subheader("📂 Base de Dados Detalhada")
    
    if df.empty:
        st.info("A planilha está vazia.")
        return

    with st.form("form_filtros_dados"):
        st.write("🔍 **Filtros de Pesquisa**")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        anos_disp = sorted(df['Ano'].unique(), reverse=True) if 'Ano' in df.columns else []
        ano_atual = date.today().year; default_ano = [ano_atual] if ano_atual in anos_disp else []
        filtro_ano = c1.multiselect("Ano (Obrig.)", anos_disp, default=default_ano)
        
        meses_disp = sorted(df['Mês'].unique()) if 'Mês' in df.columns else []; filtro_mes = c2.multiselect("Mês", meses_disp)
        proj_disp = sorted(df['Projeto'].unique()) if 'Projeto' in df.columns else []; filtro_proj = c3.multiselect("Projeto", proj_disp)
        tipo_disp = sorted(df['Tipo'].unique()) if 'Tipo' in df.columns else []; filtro_tipo = c4.multiselect("Tipo", tipo_disp)
        cat_disp = sorted(df['Categoria'].unique()) if 'Categoria' in df.columns else []; filtro_cat = c5.multiselect("Categoria", cat_disp)

        btn_filtrar = st.form_submit_button("Aplicar Filtros", type="primary")

    if 'dados_filtro_ativo' not in st.session_state: st.session_state.dados_filtro_ativo = False
    if btn_filtrar: st.session_state.dados_filtro_ativo = True

    if not filtro_ano:
        st.warning("⚠️ Selecione pelo menos um ANO para visualizar os dados.")
        st.session_state.dados_filtro_ativo = False
        return

    df_view = df.copy()
    if filtro_ano: df_view = df_view[df_view['Ano'].isin(filtro_ano)]
    if filtro_mes: df_view = df_view[df_view['Mês'].isin(filtro_mes)]
    if filtro_proj: df_view = df_view[df_view['Projeto'].isin(filtro_proj)]
    if filtro_tipo: df_view = df_view[df_view['Tipo'].isin(filtro_tipo)]
    if filtro_cat: df_view = df_view[df_view['Categoria'].isin(filtro_cat)]

    # CÁLCULOS
    df_realizado = df_view[df_view['Tipo'] == 'Realizado'].copy()
    df_consumo = df_realizado.groupby(['Ano', 'Mês', 'Projeto', 'Categoria'])['Valor'].sum().reset_index()
    df_consumo.rename(columns={'Valor': 'Valor_Consumido_Calc'}, inplace=True)
    
    df_final = pd.merge(df_view, df_consumo, on=['Ano', 'Mês', 'Projeto', 'Categoria'], how='left')
    df_final['Valor_Consumido_Calc'] = df_final['Valor_Consumido_Calc'].fillna(0)
    
    # Regras
    condicao_orcado = df_final['Tipo'] == 'Orçado'
    df_final.loc[condicao_orcado, 'Valor Consumido'] = df_final.loc[condicao_orcado, 'Valor_Consumido_Calc']
    df_final.loc[condicao_orcado, 'Diferença'] = df_final.loc[condicao_orcado, 'Valor'] - df_final.loc[condicao_orcado, 'Valor Consumido']
    df_final.loc[condicao_orcado, 'Status'] = np.where(df_final.loc[condicao_orcado, 'Diferença'] < 0, "Estouro", "OK")
    
    condicao_realizado = df_final['Tipo'] == 'Realizado'
    df_final.loc[condicao_realizado, 'Abatido'] = "Sim" 
    df_final.loc[condicao_realizado, 'Valor Consumido'] = None
    df_final.loc[condicao_realizado, 'Diferença'] = None
    df_final.loc[condicao_realizado, 'Status'] = None

    st.markdown(f"**Total de Registros:** {len(df_final)}")

    tamanho_pagina = 50; total_paginas = math.ceil(len(df_final) / tamanho_pagina)
    if total_paginas > 1:
        col_pag, _ = st.columns([1, 4]); pagina_atual = col_pag.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1)
    else: pagina_atual = 1

    inicio = (pagina_atual - 1) * tamanho_pagina; fim = inicio + tamanho_pagina
    df_paginado = df_final.iloc[inicio:fim].copy()

    df_paginado["Excluir"] = False
    
    # ATUALIZADO: Inclui novas colunas na visualização
    colunas_ordenadas = [
        "Data", "Mês", "Tipo", "Projeto", "Categoria", 
        "Valor", "Valor Consumido", "Diferença", "Status", 
        "Descrição", "Envolvidos", "Info Gerais", # Novas colunas visíveis
        "Parcela"
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
        disabled=["Data", "Mês", "Tipo", "Projeto", "Categoria", "Valor", "Descrição", "Parcela", "Envolvidos", "Info Gerais"],
        hide_index=True,
        use_container_width=True,
        key=f"editor_dados_pag_{pagina_atual}"
    )

    linhas_para_excluir = df_edited[df_edited["Excluir"] == True]
    if not linhas_para_excluir.empty:
        st.error(f"⚠️ {len(linhas_para_excluir)} registro(s) marcado(s).")
        if st.button("🗑️ CONFIRMAR EXCLUSÃO", type="primary"):
            indices_selecionados = linhas_para_excluir.index
            if "_row_id" in df_view.columns:
                indices_reais = df_paginado.loc[indices_selecionados, "_row_id"].tolist()
                if excluir_linhas_google(indices_reais): st.success("Registros excluídos!"); st.rerun()

def tela_cadastros(df_cad):
    st.subheader("⚙️ Gerenciar Cadastros")
    c1, c2 = st.columns(2)
    with c1:
        st.write("### 🏢 Projetos")
        novo_proj = st.text_input("Novo Projeto", key="in_proj")
        if st.button("Adicionar Projeto"):
            if novo_proj:
                if salvar_cadastro_novo("Projeto", novo_proj): st.success("Salvo!"); st.rerun()
        if not df_cad.empty: st.dataframe(df_cad[df_cad['Tipo'] == 'Projeto'][['Nome']], use_container_width=True, hide_index=True)
    with c2:
        st.write("### 🏷️ Categorias")
        nova_cat = st.text_input("Nova Categoria", key="in_cat")
        if st.button("Adicionar Categoria"):
            if nova_cat:
                if salvar_cadastro_novo("Categoria", nova_cat): st.success("Salvo!"); st.rerun()
        if not df_cad.empty: st.dataframe(df_cad[df_cad['Tipo'] == 'Categoria'][['Nome']], use_container_width=True, hide_index=True)

# --- 7. MENU PRINCIPAL ---
def main():
    df_lancamentos, df_cadastros = carregar_dados()
    with st.sidebar:
        st.title("💰 Controle Orçamentário")
        menu = ["📊 Painel", "➕ Novo", "📂 Dados", "⚙️ Cadastros"]
        escolha = st.radio("Navegação", menu)
        st.markdown("---")
        if st.button("🔄 Atualizar Dados"): st.cache_data.clear(); st.rerun()

    if escolha == "📊 Painel": tela_resumo(df_lancamentos)
    elif escolha == "➕ Novo": tela_novo(df_lancamentos, df_cadastros)
    elif escolha == "📂 Dados": tela_dados(df_lancamentos)
    elif escolha == "⚙️ Cadastros": tela_cadastros(df_cadastros)

if __name__ == "__main__":
    main()



