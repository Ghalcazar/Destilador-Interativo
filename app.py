import streamlit as st
import pandas as pd
import numpy as np
import graphviz

# Configuração da página
st.set_page_config(page_title="Balanço de Massa - Destilação", layout="wide")

st.title("⚗️ Simulador de Balanço de Massa")
st.markdown("---")

# ==========================================
# 1. CONFIGURAÇÃO INICIAL (Sidebar)
# ==========================================
with st.sidebar:
    st.header("Configurações")
    num_correntes = st.number_input("Quantidade de Correntes", min_value=3, value=3, step=1)
    num_componentes = st.number_input("Quantidade de Componentes", min_value=1, value=2, step=1)
    
    nomes_comp = []
    for i in range(num_componentes):
        nome = st.text_input(f"Nome do Componente {i+1}", value=f"Comp {i+1}")
        nomes_comp.append(nome)

# Nomenclatura das Correntes
correntes_saida = ["Topo/Destilado"]
if num_correntes > 3:
    # Subtrai 2 para descontar a Entrada, o Topo e o Fundo
    for i in range(1, num_correntes - 2):
        correntes_saida.append(f"Saída Intermediária {i}")
correntes_saida.append("Fundo")

correntes_todas = ["Entrada"] + correntes_saida

# Estrutura de Colunas (MultiIndex)
colunas_multi = [("Geral", "Vazão Total")]
for comp in nomes_comp:
    colunas_multi.append((comp, "Vazão"))
    colunas_multi.append((comp, "%"))

hierarquia_colunas = pd.MultiIndex.from_tuples(colunas_multi)

# ==========================================
# 2. INTERFACE DE PREENCHIMENTO (Colunas)
# ==========================================
st.subheader("Preenchimento de Dados")
col_esq, col_centro, col_dir = st.columns([1, 0.5, 1])

dados_entrada = {}

# --- ALTURA DINÂMICA CALIBRADA ---
# Base do expander (~130px) + cada componente adiciona uma linha (~75px)
altura_por_corrente = 130 + (num_componentes * 75)
altura_total_svg = max(300, len(correntes_saida) * altura_por_corrente)

# --- LADO ESQUERDO: ENTRADA (Centralizado Verticalmente) ---
with col_esq:
    # Centraliza o bloco de entrada de acordo com a altura gerada para o SVG
    espaco_topo = max(0, int((altura_total_svg - (130 + (num_componentes * 75))) / 2))
    if espaco_topo > 0:
        st.markdown(f"<div style='height: {espaco_topo}px;'></div>", unsafe_allow_html=True)
        
    st.markdown("### ➡️ Corrente de Entrada")
    with st.container(border=True):
        dados_entrada["Entrada_VazaoTotal"] = st.number_input("Vazão Total (Entrada)", value=None, format="%.2f")
        for comp in nomes_comp:
            c1, c2 = st.columns(2)
            with c1:
                dados_entrada[f"Entrada_{comp}_Vazao"] = st.number_input(f"Vazão de {comp}", key=f"v_ent_{comp}", value=None, format="%.2f")
            with c2:
                dados_entrada[f"Entrada_{comp}_Perc"] = st.number_input(f"% de {comp} (decimal)", key=f"p_ent_{comp}", value=None, format="%.4f", help="Use 0.5 para 50%")

