import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analise import (grafico, AZUL, CORES_REGIAO, CORES, ELIMINADOS, ORIGENS, REGIOES, VERMELHO, carregar, como_ler, fmt,
                     fmt_pct, mapa, matriz_transferencia, recorte, tabela_mapa, tabela_municipios)

mun, nome = recorte()
s = mun.sum(numeric_only=True)
ganho_lula = s["t2_Lula"] - s["t1_Lula"]
ganho_flavio = s["t2_Flávio"] - s["t1_Flávio"]

st.title("Comparação entre os turnos")
st.markdown("#### De onde vieram os votos que Lula ganhou no 2º turno?")
st.caption(f"Recorte: **{nome}**")

c1, c2, c3, c4 = st.columns(4)
c1.metric("🔴 Lula ganhou", f"+{fmt(ganho_lula)}")
c2.metric("🔵 Flávio ganhou", f"+{fmt(ganho_flavio)}")
c3.metric("Eleitores sem candidato no 2º turno", fmt(sum(s[f"t1_{g}"] for g in ELIMINADOS)))
c4.metric("Eleitores a mais que foram votar", fmt(s["t1_Abstenção"] - s["t2_Abstenção"]))

# ---------------------------------------------------------------------------
# 1) O que mudou no mapa
# ---------------------------------------------------------------------------
st.divider()
st.subheader("1. O que mudou no mapa")
nivel = st.segmented_control("Ver por", ["Estado", "Município"], default="Estado", key="nivel_cmp") or "Estado"
d = tabela_mapa(mun, nivel)

c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Vencedor no 1º turno**")
    grafico(mapa(d, nivel, altura=430, color="vencedor1", color_discrete_map=CORES,
                 hover_data={"id": False}, labels={"vencedor1": "Vencedor"}), key="mapa_v1")
with c2:
    st.markdown("**Vencedor no 2º turno**")
    grafico(mapa(d, nivel, altura=430, color="vencedor2", color_discrete_map=CORES,
                 hover_data={"id": False}, labels={"vencedor2": "Vencedor"}), key="mapa_v2")

virou = d[(d["vencedor1"] != "Lula") & (d["vencedor2"] == "Lula")]
unidade = ("estado" if nivel == "Estado" else "município") + ("s" if len(virou) > 1 else "")
if len(virou):
    nomes = ", ".join(virou.sort_values("aptos", ascending=False)["local"].head(8))
    st.info(f"**{len(virou)} {unidade} {'viraram' if len(virou) > 1 else 'virou'} para Lula** no 2º turno: {nomes}"
            + ("..." if len(virou) > 8 else "."))

# ---------------------------------------------------------------------------
# 2) De onde vieram os votos novos de Lula
# ---------------------------------------------------------------------------
st.divider()
st.subheader("2. De onde vieram os votos novos de Lula")
if len(mun) < 30:
    st.warning("Poucos municípios neste recorte: a estimativa fica instável. Prefira uma região inteira.")

P = matriz_transferencia(mun)
fluxo = P.mul(s[[f"t1_{g}" for g in ORIGENS]].to_numpy(), axis=0)
rotulos = {"Branco/Nulo": "Votou branco/nulo no 1º", "Abstenção": "Não votou no 1º",
           "Augusto Cury": "Eleitor de Augusto Cury", "Renan Santos": "Eleitor de Renan Santos",
           "Ronaldo Caiado": "Eleitor de Ronaldo Caiado", "Outros": "Eleitor de outros candidatos"}

c1, c2 = st.columns(2, gap="large")
for col, candidato, cor in [(c1, "Lula", VERMELHO), (c2, "Flávio", AZUL)]:
    with col:
        origem = fluxo[candidato].drop(["Lula", "Flávio"]).rename(rotulos).sort_values()
        origem = origem[origem > 1000]
        st.markdown(f"**Votos novos de {candidato}: ~{fmt(origem.sum())}**")
        fig = px.bar(x=origem.values, y=origem.index, orientation="h", text=[fmt(v) for v in origem.values])
        fig.update_traces(marker_color=cor, textposition="outside", cliponaxis=False)
        fig.update_layout(height=300, xaxis=dict(visible=False, range=[0, fluxo[["Lula", "Flávio"]]
                                                                   .drop(["Lula", "Flávio"]).max().max() * 1.3]),
                          yaxis_title="", margin=dict(l=0, r=0, t=10, b=10))
        grafico(fig, key=f"origem_{candidato}")
