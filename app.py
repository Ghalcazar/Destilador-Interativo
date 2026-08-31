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

correntes_saida = ["Topo/Destilado"]
if num_correntes > 3:
    for i in range(1, num_correntes - 2):
        correntes_saida.append(f"Saída Intermediária {i}")
correntes_saida.append("Fundo")

correntes_todas = ["Entrada"] + correntes_saida
num_total_correntes = len(correntes_todas)

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
altura_por_corrente = 130 + (num_componentes * 75)
altura_total_svg = max(300, len(correntes_saida) * altura_por_corrente)

with col_esq:
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

with col_centro:
    altura_cilindro = altura_total_svg - 20
    num_pratos = len(correntes_saida) * 3 
    linhas_pratos = "".join([f"<line x1='15' y1='{10 + (i * (altura_cilindro / (num_pratos + 1))):.1f}' x2='55' y2='{10 + (i * (altura_cilindro / (num_pratos + 1))):.1f}' stroke='#2c3e50' stroke-width='2' stroke-dasharray='4 2'/>" for i in range(1, num_pratos + 1)])
    
    svg_coluna = (
        f"<div style='display: flex; justify-content: center; margin-top: 50px; margin-bottom: 10px;'>"
        f"<svg width='70' height='{altura_total_svg}' viewBox='0 0 70 {altura_total_svg}' xmlns='http://www.w3.org/2000/svg'>"
        f"<rect x='15' y='10' width='40' height='{altura_cilindro}' rx='8' ry='8' fill='#add8e6' stroke='#2c3e50' stroke-width='3'/>"
        f"{linhas_pratos}</svg></div>"
    )
    st.markdown(svg_coluna, unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-weight: 600; color: #cbd5e1;'>Coluna de<br>Destilação</p>", unsafe_allow_html=True)

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
                    dados_entrada[f"{corr}_{comp}_Perc"] = st.number_input(f"% de {comp} (decimal)", key=f"p_{corr}_{comp}", value=None, format="%.4f")

# ==========================================
# 3. NÚCLEO MATEMÁTICO (ÁLGEBRA LINEAR)
# ==========================================
st.markdown("---")
if st.button("🔢 Calcular Balanço de Massa", type="primary", use_container_width=True):
    
    # --- FASE 1: Validação Rigorosa de Entradas ---
    erros = []
    for corr in correntes_todas:
        p_vals = [dados_entrada.get(f"{corr}_{comp}_Perc") for comp in nomes_comp]
        p_vals_clean = [p for p in p_vals if p is not None]
        
        for i, comp in enumerate(nomes_comp):
            val = dados_entrada.get(f"{corr}_{comp}_Perc")
            if val is not None and val > 1.0:
                dados_entrada[f"{corr}_{comp}_Perc"] = val / 100.0
                p_vals_clean[i] = val / 100.0

        soma_p = sum(p_vals_clean)
        if soma_p > 1.0001:
            erros.append(f"**{corr}**: A soma das frações excede 100% ({soma_p*100:.2f}%).")
        elif len(p_vals_clean) == num_componentes and soma_p < 0.9999:
            erros.append(f"**{corr}**: Todas as frações informadas não somam 100% (Somam {soma_p*100:.2f}%).")

    if erros:
        st.error("⚠️ Inconsistências físicas encontradas nas entradas:")
        for erro in erros: st.warning(erro)
        st.stop()

    # --- FASE 2: Modelagem do Sistema e Rastreabilidade ---
    num_vars = num_total_correntes * num_componentes
    nomes_variaveis = [f"Massa de {comp} em {corr}" for corr in correntes_todas for comp in nomes_comp]
    
    A_list = []
    B_list = []
    descricoes_equacoes = [] # Guarda o significado físico de cada equação

    # 1. Equações de Balanço Global por Componente
    for c, comp in enumerate(nomes_comp):
        eq = np.zeros(num_vars)
        eq[0 * num_componentes + c] = 1.0 
        for s in range(1, num_total_correntes):
            eq[s * num_componentes + c] = -1.0 
        A_list.append(eq)
        B_list.append(0.0)
        descricoes_equacoes.append(f"Conservação do componente '{comp}' (Entrada = Todas as Saídas)")

    # 2. Equações baseadas nos inputs do usuário
    for s, corr in enumerate(correntes_todas):
        v_tot = dados_entrada.get(f"{corr}_VazaoTotal")
        if v_tot is not None:
            eq = np.zeros(num_vars)
            for c in range(num_componentes):
                eq[s * num_componentes + c] = 1.0
            A_list.append(eq)
            B_list.append(v_tot)
            descricoes_equacoes.append(f"Soma das massas parciais em '{corr}' fixada em {v_tot} kg/h")

        for c, comp in enumerate(nomes_comp):
            v_comp = dados_entrada.get(f"{corr}_{comp}_Vazao")
            if v_comp is not None:
                eq = np.zeros(num_vars)
                eq[s * num_componentes + c] = 1.0
                A_list.append(eq)
                B_list.append(v_comp)
                descricoes_equacoes.append(f"Vazão específica de '{comp}' em '{corr}' fixada em {v_comp} kg/h")

            p_comp = dados_entrada.get(f"{corr}_{comp}_Perc")
            if p_comp is not None:
                eq = np.zeros(num_vars)
                for k in range(num_componentes):
                    if k == c:
                        eq[s * num_componentes + k] = 1.0 - p_comp
                    else:
                        eq[s * num_componentes + k] = -p_comp
                A_list.append(eq)
                B_list.append(0.0)
                descricoes_equacoes.append(f"Proporção de '{comp}' em '{corr}' amarrada em {p_comp*100:.2f}% do total da corrente")

    A_mat = np.array(A_list)
    B_vec = np.array(B_list)

    # --- FASE 3: Análise de Erros Específicos e Resolução ---
    posto_A = np.linalg.matrix_rank(A_mat)
    
    # ERRO ESPECÍFICO 1: Faltam Dados
    if posto_A < num_vars:
        faltam = num_vars - posto_A
        st.warning(f"⚠️ **Faltam dados! O sistema está sub-especificado.**\n\n"
                   f"O simulador precisa descobrir **{num_vars} variáveis** (massas individuais), mas os dados que você preencheu só permitiram criar **{posto_A} equações matemáticas independentes**.\n\n"
                   f"**💡 Dica de Resolução:** Você precisa fornecer mais **{faltam}** informação(ões). Tente informar a Vazão Total de uma corrente ou a Fração (%) de um componente no Topo/Fundo.")
        st.stop()

    X, residuals, rank, singular = np.linalg.lstsq(A_mat, B_vec, rcond=None)
    
    # ERRO ESPECÍFICO 2: Dados Contraditórios (Resíduo Alto)
    erros_eq = np.abs(np.dot(A_mat, X) - B_vec)
    max_erro_idx = np.argmax(erros_eq)
    
    if erros_eq[max_erro_idx] > 1e-4:
        eq_falha = descricoes_equacoes[max_erro_idx]
        st.error(f"❌ **Dados Contraditórios.** As informações que você preencheu brigam entre si matematicamente.\n\n"
                 f"**📍 Onde a matemática quebrou:** `{eq_falha}`\n\n"
                 f"O sistema tentou calcular, mas foi impossível fechar essa equação com os dados exatos fornecidos nas outras correntes. Verifique se você não digitou um valor conflitante.")
        st.stop()

    # ERRO ESPECÍFICO 3: Massa Negativa
    if np.any(X < -1e-4):
        indices_negativos = np.where(X < -1e-4)[0]
        vars_negativas = [nomes_variaveis[i] for i in indices_negativos]
        st.error(f"❌ **Erro Físico (Massas Negativas):** O cálculo matemático foi forçado a 'sugar' massa para tentar equilibrar a coluna.\n\n"
                 f"**📍 O problema ocorreu em:** `{', '.join(vars_negativas)}`\n\n"
                 f"Isso geralmente acontece quando você exige que saia no Topo/Fundo uma quantidade de matéria MAIOR do que a que realmente entrou na coluna. Revise os fluxos.")
        st.stop()

    # --- FASE 4: Reconstrução e Passo a Passo (Módulo Educacional) ---
    tabela_final = pd.DataFrame(index=correntes_todas, columns=hierarquia_colunas)
    
    for s, corr in enumerate(correntes_todas):
        massas_corrente = X[s * num_componentes : (s+1) * num_componentes]
        vazao_total = np.sum(massas_corrente)
        tabela_final.loc[corr, ("Geral", "Vazão Total")] = vazao_total
        
        for c, comp in enumerate(nomes_comp):
            massa_comp = massas_corrente[c]
            fracao_comp = massa_comp / vazao_total if vazao_total > 1e-8 else 0.0
            
            tabela_final.loc[corr, (comp, "Vazão")] = massa_comp
            tabela_final.loc[corr, (comp, "%")] = fracao_comp

    st.success("✅ Sistema resolvido com sucesso via Álgebra Linear!")

    # Expandir com o racional matemático
    st.subheader("🧠 Passo a Passo da Modelagem Matemática")
    with st.expander("Ver Lógica de Resolução e Equações do Sistema", expanded=False):
        st.markdown("Ao invés de procurar as respostas tentando adivinhar uma lacuna por vez, problemas de engenharia são resolvidos montando um **Sistema de Equações Simultâneas** formulado como uma matriz genérica $A \cdot x = B$. Veja como o simulador 'pensou':")
        
        st.markdown(f"**1º Passo: Mapear as {num_vars} Incógnitas (Vetor $x$)**")
        st.markdown("O simulador ignorou as frações temporariamente e buscou descobrir apenas as **massas absolutas** de cada componente em cada lugar:")
        for var in nomes_variaveis:
            st.markdown(f"- $x_{{{nomes_variaveis.index(var)}}}$ = {var}")
            
        st.markdown("<br>**2º Passo: Formular as Equações baseadas nos seus Inputs**", unsafe_allow_html=True)
        st.markdown("O algoritmo leu o que você digitou e transformou em equações lineares:")
        for i, (desc, val) in enumerate(zip(descricoes_equacoes, B_list)):
            st.markdown(f"- **Eq {i+1}:** {desc} $\\rightarrow$ Resulta em **{val:.2f}**")
            
        st.markdown("<br>**3º Passo: Resolução via Matrizes**", unsafe_allow_html=True)
        st.markdown("O simulador resolveu a matriz encontrando o valor de cada incógnita $x$ que satisfizesse todas as equações acima ao mesmo tempo. Com as massas absolutas descobertas, as frações percentuais e totais foram calculadas por mera divisão/soma matemática para preencher a tabela abaixo.")

    # Exibição dos resultados
    st.subheader("📋 Tabela Final de Resultados")
    st.dataframe(tabela_final.style.format("{:.4f}"), use_container_width=True)

    # ==========================================
    # 5. GERADOR DO DIAGRAMA (GRAPHVIZ)
    # ==========================================
    st.markdown("---")
    st.subheader("🗼 Esboço Final da Coluna com Composições")
    
    diagrama = graphviz.Digraph(engine="dot")
    diagrama.attr(rankdir='LR', splines='ortho', nodesep='1.0')
    diagrama.node('Coluna', 'Torre de\nDestilação', shape='cylinder', style='filled', fillcolor='#add8e6', width='1.5', height='1.5')
    
    def montar_label_corrente(nome_corrente):
        v_tot = tabela_final.loc[nome_corrente, ("Geral", "Vazão Total")]
        texto = f"{nome_corrente}\nTotal: {v_tot:.2f} kg/h\n"
        
        for comp in nomes_comp:
            v_c = tabela_final.loc[nome_corrente, (comp, "Vazão")]
            p_c = tabela_final.loc[nome_corrente, (comp, "%")]
            texto += f"- {comp}: {v_c:.2f} kg/h ({p_c * 100:.2f}%)\n"
            
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
