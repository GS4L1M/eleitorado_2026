import pandas as pd
import plotly.express as px
import streamlit as st

from analise import (grafico, AZUL, REGIOES, VERMELHO, como_ler, fmt, fmt_pct, mapa, recorte,
                     tabela_mapa)

mun, nome = recorte()
s = mun.sum(numeric_only=True)

st.title("2º turno · 25 de outubro de 2026")
st.caption(f"Recorte: **{nome}**")

# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("🔴 Lula", fmt_pct(s["t2_Lula"] / s["t2_validos"] * 100), fmt(s["t2_Lula"]),
          delta_color="off", delta_arrow="off")
c2.metric("🔵 Flávio", fmt_pct(s["t2_Flávio"] / s["t2_validos"] * 100), fmt(s["t2_Flávio"]),
          delta_color="off", delta_arrow="off")
dif = s["t2_Lula"] - s["t2_Flávio"]
c3.metric("Diferença", fmt(abs(dif)), "a favor de " + ("Lula" if dif >= 0 else "Flávio"),
          delta_color="off", delta_arrow="off")
c4.metric("Não votaram ou anularam", fmt_pct((s["t2_Abstenção"] + s["t2_Branco/Nulo"]) / s["aptos"] * 100),
          "dos eleitores aptos", delta_color="off", delta_arrow="off")

# Barra única Lula x Flávio
pct_lula = s["t2_Lula"] / s["t2_validos"] * 100
fig = px.bar(pd.DataFrame({"c": ["Lula", "Flávio"], "pct": [pct_lula, 100 - pct_lula], "y": [""] * 2}),
             x="pct", y="y", color="c", orientation="h", text_auto=".1f",
             color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL})
fig.update_traces(texttemplate="%{x:.1f}%", textposition="inside", textfont_size=16)
fig.update_layout(height=110, showlegend=False, xaxis=dict(visible=False, range=[0, 100]),
                  yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0))
grafico(fig)

# ---------------------------------------------------------------------------
# Mapa da margem + estados
# ---------------------------------------------------------------------------
st.subheader("Vantagem de cada candidato")
nivel = st.segmented_control("Ver por", ["Estado", "Município"], default="Estado", key="nivel_t2")
d = tabela_mapa(mun, nivel or "Estado")
lim = max(abs(d["margem2"]).quantile(0.98), 5)

col_mapa, col_uf = st.columns([3, 2], gap="large")
with col_mapa:
    fig = mapa(d, nivel or "Estado", color="margem2", range_color=(-lim, lim),
               color_continuous_scale=[AZUL, "#F4F4F4", VERMELHO],
               hover_data={"id": False, "pct2_Lula": ":.1f", "pct2_Flávio": ":.1f", "margem2": False},
               labels={"pct2_Lula": "% Lula", "pct2_Flávio": "% Flávio"})
    fig.update_layout(coloraxis_colorbar=dict(
        title="", orientation="h", y=-0.05, thickness=12,
        tickvals=[-lim, 0, lim], ticktext=[f"Flávio +{lim:.0f} p.p.", "empate", f"Lula +{lim:.0f} p.p."]))
    grafico(fig)
    como_ler("quanto mais forte a cor, maior a vantagem. Azul = Flávio, vermelho = Lula.")

with col_uf:
    st.markdown("**% de Lula nos votos válidos, por estado**")
    uf = tabela_mapa(mun, "Estado").sort_values("pct2_Lula")
    uf["vencedor"] = uf["vencedor2"]
    fig = px.bar(uf, x="margem2", y="uf", orientation="h", color="vencedor",
                 color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL},
                 text=uf["pct2_Lula"].map(lambda v: f"{v:.0f}%"),
                 hover_data={"pct2_Lula": ":.1f", "margem2": False, "vencedor": False})
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
    fig.update_layout(height=max(260, 22 * len(uf)), showlegend=False, yaxis_title="",
                      xaxis=dict(title="← Flávio · Lula →", zeroline=True, zerolinecolor="#888",
                                 showticklabels=False, showgrid=False,
                                 range=[uf["margem2"].min() * 1.3 - 5, uf["margem2"].max() * 1.3 + 5]),
                      margin=dict(l=0, r=30, t=10, b=10))
    grafico(fig)

# ---------------------------------------------------------------------------
# Por região
# ---------------------------------------------------------------------------
st.subheader("Resultado por região")
reg = mun[mun["uf"] != "ZZ"].groupby("regiao")[["t2_Lula", "t2_Flávio"]].sum()
reg = reg.reindex([r for r in REGIOES if r in reg.index])
reg_pct = reg.div(reg.sum(axis=1), axis=0) * 100
longo = reg_pct.rename(columns={"t2_Lula": "Lula", "t2_Flávio": "Flávio"}).reset_index() \
    .melt(id_vars="regiao", var_name="candidato", value_name="pct")
fig = px.bar(longo, x="pct", y="regiao", color="candidato", orientation="h",
             color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL},
             text=longo["pct"].map(lambda v: f"{v:.1f}%".replace(".", ",")),
             category_orders={"regiao": REGIOES[::-1], "candidato": ["Lula", "Flávio"]})
fig.add_vline(x=50, line_dash="dot", line_color="#888")
fig.update_traces(textposition="inside", insidetextanchor="middle")
fig.update_layout(height=320, xaxis=dict(visible=False), yaxis_title="",
                  legend=dict(orientation="h", y=-0.1, title=""), margin=dict(l=0, r=0, t=10, b=10))
grafico(fig)
como_ler("a linha pontilhada marca 50%. Quem passa dela venceu na região.")