# --- CENTRO: DESENHO DA COLUNA (SVG Dinâmico) ---
with col_centro:
    altura_cilindro = altura_total_svg - 20
    num_pratos = len(correntes_saida) * 3 
    linhas_pratos = ""
    espacamento = altura_cilindro / (num_pratos + 1)
    
    # Gera os pratos
    for i in range(1, num_pratos + 1):
        y_pos = 10 + (i * espacamento)
        linhas_pratos += f"<line x1='15' y1='{y_pos:.1f}' x2='55' y2='{y_pos:.1f}' stroke='#2c3e50' stroke-width='2' stroke-dasharray='4 2'/>"

    # SVG string limpa
    svg_coluna = (
        f"<div style='display: flex; justify-content: center; margin-top: 50px; margin-bottom: 10px;'>"
        f"<svg width='70' height='{altura_total_svg}' viewBox='0 0 70 {altura_total_svg}' xmlns='http://www.w3.org/2000/svg'>"
        f"<rect x='15' y='10' width='40' height='{altura_cilindro}' rx='8' ry='8' fill='#add8e6' stroke='#2c3e50' stroke-width='3'/>"
        f"{linhas_pratos}"
        f"</svg></div>"
    )
    
    st.markdown(svg_coluna, unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-weight: 600; color: #cbd5e1;'>Coluna de<br>Destilação</p>", unsafe_allow_html=True)

# --- LADO DIREITO: SAÍDAS ---
with col_dir:
    st.markdown("### ➡️ Correntes de Saída")
    for corr in correntes_saida:
        with st.expander(f"⚙️ {corr}", expanded=True):
            dados_entrada[f"{corr}_VazaoTotal"] = st.number_input(f"Vazão Total ({corr})", key=f"vt_{corr}", value=None, format="%.2f")
            for comp in nomes_comp:
                c1, c2 = st.columns(2)
                with c1:
                    dados_entrada[f"{corr}_{comp}_Vazao"] = st.number_input(f"Vazão de {comp}", key=f"v_{corr}_{comp}", value=None, format="%.2f")
                with c2:
                    dados_entrada[f"{corr}_{comp}_Perc"] = st.number_input(f"% de {comp} (decimal)", key=f"p_{corr}_{comp}", value=None, format="%.4f", help="Use 0.5 para 50%")

# ==========================================
# 3. CÁLCULO E RESULTADOS (O CÉREBRO)
# ==========================================
st.markdown("---")
if st.button("🔢 Calcular Balanço de Massa", type="primary", use_container_width=True):
    
    # ---------------------------------------------------------
    # FASE 0: CONSTRUÇÃO DA TABELA INICIAL
    # ---------------------------------------------------------
    tabela = pd.DataFrame(np.nan, index=correntes_todas, columns=hierarquia_colunas)
    
    for corr in correntes_todas:
        v_tot = dados_entrada.get(f"{corr}_VazaoTotal")
        tabela.loc[corr, ("Geral", "Vazão Total")] = v_tot if v_tot is not None else np.nan
        
        for comp in nomes_comp:
            v_comp = dados_entrada.get(f"{corr}_{comp}_Vazao")
            p_comp = dados_entrada.get(f"{corr}_{comp}_Perc")
            
            if p_comp is not None and p_comp > 1.0:
                p_comp = p_comp / 100.0
                
            tabela.loc[corr, (comp, "Vazão")] = v_comp if v_comp is not None else np.nan
            tabela.loc[corr, (comp, "%")] = p_comp if p_comp is not None else np.nan

    tabela_inicial = tabela.copy()

    # ---------------------------------------------------------
    # FASE 1: VALIDAÇÃO DOS DADOS
    # ---------------------------------------------------------
    erros_encontrados = []
    
    for corr in correntes_todas:
        v_total = tabela.loc[corr, ("Geral", "Vazão Total")]
        soma_vazoes_comp = tabela.loc[corr, pd.IndexSlice[:, "Vazão"]].sum()
        soma_porcentagens = tabela.loc[corr, pd.IndexSlice[:, "%"]].sum()

        for comp in nomes_comp:
            v_val = tabela.loc[corr, (comp, "Vazão")]
            p_val = tabela.loc[corr, (comp, "%")]
            
            if pd.notna(v_total) and pd.notna(v_val) and pd.notna(p_val):
                if not np.isclose(v_total * p_val, v_val, atol=1e-4):
                    erros_encontrados.append(f"**Inconsistência matemática em {corr} ({comp})**: {v_total} * {p_val} != {v_val}")
                    
        if pd.notna(v_total) and soma_vazoes_comp > (v_total + 1e-5):
            erros_encontrados.append(f"**Na corrente '{corr}'**, a soma das vazões dos componentes excede o total!")
        if soma_porcentagens > 1.0001:
            erros_encontrados.append(f"**Na corrente '{corr}'**, a soma das porcentagens ultrapassa 100% (1.0)!")

    v_entrada = tabela.loc["Entrada", ("Geral", "Vazão Total")]
    v_saidas_lista = tabela.loc[correntes_saida, ("Geral", "Vazão Total")]
    soma_saidas = v_saidas_lista.sum()

    if pd.notna(v_entrada) and soma_saidas > (v_entrada + 1e-5):
        erros_encontrados.append(f"**[ERRO GLOBAL]** A soma das saídas totais ({soma_saidas}) excede a entrada ({v_entrada})!")

    for comp in nomes_comp:
        v_comp_entrada = tabela.loc["Entrada", (comp, "Vazão")]
        soma_saidas_comp = tabela.loc[correntes_saida, (comp, "Vazão")].sum()
        if pd.notna(v_comp_entrada) and soma_saidas_comp > (v_comp_entrada + 1e-5):
            erros_encontrados.append(f"**[ERRO DE COMPONENTE]** A soma das saídas de {comp} excede a entrada informada!")

    if erros_encontrados:
        st.error("⚠️ Encontramos problemas nos dados preenchidos. Por favor, corrija antes de calcular:")
        for erro in erros_encontrados:
            st.warning(erro)
        st.stop()

    # ---------------------------------------------------------
    # FASE 2: RESOLUÇÃO ITERATIVA
    # ---------------------------------------------------------
    st.success("Dados validados com sucesso! Iniciando cálculos...")
    
    iteracao = 1
    historico_logs = {}
    sucesso_total = False
    
    while True:
        nans_antes = tabela.isna().sum().sum()
        if nans_antes == 0:
            sucesso_total = True
            break
            
        logs_desta_iteracao = []

        # 1A: Descobrir total pela linha
        for corr in correntes_todas:
            if pd.isna(tabela.loc[corr, ("Geral", "Vazão Total")]):
                for comp in nomes_comp:
                    v_c = tabela.loc[corr, (comp, "Vazão")]
                    p_c = tabela.loc[corr, (comp, "%")]
                    if pd.notna(v_c) and pd.notna(p_c) and p_c != 0:
                        calculado = round(v_c / p_c, 5)
                        tabela.loc[corr, ("Geral", "Vazão Total")] = calculado
                        logs_desta_iteracao.append(f"🔹 Vazão Total de **'{corr}'** calculada via {comp}: {v_c} / {p_c} = **{calculado}**")
                        break

        # 1B: Descobrir total pelo balanço global
        v_tot_entrada = tabela.loc["Entrada", ("Geral", "Vazão Total")]
        v_totais_saidas = tabela.loc[correntes_saida, ("Geral", "Vazão Total")]

        if pd.isna(v_tot_entrada) and v_totais_saidas.notna().all():
            soma = round(v_totais_saidas.sum(), 5)
            tabela.loc["Entrada", ("Geral", "Vazão Total")] = soma
            logs_desta_iteracao.append(f"🔹 Vazão Total de **Entrada** calculada pela soma das saídas: Total = **{soma}**")
            
        elif v_totais_saidas.isna().sum() == 1 and pd.notna(v_tot_entrada):
            saida_faltante = v_totais_saidas[v_totais_saidas.isna()].index[0]
            soma_saidas_conhecidas = v_totais_saidas.sum()
            calculado = round(v_tot_entrada - soma_saidas_conhecidas, 5)
            tabela.loc[saida_faltante, ("Geral", "Vazão Total")] = calculado
            logs_desta_iteracao.append(f"🔹 Vazão Total de **'{saida_faltante}'** calculada por balanço global: {v_tot_entrada} - {soma_saidas_conhecidas} = **{calculado}**")

        # 2: RESOLUÇÃO DENTRO DA CORRENTE
        for corr in correntes_todas:
            v_total = tabela.loc[corr, ("Geral", "Vazão Total")]
            
            # 2A. Fechamento de %
            faltantes_perc = [c for c in nomes_comp if pd.isna(tabela.loc[corr, (c, "%")])]
            if len(faltantes_perc) == 1:
                comp_falt = faltantes_perc[0]
                soma_perc = sum([tabela.loc[corr, (c, "%")] for c in nomes_comp if pd.notna(tabela.loc[corr, (c, "%")])])
                calculado = round(1.0 - soma_perc, 5)
                tabela.loc[corr, (comp_falt, "%")] = calculado
                logs_desta_iteracao.append(f"🔸 % de **{comp_falt}** em '{corr}' fechada por diferença: 1.0 - {soma_perc} = **{calculado}**")

            # 2B. Cálculo cruzado (Vazão = Total * %)
            for comp in nomes_comp:
                v_comp = tabela.loc[corr, (comp, "Vazão")]
                p_comp = tabela.loc[corr, (comp, "%")]

                if pd.notna(v_total):
                    if pd.isna(v_comp) and pd.notna(p_comp):
                        calculado = round(v_total * p_comp, 5)
                        tabela.loc[corr, (comp, "Vazão")] = calculado
                        logs_desta_iteracao.append(f"🔸 Vazão de **{comp}** em '{corr}' calculada (Total * %): {v_total} * {p_comp} = **{calculado}**")
                    elif pd.isna(p_comp) and pd.notna(v_comp):
                        calculado = round(v_comp / v_total, 5)
                        tabela.loc[corr, (comp, "%")] = calculado
                        logs_desta_iteracao.append(f"🔸 % de **{comp}** em '{corr}' calculada (Vazão / Total): {v_comp} / {v_total} = **{calculado}**")

            # 2C. Fechamento de Vazão na Linha
            if pd.notna(v_total):
                faltantes_vazao = [c for c in nomes_comp if pd.isna(tabela.loc[corr, (c, "Vazão")])]
                if len(faltantes_vazao) == 1:
                    comp_falt = faltantes_vazao[0]
                    soma_vazoes = sum([tabela.loc[corr, (c, "Vazão")] for c in nomes_comp if pd.notna(tabela.loc[corr, (c, "Vazão")])])
                    calculado = round(v_total - soma_vazoes, 5)
                    tabela.loc[corr, (comp_falt, "Vazão")] = calculado
                    logs_desta_iteracao.append(f"🔸 Vazão de **{comp_falt}** em '{corr}' calculada por diferença de massa: {v_total} - {soma_vazoes} = **{calculado}**")
                    
                    if pd.isna(tabela.loc[corr, (comp_falt, "%")]):
                        perc_calc = round(calculado / v_total, 5)
                        tabela.loc[corr, (comp_falt, "%")] = perc_calc
                        logs_desta_iteracao.append(f"🔸 % de **{comp_falt}** em '{corr}' atualizada: {calculado} / {v_total} = **{perc_calc}**")

        # 3: BALANÇO POR COMPONENTE
        for comp in nomes_comp:
            v_comp_entrada = tabela.loc["Entrada", (comp, "Vazão")]
            v_comp_saidas = tabela.loc[correntes_saida, (comp, "Vazão")]
            
            if pd.isna(v_comp_entrada) and v_comp_saidas.notna().all():
                soma = round(v_comp_saidas.sum(), 5)
                tabela.loc["Entrada", (comp, "Vazão")] = soma
                logs_desta_iteracao.append(f"🟢 Entrada de **{comp}** calculada pela soma das saídas: **{soma}**")
                
            elif pd.notna(v_comp_entrada) and v_comp_saidas.isna().sum() == 1:
                saida_falt_comp = v_comp_saidas[v_comp_saidas.isna()].index[0]
                soma_conhecidas = v_comp_saidas.sum()
                calculado = round(v_comp_entrada - soma_conhecidas, 5)
                tabela.loc[saida_falt_comp, (comp, "Vazão")] = calculado
                logs_desta_iteracao.append(f"🟢 Saída de **{comp}** em '{saida_falt_comp}' calculada pelo balanço do componente: {v_comp_entrada} - {soma_conhecidas} = **{calculado}**")

        # Verifica Parada
        nans_depois = tabela.isna().sum().sum()
        if nans_antes == nans_depois:
            break
            
        historico_logs[f"Iteração {iteracao}"] = logs_desta_iteracao
        iteracao += 1

    # ==========================================
    # 4. EXIBIÇÃO DOS RESULTADOS NA TELA
    # ==========================================
    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.subheader("📋 Tabela Inicial (Inputs)")
        st.dataframe(tabela_inicial.style.format(na_rep="-", precision=4), use_container_width=True)
        
    with col_res2:
        st.subheader("✅ Tabela Final Resolvida")
        st.dataframe(tabela.style.format(na_rep="?", precision=4), use_container_width=True)

    # Exibe os Logs Passo a Passo
    st.subheader("🧠 Passo a Passo dos Cálculos")
    if historico_logs:
        for iter_name, mensagens in historico_logs.items():
            with st.expander(iter_name, expanded=(iter_name == "Iteração 1")):
                for msg in mensagens:
                    st.markdown(msg)
    else:
        st.info("Nenhum cálculo foi necessário (ou faltam dados).")

    if sucesso_total:
        st.success(f"✅ Balanço de Massa 100% resolvido na iteração {iteracao-1}!")
    else:
        st.warning(f"⚠️ O algoritmo parou na iteração {iteracao}. Faltam graus de liberdade (dados insuficientes) para resolver o restante da tabela.")

    # ==========================================
    # 5. GERADOR DO DIAGRAMA (GRAPHVIZ)
    # ==========================================
    st.markdown("---")
    st.subheader("🗼 Esboço Final da Coluna com Composições")
    
    diagrama = graphviz.Digraph(engine="dot")
    diagrama.attr(rankdir='LR', splines='ortho', nodesep='1.0')
    
    diagrama.node('Coluna', 'Torre de\nDestilação', shape='cylinder', style='filled', fillcolor='#add8e6', width='1.5', height='1.5')
    
    def montar_label_corrente(nome_corrente):
        v_tot = tabela.loc[nome_corrente, ("Geral", "Vazão Total")]
        texto = f"{nome_corrente}\nTotal: {v_tot} kg/h\n" if pd.notna(v_tot) else f"{nome_corrente}\nTotal: ? kg/h\n"
        
        for comp in nomes_comp:
            v_c = tabela.loc[nome_corrente, (comp, "Vazão")]
            p_c = tabela.loc[nome_corrente, (comp, "%")]
            
            str_v = f"{v_c} kg/h" if pd.notna(v_c) else "? kg/h"
            str_p = f"{p_c * 100:.2f}%" if pd.notna(p_c) else "? %"
            
            texto += f"- {comp}: {str_v} ({str_p})\n"
            
        return texto

    lbl_ent = montar_label_corrente("Entrada")
    diagrama.node('Entrada_Node', 'Entrada', shape='ellipse')
    diagrama.edge('Entrada_Node', 'Coluna', label=lbl_ent)
    
    for corr in correntes_saida:
        lbl_sai = montar_label_corrente(corr)
        node_id = f"Node_{corr}"
        
        diagrama.node(node_id, corr, shape='ellipse')
        diagrama.edge('Coluna', node_id, label=lbl_sai)
        
    st.graphviz_chart(diagrama, use_container_width=True)