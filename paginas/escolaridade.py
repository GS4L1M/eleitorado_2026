import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analise import (AZUL, CORES_ESCOLARIDADE, FAIXAS_ESCOLARIDADE, FAIXAS_MODELO, NIVEIS_ESCOLARIDADE, REGIOES,
                     VERMELHO, carregar, como_ler, fmt, fmt_pct, grafico, mapa, recorte,
                     tabela_mapa, tem_escolaridade, voto_por_escolaridade)

mun, nome = recorte()
_, _, perfil = carregar()

st.title("Escolaridade e voto")
st.markdown("#### Como votou cada nível de escolaridade, e onde Lula cresceu entre os turnos?")
st.caption(f"Recorte: **{nome}** · Fonte: TSE (perfil do eleitorado e votação por seção)")

if not tem_escolaridade(perfil):
    st.info("Rode `python preparar_dados.py --perfil` para gerar os dados de escolaridade.")
    st.stop()

d = mun[mun["uf"] != "ZZ"].merge(perfil[["cd_tse"] + list(NIVEIS_ESCOLARIDADE)], on="cd_tse")
for faixa, cols in FAIXAS_ESCOLARIDADE.items():
    d[faixa] = d[cols].sum(axis=1)
d["eleitores_perfil"] = d[list(NIVEIS_ESCOLARIDADE)].sum(axis=1)
d["pct_superior"] = d["Superior completo"] / d["eleitores_perfil"] * 100
d["pct_sem_fund"] = d["Sem fundamental completo"] / d["eleitores_perfil"] * 100
tot = d[list(FAIXAS_ESCOLARIDADE)].sum()

# ---------------------------------------------------------------------------
# 1) Quem é o eleitor
# ---------------------------------------------------------------------------
st.divider()
st.subheader("1. Escolaridade do eleitorado")
cols = st.columns(4)
for col, (faixa, n) in zip(cols, tot.items()):
    col.metric(faixa, fmt_pct(n / tot.sum() * 100), fmt(n), delta_color="off", delta_arrow="off")

c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Eleitores por nível de escolaridade**")
    niveis = d[list(NIVEIS_ESCOLARIDADE)].sum().rename(NIVEIS_ESCOLARIDADE)
    faixa_de = {NIVEIS_ESCOLARIDADE[c]: f for f, cs in FAIXAS_ESCOLARIDADE.items() for c in cs}
    df = pd.DataFrame({"nivel": niveis.index, "pct": niveis.values / niveis.sum() * 100})
    df["faixa"] = df["nivel"].map(faixa_de)
    fig = px.bar(df, x="pct", y="nivel", orientation="h", color="faixa",
                 color_discrete_map=CORES_ESCOLARIDADE,
                 text=df["pct"].map(lambda v: fmt_pct(v)),
                 category_orders={"nivel": list(NIVEIS_ESCOLARIDADE.values())})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=360, xaxis=dict(visible=False, range=[0, df["pct"].max() * 1.25]),
                      yaxis_title="", legend=dict(orientation="h", y=-0.05, title=""),
                      margin=dict(l=0, r=0, t=10, b=10))
    grafico(fig)
    como_ler("as cores mostram como os 8 níveis do TSE foram agrupados em 4 faixas.")

with c2:
    st.markdown("**Faixas de escolaridade por região**")
    reg = d.groupby("regiao")[list(FAIXAS_ESCOLARIDADE)].sum()
    reg = (reg.div(reg.sum(axis=1), axis=0) * 100).reindex([r for r in REGIOES if r in reg.index])
    longo = reg.reset_index().melt(id_vars="regiao", var_name="faixa", value_name="pct")
    fig = px.bar(longo, x="pct", y="regiao", color="faixa", orientation="h",
                 color_discrete_map=CORES_ESCOLARIDADE,
                 text=longo["pct"].map(lambda v: f"{v:.0f}%" if v >= 7 else ""),
                 category_orders={"regiao": REGIOES[::-1], "faixa": list(FAIXAS_ESCOLARIDADE)})
    fig.update_traces(textposition="inside", insidetextanchor="middle", textangle=0)
    fig.update_layout(height=360, xaxis=dict(visible=False), yaxis_title="",
                      legend=dict(orientation="h", y=-0.05, title=""),
                      margin=dict(l=0, r=0, t=10, b=10))
    grafico(fig)
    como_ler("cada barra soma 100% dos eleitores da região.")

# ---------------------------------------------------------------------------
# 2) Mapa
# ---------------------------------------------------------------------------
st.divider()
st.subheader("2. Onde estão os eleitores mais e menos escolarizados")
m1, m2 = st.columns([2, 1])
indicador = m1.segmented_control("Mostrar", ["% com superior completo", "% sem fundamental completo"],
                                 default="% com superior completo", key="esc_ind") \
    or "% com superior completo"
nivel = m2.segmented_control("Ver por", ["Estado", "Município"], default="Estado", key="nivel_esc") \
    or "Estado"
coluna = "pct_superior" if "superior" in indicador else "pct_sem_fund"