como_ler("cada barra estima quantos eleitores daquele grupo do 1º turno votaram no candidato no 2º. "
         "As duas colunas usam a mesma escala.")

st.markdown("**Para onde foi cada grupo de eleitores** (estimado)")
tabela = P.drop(["Lula", "Flávio"]).rename(index=rotulos)
longo = (tabela * 100).reset_index(names="origem").melt(id_vars="origem", var_name="destino",
                                                        value_name="pct")
longo["destino"] = longo["destino"].replace({"Branco/Nulo": "Branco/nulo", "Abstenção": "Não votou"})
fig = px.bar(longo, x="pct", y="origem", color="destino", orientation="h",
             color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL, "Branco/nulo": "#707070",
                                 "Não votou": "#D5D5D5"},
             text=longo["pct"].map(lambda v: f"{v:.0f}%" if v >= 6 else ""),
             category_orders={"origem": list(tabela.index)[::-1],
                              "destino": ["Lula", "Flávio", "Branco/nulo", "Não votou"]})
fig.update_traces(textposition="inside", insidetextanchor="middle")
fig.update_layout(height=340, xaxis=dict(visible=False), yaxis_title="",
                  legend=dict(orientation="h", y=-0.08, title="No 2º turno:"),
                  margin=dict(l=0, r=0, t=10, b=10))
grafico(fig)
como_ler("cada barra é 100% de um grupo do 1º turno, dividido pelo que esse grupo fez no 2º.")

with st.expander("Como essa estimativa é feita (e seus limites)"):
    st.markdown("""
O voto é secreto, então não dá para saber quem migrou para quem. O modelo usa **inferência
ecológica**: compara, município a município, o 1º turno com o 2º e encontra as proporções de
transferência (entre 0% e 100%, somando 100% por grupo) que melhor explicam todos os municípios
ao mesmo tempo. Municípios maiores pesam mais.

- É uma **estimativa média** para o recorte. Filtrar por região costuma dar resultados mais confiáveis.
- Brancos, nulos e abstenção se misturam: quem anulou no 1º turno pode ter votado no 2º, e vice-versa.
- Use os números como **ordem de grandeza**, não como contagem exata.
""")

# ---------------------------------------------------------------------------
# 3) Por região
# ---------------------------------------------------------------------------
st.divider()
st.subheader("3. Onde cada candidato cresceu")
todos = tabela_municipios()
todos = todos[todos["uf"] != "ZZ"]
reg = todos.groupby("regiao").sum(numeric_only=True).reindex(REGIOES)
ganho = pd.DataFrame({"Lula": reg["t2_Lula"] - reg["t1_Lula"],
                      "Flávio": reg["t2_Flávio"] - reg["t1_Flávio"]})

c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Votos ganhos do 1º para o 2º turno, por região**")
    longo = ganho.reset_index(names="regiao").melt(id_vars="regiao", var_name="candidato",
                                                   value_name="ganho")
    fig = px.bar(longo, x="regiao", y="ganho", color="candidato", barmode="group",
                 color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL},
                 text=longo["ganho"].map(fmt))
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
    fig.update_layout(height=380, yaxis=dict(visible=False), xaxis_title="",
                      legend=dict(orientation="h", y=1.08, title=""),
                      margin=dict(l=0, r=0, t=30, b=10))
    grafico(fig)
    maior = ganho["Lula"].idxmax()
    como_ler(f"o **{maior}** deu a Lula {fmt(ganho.loc[maior, 'Lula'])} de votos novos, "
             f"{fmt_pct(ganho.loc[maior, 'Lula'] / ganho['Lula'].sum() * 100, 0)} do total. "
             "Este gráfico mostra sempre o Brasil inteiro.")

