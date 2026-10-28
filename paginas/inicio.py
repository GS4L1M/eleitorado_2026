import streamlit as st

from analise import fmt, fmt_pct, matriz_transferencia, recorte

mun, nome = recorte()
s = mun.sum(numeric_only=True)

st.title("Eleição presidencial 2026")
st.markdown("### Lula ficou atrás no 1º turno e venceu no 2º. De onde vieram os votos?")
st.caption(f"Recorte: **{nome}** · Fonte: TSE")

# Resultado dos dois turnos lado a lado
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### 1º turno · 4 de outubro")
    a, b = st.columns(2)
    a.metric("🔵 Flávio", fmt_pct(s["t1_Flávio"] / s["t1_validos"] * 100), fmt(s["t1_Flávio"]),
             delta_color="off", delta_arrow="off")
    b.metric("🔴 Lula", fmt_pct(s["t1_Lula"] / s["t1_validos"] * 100), fmt(s["t1_Lula"]),
             delta_color="off", delta_arrow="off")
with c2:
    st.markdown("#### 2º turno · 25 de outubro")
    a, b = st.columns(2)
    a.metric("🔵 Flávio", fmt_pct(s["t2_Flávio"] / s["t2_validos"] * 100), fmt(s["t2_Flávio"]),
             delta_color="off", delta_arrow="off")
    b.metric("🔴 Lula", fmt_pct(s["t2_Lula"] / s["t2_validos"] * 100), fmt(s["t2_Lula"]),
             delta_color="off", delta_arrow="off")

st.divider()

# Principais achados, calculados para o recorte escolhido
P = matriz_transferencia(mun)
t1 = s[[f"t1_{g}" for g in P.index]].to_numpy()
para_lula = (P["Lula"] * t1).drop("Lula").sort_values(ascending=False)
ganho_lula = s["t2_Lula"] - s["t1_Lula"]
ganho_flavio = s["t2_Flávio"] - s["t1_Flávio"]

st.markdown("### Resumo")
c1, c2, c3 = st.columns(3)
c1.metric("Votos que Lula ganhou do 1º para o 2º turno", f"+{fmt(ganho_lula)}")
c2.metric("Votos que Flávio ganhou", f"+{fmt(ganho_flavio)}")
c3.metric("Maior fonte dos votos novos de Lula (estimado)", para_lula.index[0],
          f"~{fmt(para_lula.iloc[0])}", delta_color="off", delta_arrow="off")

st.markdown(f"""
- Lula ganhou **{fmt(ganho_lula)}** de votos entre os turnos; Flávio, **{fmt(ganho_flavio)}**.
- As três maiores fontes estimadas dos votos novos de Lula foram
  **{para_lula.index[0]}** (~{fmt(para_lula.iloc[0])}),
  **{para_lula.index[1]}** (~{fmt(para_lula.iloc[1])}) e
  **{para_lula.index[2]}** (~{fmt(para_lula.iloc[2])}).
- A abstenção caiu **{fmt(s['t1_Abstenção'] - s['t2_Abstenção'])}** e os brancos e nulos caíram
  **{fmt(s['t1_Branco/Nulo'] - s['t2_Branco/Nulo'])}**.
""")

st.divider()
st.markdown("### Navegue pela análise")
c1, c2, c3, c5, c4 = st.columns(5)
with c1:
    st.page_link("paginas/primeiro_turno.py", label="1º turno", icon="1️⃣")
    st.caption("Resultado por candidato, mapa e regiões.")
with c2:
    st.page_link("paginas/segundo_turno.py", label="2º turno", icon="2️⃣")
    st.caption("Lula x Flávio por estado, município e região.")
with c3:
    st.page_link("paginas/comparacao.py", label="Comparação", icon="🔀")
    st.caption("O que mudou e de onde vieram os votos de Lula.")
with c5:
    st.page_link("paginas/perfil_eleitorado.py", label="Perfil do eleitorado", icon="👥")
    st.caption("Idade e escolaridade dos eleitores de cada estado.")
with c4:
    st.page_link("paginas/metodologia.py", label="Metodologia", icon="🧪")
    st.caption("Etapas da análise, fontes e validações.")