dm = tabela_mapa(mun, nivel)
base = d.assign(sup=d["Superior completo"], sem=d["Sem fundamental completo"])
if nivel == "Estado":
    agg = base.groupby("uf")[["sup", "sem", "eleitores_perfil"]].sum()
    dm = dm.merge(agg, left_on="uf", right_index=True)
else:
    dm = dm.merge(base[["cd_tse", "sup", "sem", "eleitores_perfil"]], on="cd_tse")
dm["pct_superior"] = dm["sup"] / dm["eleitores_perfil"] * 100
dm["pct_sem_fund"] = dm["sem"] / dm["eleitores_perfil"] * 100

c1, c2 = st.columns([3, 2], gap="large")
with c1:
    fig = mapa(dm, nivel, color=coluna,
               color_continuous_scale=["#F3EEFA", "#AE93D4", "#45267A"],
               range_color=(dm[coluna].quantile(0.02), dm[coluna].quantile(0.98)),
               hover_data={"id": False, coluna: ":.1f", "pct2_Lula": ":.1f"},
               labels={coluna: indicador, "pct2_Lula": "% Lula no 2º turno"})
    fig.update_layout(coloraxis_colorbar=dict(title="%", orientation="h", y=-0.05, thickness=12))
    grafico(fig, key="mapa_esc")
with c2:
    uf = dm.copy() if nivel == "Estado" else tabela_mapa(mun, "Estado").merge(
        base.groupby("uf")[["sup", "sem", "eleitores_perfil"]].sum(), left_on="uf", right_index=True)
    uf["valor"] = uf["sup" if coluna == "pct_superior" else "sem"] / uf["eleitores_perfil"] * 100
    uf = uf.sort_values("valor")
    st.markdown(f"**{indicador}, por estado**")
    fig = px.bar(uf, x="valor", y="uf", orientation="h", color="vencedor2",
                 color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL},
                 text=uf["valor"].map(lambda v: f"{v:.0f}%"))
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
    fig.update_layout(height=max(260, 20 * len(uf)), yaxis_title="",
                      xaxis=dict(visible=False, range=[0, uf["valor"].max() * 1.2]),
                      showlegend=False, margin=dict(l=0, r=20, t=10, b=10))
    grafico(fig, key="barra_esc_uf")
    como_ler("a cor mostra quem venceu no estado no 2º turno (azul = Flávio, vermelho = Lula).")

# ---------------------------------------------------------------------------
# 3) Voto conforme a escolaridade do município
# ---------------------------------------------------------------------------
st.divider()
st.subheader("3. Como votaram os municípios mais e menos escolarizados")
st.markdown("Os municípios foram ordenados pela % de eleitores com superior completo e divididos em "
            "**5 grupos com o mesmo número de eleitores**.")

ordenado = d.sort_values("pct_superior")
acumulado = ordenado["eleitores_perfil"].cumsum() / ordenado["eleitores_perfil"].sum()
ordenado["grupo"] = np.minimum((acumulado * 5).apply(np.ceil).astype(int), 5).clip(lower=1)
g = ordenado.groupby("grupo").agg(
    t1_Lula=("t1_Lula", "sum"), t1_validos=("t1_validos", "sum"),
    t2_Lula=("t2_Lula", "sum"), t2_validos=("t2_validos", "sum"),
    t2_Flávio=("t2_Flávio", "sum"), t1_Flávio=("t1_Flávio", "sum"),
    sup_min=("pct_superior", "min"), sup_max=("pct_superior", "max"),
    municipios=("cd_tse", "count"))
nomes_grupo = {1: "Menos escolarizados", 2: "2º grupo", 3: "3º grupo", 4: "4º grupo", 5: "Mais escolarizados"}
curtos = {1: "Menos", 2: "2º", 3: "3º", 4: "4º", 5: "Mais"}
g["rotulo"] = [f"<b>{curtos[i]}</b><br>{r.sup_min:.0f}–{r.sup_max:.0f}%" for i, r in g.iterrows()]
g["Lula 1º turno"] = g["t1_Lula"] / g["t1_validos"] * 100
g["Lula 2º turno"] = g["t2_Lula"] / g["t2_validos"] * 100
g["ganho_lula"] = g["t2_Lula"] - g["t1_Lula"]
g["ganho_flavio"] = g["t2_Flávio"] - g["t1_Flávio"]

c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**% de Lula nos votos válidos**")
    longo = g.melt(id_vars="rotulo", value_vars=["Lula 1º turno", "Lula 2º turno"],
                   var_name="turno", value_name="pct")
    fig = px.bar(longo, x="rotulo", y="pct", color="turno", barmode="group",
                 color_discrete_map={"Lula 1º turno": "#F0A0A8", "Lula 2º turno": VERMELHO},
                 text=longo["pct"].map(lambda v: f"{v:.0f}%"))
    fig.add_hline(y=50, line_dash="dot", line_color="#888")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=400, yaxis=dict(visible=False, range=[0, longo["pct"].max() * 1.2]),
                      xaxis=dict(title="% de eleitores com superior completo no grupo", tickangle=0),
                      legend=dict(orientation="h", y=1.08, title=""),
                      margin=dict(l=0, r=0, t=30, b=10))
    grafico(fig, key="lula_grupos")
    como_ler("a linha pontilhada marca 50%. Compare a barra clara (1º turno) com a escura (2º).")