with c2:
    st.markdown("**Crescimento de Lula em % dos eleitores aptos**")
    fig = mapa(d, nivel, altura=380, color="ganho_lula_pct",
               color_continuous_scale=["#FFF5F0", "#F08080", VERMELHO, "#6B0012"],
               range_color=(0, d["ganho_lula_pct"].quantile(0.98)),
               hover_data={"id": False, "ganho_lula_pct": ":.1f"},
               labels={"ganho_lula_pct": "Lula cresceu (p.p.)"})
    fig.update_layout(coloraxis_colorbar=dict(title="p.p.", orientation="h", y=-0.05, thickness=12))
    grafico(fig, key="mapa_cresc")

# ---------------------------------------------------------------------------
# 4) Perfil do eleitorado
# ---------------------------------------------------------------------------
st.divider()
st.subheader("4. Perfil dos municípios onde Lula mais cresceu")
_, _, perfil = carregar()
if perfil is None:
    st.info("Rode `python preparar_dados.py --perfil` para habilitar esta seção.")
else:
    pm = mun.merge(perfil.drop(columns="uf"), on="cd_tse")
    pm["crescimento"] = (pm["t2_Lula"] - pm["t1_Lula"]) / pm["aptos"] * 100
    indicadores = {"% mulheres": "pct_mulheres",
                   "% de 16 a 24 anos": "pct_jovens_16_24",
                   "% com 60 anos ou mais": "pct_idosos_60_mais",
                   "% até fundamental incompleto": "pct_escolaridade_baixa",
                   "% com superior completo": "pct_superior_completo"}
    corr = {k: np.corrcoef(pm[v], pm["crescimento"])[0, 1] for k, v in indicadores.items()}

    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        st.markdown("**Relação com o crescimento de Lula**")
        cs = pd.Series(corr).sort_values()
        fig = px.bar(x=cs.values, y=cs.index, orientation="h", text=[f"{v:+.2f}" for v in cs.values])
        fig.update_traces(marker_color=[VERMELHO if v > 0 else AZUL for v in cs.values],
                          textposition="outside", cliponaxis=False)
        fig.update_layout(height=300, xaxis=dict(range=[-1, 1], title="correlação"),
                          yaxis_title="", margin=dict(l=0, r=20, t=10, b=10))
        grafico(fig)
        como_ler("acima de 0 = onde há mais desse grupo, Lula cresceu mais. Perto de 0 = sem relação. "
                 "Correlação não prova causa.")
    with c2:
        escolha = st.selectbox("Ver detalhe de", list(indicadores), key="indicador")
        fig = px.scatter(pm, x=indicadores[escolha], y="crescimento", size="aptos", color="regiao",
                         hover_name="municipio", size_max=25, opacity=0.55,
                         color_discrete_map=CORES_REGIAO, category_orders={"regiao": REGIOES},
                         labels={indicadores[escolha]: escolha, "crescimento": "Lula cresceu (p.p.)",
                                 "regiao": ""})
        fig.update_layout(height=340, legend=dict(orientation="h", y=1.1),
                          margin=dict(l=0, r=0, t=30, b=10))
        grafico(fig)

# ---------------------------------------------------------------------------
# 5) Ranking
# ---------------------------------------------------------------------------
st.divider()
st.subheader("5. Municípios onde Lula mais ganhou votos")
top = mun.assign(ganho_lula=mun["t2_Lula"] - mun["t1_Lula"],
                 ganho_flavio=mun["t2_Flávio"] - mun["t1_Flávio"],
                 eliminados=mun[[f"t1_{g}" for g in ELIMINADOS]].sum(axis=1))
top = top.nlargest(15, "ganho_lula")[["municipio", "uf", "t1_Lula", "t2_Lula", "ganho_lula",
                                       "ganho_flavio", "eliminados"]]
top.columns = ["Município", "UF", "Lula 1º", "Lula 2º", "Lula ganhou", "Flávio ganhou",
               "Votos dos eliminados"]
st.dataframe(top.style.format({c: lambda v: f"{v:,.0f}".replace(",", ".") for c in top.columns[2:]}),
             width="stretch", hide_index=True)
