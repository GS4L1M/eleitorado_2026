"""
Dashboard: eleição presidencial 2026, 1º turno, 2º turno e de onde vieram os votos de Lula.

Antes de rodar, gere os dados com:  python preparar_dados.py  (ou --perfil)
Uso:  python -m streamlit run app.py
"""

import streamlit as st

from analise import REGIOES, tabela_municipios

st.set_page_config(page_title="Eleições 2026", page_icon="🗳️", layout="wide")

paginas = st.navigation([
    st.Page("paginas/inicio.py", title="Início", icon="🏠", default=True),
    st.Page("paginas/primeiro_turno.py", title="1º turno", icon="1️⃣"),
    st.Page("paginas/segundo_turno.py", title="2º turno", icon="2️⃣"),
    st.Page("paginas/comparacao.py", title="Comparação entre turnos", icon="🔀"),
    st.Page("paginas/perfil_eleitorado.py", title="Perfil do eleitorado", icon="👥"),
    st.Page("paginas/metodologia.py", title="Metodologia e dados", icon="🧪"),
])

# Filtros: ficam na barra lateral e valem para todas as páginas
st.sidebar.header("Filtros")
regiao = st.sidebar.selectbox("Região", ["Brasil"] + REGIOES, key="regiao")
mun = tabela_municipios()
ufs = sorted(mun.loc[mun["regiao"] == regiao, "uf"].unique()) if regiao != "Brasil" else []
if st.session_state.get("uf") not in ["Todos"] + ufs:
    st.session_state["uf"] = "Todos"
st.sidebar.selectbox("Estado", ["Todos"] + ufs, key="uf", disabled=regiao == "Brasil",
                     help="Escolha uma região para filtrar por estado.")
st.sidebar.caption("🔵 Flávio Bolsonaro · 🔴 Lula")

paginas.run()