with c2:
    st.markdown("**Votos ganhos do 1º para o 2º turno**")
    longo = g.rename(columns={"ganho_lula": "Lula", "ganho_flavio": "Flávio"}) \
        .melt(id_vars="rotulo", value_vars=["Lula", "Flávio"], var_name="candidato", value_name="ganho")
    fig = px.bar(longo, x="rotulo", y="ganho", color="candidato", barmode="group",
                 color_discrete_map={"Lula": VERMELHO, "Flávio": AZUL},
                 text=longo["ganho"].map(fmt))
    fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
    fig.update_layout(height=400, yaxis=dict(visible=False, range=[0, longo["ganho"].max() * 1.2]),
                      xaxis=dict(title="% de eleitores com superior completo no grupo", tickangle=0),
                      legend=dict(orientation="h", y=1.08, title=""),
                      margin=dict(l=0, r=0, t=30, b=10))
    grafico(fig, key="ganho_grupos")
    maior = g["ganho_lula"].idxmax()
    como_ler(f"Lula ganhou mais votos no grupo **{nomes_grupo[maior].lower()}** "
             f"(+{fmt(g.loc[maior, 'ganho_lula'])}).")

# ---------------------------------------------------------------------------
# 4) Estimativa do voto dentro de cada faixa
# ---------------------------------------------------------------------------
st.divider()
st.subheader("4. Estimativa: como votou cada faixa de escolaridade")
if len(d) < 30:
    st.warning("Poucos municípios neste recorte: a estimativa fica instável. Prefira uma região inteira.")

est = voto_por_escolaridade(mun[mun["uf"] != "ZZ"], perfil)
est["Lula 1º"] = est["t1_Lula"] / (est["t1_Lula"] + est["t1_Flávio"] + est["t1_Demais"]) * 100
est["Lula 2º"] = est["t2_Lula"] / (est["t2_Lula"] + est["t2_Flávio"]) * 100
est["crescimento"] = est["Lula 2º"] - est["Lula 1º"]
est["votos_novos"] = (est["t2_Lula"] - est["t1_Lula"]) * est["eleitores"]
ordem = list(FAIXAS_MODELO)[::-1]

c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown("**Quanto Lula cresceu em cada faixa** (pontos percentuais nos votos válidos)")
    s = est["crescimento"].reindex(ordem)
    fig = px.bar(x=s.values, y=s.index, orientation="h", color=s.index,
                 color_discrete_map=CORES_ESCOLARIDADE, text=[f"+{v:.0f} p.p." for v in s.values])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=200, showlegend=False, yaxis_title="", bargap=0.45,
                      xaxis=dict(visible=False, range=[min(0, s.min() * 1.3), max(s.max(), 1) * 1.35]),
                      margin=dict(l=0, r=0, t=10, b=10))
    grafico(fig, key="est_cresc")
with c2:
    st.markdown("**Votos novos de Lula, por faixa**")
    s = est["votos_novos"].reindex(ordem)
    fig = px.bar(x=s.values, y=s.index, orientation="h", color=s.index,
                 color_discrete_map=CORES_ESCOLARIDADE, text=[fmt(v) for v in s.values])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=200, showlegend=False, yaxis_title="", bargap=0.45,
                      xaxis=dict(visible=False, range=[min(0, s.min() * 1.3), max(s.max(), 1) * 1.35]),
                      margin=dict(l=0, r=0, t=10, b=10))
    grafico(fig, key="est_novos")
como_ler("o modelo estima, a partir de todos os municípios do recorte, quanto cada faixa mudou o voto "
         "entre os turnos. Votos novos = eleitores da faixa × aumento da parcela que votou em Lula.")

with st.expander("Como essa estimativa é feita (e seus limites)"):
    st.markdown("""
O voto é secreto, e o TSE não informa a escolaridade de quem votou em cada candidato. O modelo usa a
mesma **inferência ecológica** da página de comparação: cruza a escolaridade do eleitorado de cada
município com o resultado do município e encontra as proporções de voto por faixa (entre 0% e 100%)
que melhor explicam todos os municípios ao mesmo tempo.

- Usa só **2 faixas** (até fundamental x médio ou mais). Com mais faixas, elas variam juntas entre
  os municípios e o modelo não consegue separá-las.
- Mostra o **crescimento** entre os turnos, que é estável. O nível de voto de cada faixa
  (quanto % votou em Lula) depende muito das suposições do modelo e por isso não é exibido.
- Supõe que eleitores da mesma faixa votam de forma parecida em todo o recorte. Filtrar por região
  costuma dar resultados mais confiáveis.
- A escolaridade do cadastro do TSE é declarada pelo eleitor e pode estar desatualizada.
- Use os números como **ordem de grandeza**. A seção 3, que só agrupa municípios, não depende de modelo.
""")
