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

colunas_multi = [("Geral", "Vazão Total")]
for comp in nomes_comp:
    colunas_multi.append((comp, "Vazão"))
    colunas_multi.append((comp, "%"))
hierarquia_colunas = pd.MultiIndex.from_tuples(colunas_multi)

# ==========================================
# 2. INTERFACE DE PREENCHIMENTO
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
                dados_entrada[f"Entrada_{comp}_Perc"] = st.number_input(f"% de {comp} (decimal)", key=f"p_ent_{comp}", value=None, format="%.4f")

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
# 3. NÚCLEO DE CÁLCULO HÍBRIDO
# ==========================================
st.markdown("---")
if st.button("🔢 Calcular Balanço de Massa", type="primary", width="stretch"):
    
    # --- FASE 1: VALIDAÇÃO FÍSICA BÁSICA ---
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
        if soma_p > 1.0001: erros.append(f"**{corr}**: Frações excedem 100% ({soma_p*100:.2f}%).")
        elif len(p_vals_clean) == num_componentes and soma_p < 0.9999: erros.append(f"**{corr}**: Frações não somam 100%.")

    if erros:
        st.error("⚠️ Inconsistências físicas encontradas nas entradas:")
        for erro in erros: st.warning(erro)
        st.stop()

    # --- FASE 2: TENTATIVA ITERATIVA (O CÉREBRO HUMANO) ---
    tabela_iter = pd.DataFrame(np.nan, index=correntes_todas, columns=hierarquia_colunas)
    for corr in correntes_todas:
        tabela_iter.loc[corr, ("Geral", "Vazão Total")] = dados_entrada.get(f"{corr}_VazaoTotal")
        for comp in nomes_comp:
            tabela_iter.loc[corr, (comp, "Vazão")] = dados_entrada.get(f"{corr}_{comp}_Vazao")
            tabela_iter.loc[corr, (comp, "%")] = dados_entrada.get(f"{corr}_{comp}_Perc")

    logs_iterativos = []
    sucesso_iterativo = False
    
    while True:
        nans_antes = tabela_iter.isna().sum().sum()
        if nans_antes == 0:
            sucesso_iterativo = True
            break
            
        for corr in correntes_todas:
            if pd.isna(tabela_iter.loc[corr, ("Geral", "Vazão Total")]):
                for comp in nomes_comp:
                    v_c = tabela_iter.loc[corr, (comp, "Vazão")]
                    p_c = tabela_iter.loc[corr, (comp, "%")]
                    if pd.notna(v_c) and pd.notna(p_c) and p_c != 0:
                        tabela_iter.loc[corr, ("Geral", "Vazão Total")] = v_c / p_c
                        logs_iterativos.append(f"🔹 **Vazão Total ({corr}):** Calculada via regra de 3 ({v_c:.2f} / {p_c:.2f}) = {(v_c/p_c):.2f}")
                        break

        v_tot_entrada = tabela_iter.loc["Entrada", ("Geral", "Vazão Total")]
        v_totais_saidas = tabela_iter.loc[correntes_saida, ("Geral", "Vazão Total")]
        if pd.isna(v_tot_entrada) and v_totais_saidas.notna().all():
            tabela_iter.loc["Entrada", ("Geral", "Vazão Total")] = v_totais_saidas.sum()
            logs_iterativos.append(f"🔹 **Entrada Total:** Somatório das saídas conhecidas = {v_totais_saidas.sum():.2f}")
        elif v_totais_saidas.isna().sum() == 1 and pd.notna(v_tot_entrada):
            saida_faltante = v_totais_saidas[v_totais_saidas.isna()].index[0]
            soma_conhecidas = v_totais_saidas.sum()
            tabela_iter.loc[saida_faltante, ("Geral", "Vazão Total")] = v_tot_entrada - soma_conhecidas
            logs_iterativos.append(f"🔹 **Total em {saida_faltante}:** Calculado por diferença (Entrada - Outras Saídas) = {(v_tot_entrada - soma_conhecidas):.2f}")

        for corr in correntes_todas:
            v_total = tabela_iter.loc[corr, ("Geral", "Vazão Total")]
            falt_perc = [c for c in nomes_comp if pd.isna(tabela_iter.loc[corr, (c, "%")])]
            if len(falt_perc) == 1:
                soma_p = sum([tabela_iter.loc[corr, (c, "%")] for c in nomes_comp if pd.notna(tabela_iter.loc[corr, (c, "%")])])
                tabela_iter.loc[corr, (falt_perc[0], "%")] = 1.0 - soma_p
                logs_iterativos.append(f"🔸 **% {falt_perc[0]} ({corr}):** Fechamento de 100% = {(1.0 - soma_p)*100:.2f}%")
            
            for comp in nomes_comp:
                v_c = tabela_iter.loc[corr, (comp, "Vazão")]
                p_c = tabela_iter.loc[corr, (comp, "%")]
                if pd.notna(v_total):
                    if pd.isna(v_c) and pd.notna(p_c):
                        tabela_iter.loc[corr, (comp, "Vazão")] = v_total * p_c
                        logs_iterativos.append(f"🔸 **Vazão {comp} ({corr}):** Total $\\times$ % ({v_total:.2f} $\\times$ {p_c:.2f}) = {(v_total * p_c):.2f}")
                    elif pd.isna(p_c) and pd.notna(v_c):
                        tabela_iter.loc[corr, (comp, "%")] = v_c / v_total
                        logs_iterativos.append(f"🔸 **% {comp} ({corr}):** Fração mássica ({v_c:.2f} / {v_total:.2f}) = {(v_c/v_total)*100:.2f}%")
            
            if pd.notna(v_total):
                falt_vaz = [c for c in nomes_comp if pd.isna(tabela_iter.loc[corr, (c, "Vazão")])]
                if len(falt_vaz) == 1:
                    soma_v = sum([tabela_iter.loc[corr, (c, "Vazão")] for c in nomes_comp if pd.notna(tabela_iter.loc[corr, (c, "Vazão")])])
                    tabela_iter.loc[corr, (falt_vaz[0], "Vazão")] = v_total - soma_v
                    logs_iterativos.append(f"🔸 **Vazão {falt_vaz[0]} ({corr}):** Diferença de vazão parcial = {(v_total - soma_v):.2f}")

        for comp in nomes_comp:
            v_ent = tabela_iter.loc["Entrada", (comp, "Vazão")]
            v_sais = tabela_iter.loc[correntes_saida, (comp, "Vazão")]
            if pd.isna(v_ent) and v_sais.notna().all():
                tabela_iter.loc["Entrada", (comp, "Vazão")] = v_sais.sum()
                logs_iterativos.append(f"🟢 **Entrada de {comp}:** Soma das saídas = {v_sais.sum():.2f}")
            elif pd.notna(v_ent) and v_sais.isna().sum() == 1:
                s_falt = v_sais[v_sais.isna()].index[0]
                tabela_iter.loc[s_falt, (comp, "Vazão")] = v_ent - v_sais.sum()
                logs_iterativos.append(f"🟢 **Saída de {comp} ({s_falt}):** Balanço parcial do componente = {(v_ent - v_sais.sum()):.2f}")

        nans_depois = tabela_iter.isna().sum().sum()
        if nans_antes == nans_depois:
            break

    # --- FASE 3: A MATRIZ DE SEGURANÇA (O CÉREBRO MÁQUINA) ---
    num_vars = num_total_correntes * num_componentes
    nomes_vars = [f"Vazão de {comp} em {corr}" for corr in correntes_todas for comp in nomes_comp]
    
    A_todas = []
    B_todas = []
    desc_todas = []

    for c, comp in enumerate(nomes_comp):
        eq = np.zeros(num_vars)
        eq[0 * num_componentes + c] = 1.0 
        for s in range(1, num_total_correntes):
            eq[s * num_componentes + c] = -1.0 
        A_todas.append(eq)
        B_todas.append(0.0)
        desc_todas.append(f"Conservação de '{comp}' (Entrada = Saídas)")

    for s, corr in enumerate(correntes_todas):
        v_tot = tabela_iter.loc[corr, ("Geral", "Vazão Total")]
        if pd.notna(v_tot):
            eq = np.zeros(num_vars)
            for c in range(num_componentes): eq[s * num_componentes + c] = 1.0
            A_todas.append(eq)
            B_todas.append(v_tot)
            desc_todas.append(f"Vazão Total em '{corr}' fixada em {v_tot:.2f}")

        for c, comp in enumerate(nomes_comp):
            v_comp = tabela_iter.loc[corr, (comp, "Vazão")]
            if pd.notna(v_comp):
                eq = np.zeros(num_vars)
                eq[s * num_componentes + c] = 1.0
                A_todas.append(eq)
                B_todas.append(v_comp)
                desc_todas.append(f"Vazão exata de '{comp}' em '{corr}' já calculada como {v_comp:.2f}")

            p_comp = tabela_iter.loc[corr, (comp, "%")]
            if pd.notna(p_comp):
                eq = np.zeros(num_vars)
                for k in range(num_componentes):
                    if k == c: eq[s * num_componentes + k] = 1.0 - p_comp
                    else: eq[s * num_componentes + k] = -p_comp
                A_todas.append(eq)
                B_todas.append(0.0)
                desc_todas.append(f"Proporção de '{comp}' em '{corr}' amarrada em {p_comp*100:.2f}%")

    posto_geral = np.linalg.matrix_rank(np.array(A_todas))
    if posto_geral < num_vars:
        faltam = num_vars - posto_geral
        st.warning(f"⚠️ **Faltam dados! O sistema está sub-especificado.** O simulador precisa de {num_vars} variáveis independentes, mas os dados só renderam {posto_geral} equações. Forneça mais {faltam} informação(ões).")
        st.stop()

    A_list = []
    B_list = []
    descricoes_equacoes = []
    
    for eq, b_val, desc in zip(A_todas, B_todas, desc_todas):
        temp_A = A_list + [eq]
        if np.linalg.matrix_rank(np.array(temp_A)) == len(temp_A):
            A_list.append(eq)
            B_list.append(b_val)
            descricoes_equacoes.append(desc)
        if len(A_list) == num_vars:
            break

    A_mat = np.array(A_list)
    B_vec = np.array(B_list)

    X = np.linalg.solve(A_mat, B_vec)
    
    erros_eq = np.abs(np.dot(np.array(A_todas), X) - np.array(B_todas))
    if np.max(erros_eq) > 1e-4:
        st.error("❌ **Dados Contraditórios.** As informações fornecidas violam a lei de conservação de massa. Revise os dados de entrada.")
        st.stop()

    if np.any(X < -1e-4):
        indices_negativos = np.where(X < -1e-4)[0]
        vars_negativas = [nomes_vars[i] for i in indices_negativos]
        st.error(f"❌ **Erro Físico (Vazões Negativas):** O cálculo matemático foi forçado a gerar um fluxo negativo para tentar equilibrar a coluna.\n\n📍 **O problema ocorreu em:** `{', '.join(vars_negativas)}`\n\nIsso geralmente acontece quando você exige que saia uma vazão MAIOR do que a que entrou. Revise os fluxos de operação.")
        st.stop()

    tabela_final = pd.DataFrame(index=correntes_todas, columns=hierarquia_colunas)
    for s, corr in enumerate(correntes_todas):
        vazoes_calc = X[s * num_componentes : (s+1) * num_componentes]
        v_tot = np.sum(vazoes_calc)
        tabela_final.loc[corr, ("Geral", "Vazão Total")] = v_tot
        for c, comp in enumerate(nomes_comp):
            tabela_final.loc[corr, (comp, "Vazão")] = vazoes_calc[c]
            tabela_final.loc[corr, (comp, "%")] = vazoes_calc[c] / v_tot if v_tot > 1e-8 else 0.0

    st.success("✅ Sistema solucionado com sucesso!")

    # ==========================================
    # 4. MÓDULO EDUCACIONAL HÍBRIDO
    # ==========================================
    st.subheader("🧠 Passo a Passo da Resolução")
    with st.expander("Ver Análise Didática: Linha a Linha vs. Matrizes", expanded=False):
        
        st.markdown("### 1ª Fase: O Método do Caderno (Passo a Passo Sequencial)")
        st.markdown("Primeiro, o simulador tentou resolver o problema isolando uma variável por vez, usando regras de 3 e subtrações simples (o que você faria no papel):")
        
        if logs_iterativos:
            for log in logs_iterativos: st.markdown(log)
        else:
            st.markdown("*Nenhuma dedução sequencial pôde ser iniciada com os dados crus.*")

        if sucesso_iterativo:
            st.success("🎉 **Sucesso Sequencial!** O problema tinha amarrações diretas o suficiente para ser resolvido inteiramente linha a linha.")
        else:
            st.error("🚨 **O Método do Caderno Travou!**")
            st.markdown("O algoritmo chegou em um ponto onde não havia mais nenhuma variável que pudesse ser isolada sozinha. Para destravar os cruzamentos simultâneos (ex: Topo e Fundo dependendo um do outro), precisamos da **Álgebra Linear**.")

            st.markdown("---")
            st.markdown("### 2ª Fase: A Transição para Álgebra Linear ($A \\cdot x = B$)")
            st.markdown("O simulador pegou tudo o que você preencheu + **o que ele já havia descoberto na 1ª Fase** e montou um sistema de equações focado apenas no que faltava descobrir.")
            
            st.info("""
            * **Vetor $x$ (As Incógnitas):** A lista com as vazões parciais que compõem o sistema.
            * **Vetor $B$ (Os Resultados):** Fica do lado direito da igualdade ($=$). São os valores conhecidos (ex: 50.00).
            * **Matriz $A$ (Os Coeficientes):** Fica do lado esquerdo. Mostra as proporções de cada equação. 
            
            **A Estratégia da Matriz Quadrada:** O software descartou equações redundantes e separou exatamente o número de equações necessárias para criar uma matriz quadrada perfeita, permitindo o cálculo clássico de inversão.
            
            **Por que existem valores negativos na Matriz $A$?**  
            Para o computador resolver o sistema, precisamos passar todas as incógnitas para o lado esquerdo e os números puros para o lado direito.  
            * **No Balanço Global:** A lógica "Tudo que Entra = Tudo que Sai" ($E = T + F$) vira $E - T - F = 0$.
            * **Nas Porcentagens:** Se um componente é 20% do total da sua corrente ($F_A = 0.20 \cdot (F_A + F_B)$), a matemática resulta em $0.80F_A - 0.20F_B = 0$.
            """)

            st.markdown("<br>**Mapeamento das Incógnitas (Vetor $x$)**", unsafe_allow_html=True)
            for var in nomes_vars:
                st.markdown(f"- $x_{{{nomes_vars.index(var)}}}$ = {var}")

            st.markdown("<br>**As Equações Essenciais Filtradas**", unsafe_allow_html=True)
            simbolos_vars = [f"F_{{{comp.replace(' ', '')}}}^{{{corr.split('/')[0].replace(' ', '')}}}" for corr in correntes_todas for comp in nomes_comp]
            
            for i, (desc, linha_A, val_B) in enumerate(zip(descricoes_equacoes, A_list, B_list)):
                termos = []
                for coef, simb in zip(linha_A, simbolos_vars):
                    if abs(coef) > 1e-5:
                        if coef == 1.0 and not termos: termos.append(f"{simb}")
                        elif coef == 1.0: termos.append(f"+ {simb}")
                        elif coef == -1.0 and not termos: termos.append(f"-{simb}")
                        elif coef == -1.0: termos.append(f"- {simb}")
                        else:
                            sinal = "+" if coef > 0 else "-"
                            if not termos: termos.append(f"{sinal if sinal=='-' else ''}{abs(coef):.2f}{simb}")
                            else: termos.append(f"{sinal} {abs(coef):.2f}{simb}")
                
                latex_eq = " ".join(termos) + f" = {val_B:.2f}"
                st.markdown(f"**Eq {i+1}** ({desc}):  \n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${latex_eq}$")

            st.markdown("<br>**A Matriz Final Quadrada ($A \\cdot x = B$)**", unsafe_allow_html=True)
            st.info("👀 **Dica de Leitura:** Cada **coluna** da Matriz $A$ está perfeitamente alinhada com as incógnitas. A 1ª coluna contém os coeficientes da 1ª variável do vetor $x$, a 2ª coluna da 2ª, etc.")
            
            def formata_zero(val, casas=2):
                val_rnd = round(val, casas)
                if val_rnd == 0: return "0.00"
                return f"{val_rnd:.{casas}f}"

            linhas_A_latex = [ " & ".join([formata_zero(coef, 2) for coef in linha]) for linha in A_mat ]
            latex_A = r"\begin{bmatrix}" + r" \\ ".join(linhas_A_latex) + r"\end{bmatrix}"
            latex_X = r"\begin{bmatrix}" + r" \\ ".join(simbolos_vars) + r"\end{bmatrix}"
            latex_B = r"\begin{bmatrix}" + r" \\ ".join([formata_zero(val, 2) for val in B_vec]) + r"\end{bmatrix}"
            
            st.latex(f"{latex_A} \\cdot {latex_X} = {latex_B}")

            st.markdown("<br>**Isolando as Incógnitas ($x = A^{-1} \\cdot B$)**", unsafe_allow_html=True)
            
            det_A = np.linalg.det(A_mat)
            st.info(f"""
            🧮 **Como a Matriz Inversa ($A^{{-1}}$) é calculada?**  
            Na álgebra linear, a inversa de uma matriz garante que $A \\cdot A^{{-1}} = I$ (Matriz Identidade). Para que ela exista, o determinante da matriz não pode ser zero. 
            * O simulador calculou o determinante do nosso sistema e encontrou **$\\det(A) = {det_A:.2f}$**. Como é diferente de zero, o sistema tem solução única!
            """)
            
            st.markdown("O método mais utilizado pelos computadores para encontrar a inversa é a **Eliminação de Gauss-Jordan**. O processo começa montando uma **Matriz Aumentada**, colocando a nossa Matriz $A$ lado a lado com uma Matriz Identidade ($I$) de mesmo tamanho:")
            
            I_mat = np.eye(num_vars)
            cols_format = "c" * num_vars + "|" + "c" * num_vars
            linhas_aug = []
            for i in range(num_vars):
                str_A = " & ".join([formata_zero(A_mat[i, j], 2) for j in range(num_vars)])
                str_I = " & ".join([formata_zero(I_mat[i, j], 2) for j in range(num_vars)])
                linhas_aug.append(str_A + " & " + str_I)
            
            latex_aug = r"\left[ \begin{array}{" + cols_format + r"}" + r" \\ ".join(linhas_aug) + r"\end{array} \right]"
            st.latex(latex_aug)
            
            st.markdown("Em seguida, o algoritmo realiza sucessivas operações de soma, subtração e multiplicação entre as linhas até que o lado esquerdo se transforme em uma Matriz Identidade (apenas 1s na diagonal e 0s no resto). Quando isso acontece, os números que sobrarem no lado direito formarão a nossa matriz inversa $A^{-1}$:")
            
            A_inv = np.linalg.inv(A_mat) 
            linhas_Ainv_latex = [ " & ".join([formata_zero(coef, 2) for coef in linha]) for linha in A_inv ]
            latex_Ainv = r"\begin{bmatrix}" + r" \\ ".join(linhas_Ainv_latex) + r"\end{bmatrix}"
            
            st.latex(f"{latex_X} = {latex_Ainv} \\cdot {latex_B}")

            st.markdown("Ao efetuar esta última multiplicação matricial (linha da inversa $\\times$ coluna de $B$), as incógnitas são reveladas, concluindo a modelagem:")
            for simb, val in zip(simbolos_vars, X):
                st.markdown(f"- ${simb} = {val:.2f}$")

    # ==========================================
    # 5. RESULTADOS E DIAGRAMA
    # ==========================================
    st.subheader("📋 Tabela Final de Resultados")
    
    st.dataframe(tabela_final.style.format("{:.2f}"), width="stretch")

    st.markdown("---")
    st.subheader("🗼 Esboço Final da Coluna com Composições")
    
    diagrama = graphviz.Digraph(engine="dot")
    diagrama.attr(rankdir='LR', splines='ortho', nodesep='1.0')
    diagrama.node('Coluna', 'Torre de\nDestilação', shape='cylinder', style='filled', fillcolor='#add8e6', width='1.5', height='1.5')
    
    def montar_label_corrente(nome_corrente):
        v_tot = tabela_final.loc[nome_corrente, ("Geral", "Vazão Total")]
        texto = f"{nome_corrente}\nTotal: {v_tot:.2f}\n"
        for comp in nomes_comp:
            v_c = tabela_final.loc[nome_corrente, (comp, "Vazão")]
            p_c = tabela_final.loc[nome_corrente, (comp, "%")]
            texto += f"- {comp}: {v_c:.2f} ({p_c * 100:.2f}%)\n"
        return texto

    lbl_ent = montar_label_corrente("Entrada")
    diagrama.node('Entrada_Node', 'Entrada', shape='ellipse')
    diagrama.edge('Entrada_Node', 'Coluna', label=lbl_ent)
    
    for corr in correntes_saida:
        lbl_sai = montar_label_corrente(corr)
        node_id = f"Node_{corr}"
        diagrama.node(node_id, corr, shape='ellipse')
        diagrama.edge('Coluna', node_id, label=lbl_sai)
        
    st.graphviz_chart(diagrama, width="stretch")
