import pandas as pd
import plotly.express as px
import streamlit as st

from analise import (grafico, CANDIDATOS_T1, CORES, ELIMINADOS, REGIOES, como_ler, fmt,
                     fmt_pct, mapa, recorte, tabela_mapa)

mun, nome = recorte()
s = mun.sum(numeric_only=True)

st.title("1º turno · 4 de outubro de 2026")
st.caption(f"Recorte: **{nome}**")

# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("🔵 Flávio", fmt_pct(s["t1_Flávio"] / s["t1_validos"] * 100), fmt(s["t1_Flávio"]),
          delta_color="off", delta_arrow="off")
c2.metric("🔴 Lula", fmt_pct(s["t1_Lula"] / s["t1_validos"] * 100), fmt(s["t1_Lula"]),
          delta_color="off", delta_arrow="off")
demais = sum(s[f"t1_{g}"] for g in ELIMINADOS)
c3.metric("Demais candidatos", fmt_pct(demais / s["t1_validos"] * 100), fmt(demais),
          delta_color="off", delta_arrow="off")
c4.metric("Não votaram ou anularam", fmt_pct((s["t1_Abstenção"] + s["t1_Branco/Nulo"]) / s["aptos"] * 100),
          "dos eleitores aptos", delta_color="off", delta_arrow="off")

# ---------------------------------------------------------------------------
# Votos por candidato
# ---------------------------------------------------------------------------
st.subheader("Votos válidos por candidato")
cand = pd.DataFrame({"candidato": CANDIDATOS_T1,
                     "votos": [s[f"t1_{g}"] for g in CANDIDATOS_T1]})
cand["pct"] = cand["votos"] / cand["votos"].sum() * 100
cand["texto"] = cand.apply(lambda r: f"{fmt_pct(r.pct)}  ({fmt(r.votos)})", axis=1)
cand = cand.sort_values("votos")
fig = px.bar(cand, x="pct", y="candidato", orientation="h", text="texto",
             color="candidato", color_discrete_map=CORES)
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(height=330, showlegend=False, xaxis=dict(visible=False, range=[0, cand["pct"].max() * 1.35]),
                  yaxis_title="", margin=dict(l=0, r=0, t=10, b=10))
grafico(fig)

# ---------------------------------------------------------------------------
# Mapa + regiões
# ---------------------------------------------------------------------------
st.subheader("Quem ficou em 1º lugar em cada lugar")
nivel = st.segmented_control("Ver por", ["Estado", "Município"], default="Estado", key="nivel_t1")
d = tabela_mapa(mun, nivel or "Estado")

col_mapa, col_reg = st.columns([3, 2], gap="large")
with col_mapa:
    fig = mapa(d, nivel or "Estado", color="vencedor1", color_discrete_map=CORES,
               hover_data={"id": False, "pct1_Flávio": ":.1f", "pct1_Lula": ":.1f"},
               labels={"vencedor1": "1º lugar", "pct1_Flávio": "% Flávio", "pct1_Lula": "% Lula"})
    grafico(fig)
    venc = d["vencedor1"].value_counts()
    unidade = "estados" if nivel != "Município" else "municípios"
    como_ler(" · ".join(f"{k} venceu em **{v}** {unidade}" for k, v in venc.items()) + ".")

with col_reg:
    st.markdown("**Divisão dos votos válidos por região**")
    reg = mun[mun["uf"] != "ZZ"].groupby("regiao")[[f"t1_{g}" for g in CANDIDATOS_T1]].sum()
    reg = pd.DataFrame({"Flávio": reg["t1_Flávio"], "Lula": reg["t1_Lula"],
                        "Demais candidatos": reg[[f"t1_{g}" for g in ELIMINADOS]].sum(axis=1)})
    reg = (reg.div(reg.sum(axis=1), axis=0) * 100).reindex([r for r in REGIOES if r in reg.index])
    longo = reg.reset_index().melt(id_vars="regiao", var_name="grupo", value_name="pct")
    fig = px.bar(longo, x="pct", y="regiao", color="grupo", orientation="h",
                 color_discrete_map=CORES, text=longo["pct"].map(lambda v: f"{v:.0f}%" if v >= 8 else ""),
                 category_orders={"regiao": REGIOES[::-1], "grupo": ["Flávio", "Lula", "Demais candidatos"]})
    fig.update_traces(textposition="inside", insidetextanchor="middle", textangle=0)
    fig.update_layout(height=380, xaxis=dict(visible=False), yaxis_title="",
                      legend=dict(orientation="h", y=-0.08, title=""),
                      margin=dict(l=0, r=0, t=10, b=10))
    grafico(fig)
    como_ler("cada barra soma 100% dos votos válidos da região.")

# ---------------------------------------------------------------------------
# Onde os demais candidatos foram fortes
# ---------------------------------------------------------------------------
st.subheader("Onde os demais candidatos tiveram mais votos")
st.markdown("Esses eleitores ficaram **sem candidato no 2º turno** e decidiram a eleição.")
col_mapa, col_bar = st.columns([3, 2], gap="large")
with col_mapa:
    fig = mapa(d, nivel or "Estado", color="pct1_Demais",
               color_continuous_scale=["#FFF7E6", "#E8A33D", "#8A5A00"],
               range_color=(0, d["pct1_Demais"].quantile(0.98)),
               hover_data={"id": False, "pct1_Demais": ":.1f"},
               labels={"pct1_Demais": "% demais candidatos"})
    fig.update_layout(coloraxis_colorbar=dict(title="%", orientation="h", y=-0.05, thickness=12))
    grafico(fig)
with col_bar:
    st.markdown("**Votos dos candidatos eliminados**")
    el = pd.DataFrame({"candidato": ELIMINADOS, "votos": [s[f"t1_{g}"] for g in ELIMINADOS]})
    el = el.sort_values("votos")
    fig = px.bar(el, x="votos", y="candidato", orientation="h", color="candidato",
                 color_discrete_map=CORES, text=el["votos"].map(fmt))
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=300, showlegend=False, yaxis_title="",
                      xaxis=dict(visible=False, range=[0, el["votos"].max() * 1.3]),
                      margin=dict(l=0, r=0, t=10, b=10))
    grafico(fig)
    como_ler(f"juntos, somaram **{fmt(demais)}** de votos, mais que a diferença entre "
             f"Lula e Flávio no 2º turno.")
