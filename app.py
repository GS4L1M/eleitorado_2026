"""
Dashboard: de onde vieram os votos de Lula entre o 1º e o 2º turno de 2026.

Antes de rodar, gere os dados com:  python preparar_dados.py  (ou --perfil)
Uso:  python -m streamlit run app.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.optimize import minimize

DADOS = Path(__file__).resolve().parent / "dados"

VERMELHO = "#C8102E"    # Lula
AZUL = "#1F5AA6"        # Flávio
CINZA = "#9AA0A6"

# Agrupa os candidatos do 1º turno; quem não está aqui entra em "Outros"
GRUPOS = {13: "Lula", 22: "Flávio", 70: "Augusto Cury", 14: "Renan Santos",
          55: "Ronaldo Caiado", 95: "Branco/Nulo", 96: "Branco/Nulo"}
ORIGENS = ["Lula", "Flávio", "Augusto Cury", "Renan Santos", "Ronaldo Caiado",
           "Outros", "Branco/Nulo", "Abstenção"]
DESTINOS = ["Lula", "Flávio", "Branco/Nulo", "Abstenção"]
CORES = {"Lula": VERMELHO, "Flávio": AZUL, "Augusto Cury": "#E8A33D", "Renan Santos": "#6B4C9A",
         "Ronaldo Caiado": "#2E8B57", "Outros": "#B0B0B0", "Branco/Nulo": "#707070",
         "Abstenção": "#D0D0D0"}

st.set_page_config(page_title="Eleições 2026 · Votos de Lula", page_icon="🗳️", layout="wide")


# ---------------------------------------------------------------------------
# 1) Carga dos dados (feita uma vez e guardada em cache)
# ---------------------------------------------------------------------------
@st.cache_data
def carregar():
    votos = pd.read_parquet(DADOS / "votos_municipio.parquet")
    votos["grupo"] = votos["nr_votavel"].map(GRUPOS).fillna("Outros")
    comp = pd.read_parquet(DADOS / "comparecimento_municipio.parquet")
    perfil_path = DADOS / "perfil_municipio.parquet"
    perfil = pd.read_parquet(perfil_path) if perfil_path.exists() else None
    return votos, comp, perfil


@st.cache_data
def carregar_malha(nivel: str):
    nome = "municipios.geojson" if nivel == "Município" else "ufs.geojson"
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


@st.cache_data
def tabela_municipios(votos: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por município, com os grupos do 1º turno (t1_*) e do 2º (t2_*)."""
    chaves = ["cd_tse", "cd_ibge", "uf", "regiao", "municipio"]
    votos = votos.assign(cd_ibge=votos["cd_ibge"].fillna(""))   # exterior não tem código IBGE
    largo = votos.pivot_table(index=chaves, columns=["turno", "grupo"], values="votos",
                              aggfunc="sum", fill_value=0)
    largo.columns = [f"t{t}_{g}" for t, g in largo.columns]
    largo = largo.reset_index()
    aptos = comp[comp["turno"] == 1].groupby("cd_tse")["aptos"].sum()
    largo["aptos"] = largo["cd_tse"].map(aptos)
    largo = largo.dropna(subset=["aptos"])
    # Abstenção = aptos que não aparecem em nenhum voto, para a conta fechar
    for t in (1, 2):
        cols = [c for c in largo.columns if c.startswith(f"t{t}_")]
        largo[f"t{t}_Abstenção"] = (largo["aptos"] - largo[cols].sum(axis=1)).clip(lower=0)
    for col in [f"t{t}_{g}" for t in (1, 2) for g in ORIGENS]:
        if col not in largo:
            largo[col] = 0
    return largo


# ---------------------------------------------------------------------------
# 2) Matriz de transferência de votos (inferência ecológica)
#    Para cada município i:  2º turno[i, k] ≈ Σ_j 1º turno[i, j] · P[j, k]
#    com P >= 0 e cada linha de P somando 1. Estimada por mínimos quadrados
#    ponderados pelo tamanho do município.
# ---------------------------------------------------------------------------
@st.cache_data
def matriz_transferencia(mun: pd.DataFrame) -> pd.DataFrame:
    a = mun[[f"t1_{g}" for g in ORIGENS]].to_numpy(float)
    b = mun[[f"t2_{g}" for g in DESTINOS]].to_numpy(float)
    total = a.sum(axis=1)
    ok = total > 0
    a, b, total = a[ok] / total[ok, None], b[ok] / total[ok, None], total[ok]
    peso = np.sqrt(total / total.mean())[:, None]
    J, K = len(ORIGENS), len(DESTINOS)

    def erro(p):
        return (((a @ p.reshape(J, K) - b) * peso) ** 2).sum()

    restricoes = [{"type": "eq", "fun": lambda p, j=j: p.reshape(J, K)[j].sum() - 1}
                  for j in range(J)]
    r = minimize(erro, np.full(J * K, 1 / K), bounds=[(0, 1)] * (J * K),
                 constraints=restricoes, method="SLSQP",
                 options={"maxiter": 1000, "ftol": 1e-12})
    return pd.DataFrame(r.x.reshape(J, K), index=ORIGENS, columns=DESTINOS)


def fmt(n: float) -> str:
    return f"{n / 1e6:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")


def transparente(hex_cor: str, alfa: float = 0.35) -> str:
    r, g, b = (int(hex_cor[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def fmt_pct(n: float) -> str:
    return f"{n:.1f}%".replace(".", ",")


# ---------------------------------------------------------------------------
# 3) Filtros
# ---------------------------------------------------------------------------
votos, comp, perfil = carregar()
mun_br = tabela_municipios(votos, comp)

st.sidebar.title("Filtros")
regioes = ["Brasil", "Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
regiao = st.sidebar.selectbox("Região", regioes)
mun = mun_br if regiao == "Brasil" else mun_br[mun_br["regiao"] == regiao]
ufs = sorted(mun["uf"].unique())
uf = st.sidebar.selectbox("Estado", ["Todos"] + ufs)
if uf != "Todos":
    mun = mun[mun["uf"] == uf]
recorte = regiao if uf == "Todos" else uf
st.sidebar.caption("O exterior (ZZ) entra nos totais do Brasil, mas não no mapa.")

# ---------------------------------------------------------------------------
# 4) Cabeçalho e KPIs
# ---------------------------------------------------------------------------
st.title("De onde vieram os votos de Lula no 2º turno?")
st.caption(f"Eleição presidencial 2026 · Fonte: TSE (votação por seção) · Recorte: **{recorte}**")

s = mun.sum(numeric_only=True)
ganho_lula = s["t2_Lula"] - s["t1_Lula"]
ganho_flavio = s["t2_Flávio"] - s["t1_Flávio"]
validos1 = s["t1_Lula"] + s["t1_Flávio"] + sum(s[f"t1_{g}"] for g in ORIGENS[2:6])
validos2 = s["t2_Lula"] + s["t2_Flávio"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Lula · 2º turno", fmt(s["t2_Lula"]), f"+{fmt(ganho_lula)} vs 1º turno")
c2.metric("Flávio · 2º turno", fmt(s["t2_Flávio"]), f"+{fmt(ganho_flavio)} vs 1º turno")
c3.metric("Votos dos eliminados no 1º turno", fmt(sum(s[f"t1_{g}"] for g in ORIGENS[2:6])))
c4.metric("Abstenção · 2º turno", fmt(s["t2_Abstenção"]),
          f"{fmt(s['t2_Abstenção'] - s['t1_Abstenção'])}", delta_color="inverse")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Lula · % válidos", fmt_pct(s["t2_Lula"] / validos2 * 100),
          f"{s['t1_Lula'] / validos1 * 100:.1f}% no 1º turno".replace(".", ","), delta_color="off")
c2.metric("Flávio · % válidos", fmt_pct(s["t2_Flávio"] / validos2 * 100),
          f"{s['t1_Flávio'] / validos1 * 100:.1f}% no 1º turno".replace(".", ","), delta_color="off")
c3.metric("Brancos e nulos · 2º turno", fmt(s["t2_Branco/Nulo"]),
          f"{fmt(s['t2_Branco/Nulo'] - s['t1_Branco/Nulo'])}", delta_color="inverse")
c4.metric("Diferença Lula − Flávio · 2º turno", fmt(s["t2_Lula"] - s["t2_Flávio"]))

# ---------------------------------------------------------------------------
# 5) Transferência de votos
# ---------------------------------------------------------------------------
st.header("Para onde foi cada voto do 1º turno")
if len(mun) < 30:
    st.warning("Poucos municípios neste recorte: a estimativa de transferência fica instável. "
               "Prefira uma região inteira.")

P = matriz_transferencia(mun)
fluxo = P.mul(s[[f"t1_{g}" for g in ORIGENS]].to_numpy(), axis=0)

col_a, col_b = st.columns([3, 2])
with col_a:
    entrada = fluxo["Lula"].drop("Lula")
    fig = go.Figure(go.Waterfall(
        orientation="v",
        x=["Lula 1º turno"] + list(entrada.index) + ["Lula 2º turno (estimado)"],
        y=[fluxo.loc["Lula", "Lula"]] + list(entrada.values) + [0],
        measure=["absolute"] + ["relative"] * len(entrada) + ["total"],
        text=[fmt(fluxo.loc["Lula", "Lula"])] + [f"+{fmt(v)}" for v in entrada] + [fmt(fluxo["Lula"].sum())],
        textposition="outside",
        increasing={"marker": {"color": VERMELHO}},
        totals={"marker": {"color": VERMELHO}},
        connector={"line": {"color": CINZA}},
    ))
    fig.update_layout(title="Composição estimada do voto de Lula no 2º turno",
                      yaxis_title="votos", showlegend=False, height=460,
                      margin=dict(t=60, b=40))
    st.plotly_chart(fig, width="stretch")

with col_b:
    tabela = (P * 100).round(0).astype(int).astype(str) + "%"
    tabela.index.name = "1º turno →"
    st.markdown("**Matriz de transferência estimada** (cada linha soma 100%)")
    st.dataframe(tabela, width="stretch")
    st.caption(f"Votos reais de Lula no 2º turno: **{fmt(s['t2_Lula'])}**. "
               f"Estimativa do modelo: **{fmt(fluxo['Lula'].sum())}**.")

# Sankey só com os votos em disputa: quem já votava em Lula ou Flávio e quem se
# absteve nos dois turnos ficam de fora, senão escondem as transferências
em_disputa = fluxo.loc[ORIGENS[2:]].copy()
em_disputa.loc["Abstenção", "Abstenção"] = 0
origens_s = [o for o in em_disputa.index if em_disputa.loc[o].sum() > 1000]
destinos_s = [d for d in DESTINOS if em_disputa[d].sum() > 1000]
n_orig = len(origens_s)
links = [(i, n_orig + k, em_disputa.loc[o, d])
         for i, o in enumerate(origens_s) for k, d in enumerate(destinos_s)
         if em_disputa.loc[o, d] > 1000]
rotulo_orig = {"Branco/Nulo": "Branco/Nulo", "Abstenção": "Abstenção → foi votar"}
sankey = go.Figure(go.Sankey(
    arrangement="snap",
    valueformat=",.0f",
    node=dict(
        label=[f"{rotulo_orig.get(o, o)}  {fmt(em_disputa.loc[o].sum())}" for o in origens_s]
              + [f"{d}  +{fmt(em_disputa[d].sum())}" for d in destinos_s],
        color=[CORES[o] for o in origens_s] + [CORES[d] for d in destinos_s],
        pad=22, thickness=18, line=dict(width=0),
        hovertemplate="%{label}<extra></extra>"),
    link=dict(source=[l[0] for l in links], target=[l[1] for l in links],
              value=[l[2] for l in links],
              color=[transparente(CORES[destinos_s[l[1] - n_orig]], 0.45) for l in links],
              hovertemplate="%{source.label} → %{target.label}<br>%{value:,.0f} votos<extra></extra>"),
))
sankey.update_layout(title="Para onde foram os votos em disputa (estimado)", height=520,
                     font=dict(size=14), margin=dict(t=50, b=20, l=10, r=10))
sankey.update_traces(textfont=dict(size=14, color="#222"), selector=dict(type="sankey"))
st.plotly_chart(sankey, width="stretch")
st.caption("Esquerda: eleitores dos candidatos eliminados, quem votou branco/nulo e quem se absteve "
           "no 1º turno mas votou no 2º. Direita: onde esses votos foram parar. "
           "Os eleitores que repetiram Lula ou Flávio não aparecem.")

with st.expander("Como essa estimativa é feita (e seus limites)"):
    st.markdown("""
O voto é secreto, então não dá para saber quem migrou para quem. O modelo usa **inferência
ecológica**: compara, município a município, o resultado do 1º turno com o do 2º e procura as
proporções de transferência (entre 0% e 100%, somando 100% por linha) que melhor explicam
todos os municípios ao mesmo tempo. Municípios maiores pesam mais.

- É uma **estimativa média**: ela supõe que o eleitor de Cury, por exemplo, se comporta de forma
  parecida em todo o recorte. Por isso, filtrar por região dá resultados mais confiáveis do que
  olhar o Brasil inteiro.
- Brancos, nulos e abstenção se misturam: quem anulou no 1º turno pode ter votado no 2º, e vice-versa.
- Use os números como **ordem de grandeza**, não como contagem exata.
""")

# ---------------------------------------------------------------------------
# 6) Mapa
# ---------------------------------------------------------------------------
st.header("Mapa")
m1, m2 = st.columns([2, 1])
modo = m1.radio("Mostrar", ["Margem no 2º turno", "Vencedor no 1º turno", "Vencedor no 2º turno",
                            "Crescimento de Lula entre turnos"], horizontal=True)
nivel = m2.radio("Nível", ["Estado", "Município"], horizontal=True,
                 help="O mapa por município é mais pesado para carregar.")

base = mun[mun["uf"] != "ZZ"]
if nivel == "Estado":
    dados_mapa = base.groupby("uf", as_index=False).sum(numeric_only=True)
    dados_mapa["local"] = dados_mapa["uf"]
    chave, nome = "uf", "uf"
else:
    dados_mapa = base[base["cd_ibge"] != ""].copy()
    dados_mapa["local"] = dados_mapa["municipio"] + " (" + dados_mapa["uf"] + ")"
    chave, nome = "cd_ibge", "codarea"

d = dados_mapa
d["lula_t2_pct"] = d["t2_Lula"] / (d["t2_Lula"] + d["t2_Flávio"]) * 100
d["margem"] = d["lula_t2_pct"] - (100 - d["lula_t2_pct"])
d["crescimento"] = (d["t2_Lula"] - d["t1_Lula"]) / d["aptos"] * 100
cand_t1 = ["Lula", "Flávio", "Augusto Cury", "Renan Santos", "Ronaldo Caiado"]
d["vencedor_1"] = d[[f"t1_{g}" for g in cand_t1]].idxmax(axis=1).str[3:]
d["vencedor_2"] = np.where(d["t2_Lula"] >= d["t2_Flávio"], "Lula", "Flávio")

comum = dict(geojson=carregar_malha(nivel), locations=chave, featureidkey=f"properties.{nome}",
             hover_name="local")
if modo == "Margem no 2º turno":
    lim = max(abs(d["margem"]).quantile(0.98), 1)
    fig = px.choropleth(d, color="margem", range_color=(-lim, lim),
                        color_continuous_scale=[AZUL, "#F2F2F2", VERMELHO],
                        hover_data={"margem": ":.1f", "lula_t2_pct": ":.1f", chave: False},
                        labels={"margem": "Lula − Flávio (p.p.)", "lula_t2_pct": "% Lula"}, **comum)
elif modo.startswith("Vencedor"):
    col = "vencedor_1" if "1º" in modo else "vencedor_2"
    fig = px.choropleth(d, color=col, color_discrete_map=CORES,
                        hover_data={chave: False}, labels={col: "Vencedor"}, **comum)
else:
    fig = px.choropleth(d, color="crescimento",
                        range_color=(0, d["crescimento"].quantile(0.98)),
                        color_continuous_scale=["#FFF5F0", VERMELHO],
                        hover_data={"crescimento": ":.1f", chave: False},
                        labels={"crescimento": "Lula ganhou (% dos aptos)"}, **comum)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_traces(marker_line_width=0.2 if nivel == "Município" else 0.6, marker_line_color="white")
fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, width="stretch")
st.caption("Azul = Flávio Bolsonaro · Vermelho = Lula")

# ---------------------------------------------------------------------------
# 7) Por região
# ---------------------------------------------------------------------------
st.header("Ganho de votos por região")
por_reg = mun_br[mun_br["uf"] != "ZZ"].groupby("regiao").sum(numeric_only=True)
por_reg = pd.DataFrame({
    "Lula": por_reg["t2_Lula"] - por_reg["t1_Lula"],
    "Flávio": por_reg["t2_Flávio"] - por_reg["t1_Flávio"],
}).reindex(regioes[1:])
fig = px.bar(por_reg.reset_index().melt(id_vars="regiao", var_name="candidato", value_name="ganho"),
             x="regiao", y="ganho", color="candidato", barmode="group",
             color_discrete_map=CORES, labels={"regiao": "", "ganho": "votos ganhos no 2º turno"},
             text_auto=".3s")
fig.update_layout(height=420, legend_title="")
st.plotly_chart(fig, width="stretch")

# Transferências por região: o que cada região deu a Lula
linhas = []
for reg in regioes[1:]:
    m = mun_br[mun_br["regiao"] == reg]
    Pr = matriz_transferencia(m)
    t1 = m[[f"t1_{g}" for g in ORIGENS]].sum().to_numpy()
    for origem, v in (Pr["Lula"] * t1).drop("Lula").items():
        linhas.append({"regiao": reg, "origem": origem, "votos": v})
fig = px.bar(pd.DataFrame(linhas), x="regiao", y="votos", color="origem",
             color_discrete_map=CORES, labels={"regiao": "", "votos": "votos novos de Lula (estimado)"},
             title="De onde vieram os votos novos de Lula, por região (estimado)")
fig.update_layout(height=440, legend_title="Origem (1º turno)")
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# 8) Perfil do eleitorado x crescimento de Lula
# ---------------------------------------------------------------------------
st.header("Perfil do eleitorado onde Lula mais cresceu")
if perfil is None:
    st.info("Rode `python preparar_dados.py --perfil` para habilitar esta seção.")
else:
    pm = mun.merge(perfil.drop(columns="uf"), on="cd_tse")
    pm["crescimento"] = (pm["t2_Lula"] - pm["t1_Lula"]) / pm["aptos"] * 100
    indicadores = {"pct_escolaridade_baixa": "% até fundamental incompleto",
                   "pct_superior_completo": "% com superior completo",
                   "pct_idosos_60_mais": "% com 60 anos ou mais",
                   "pct_jovens_16_24": "% de 16 a 24 anos",
                   "pct_mulheres": "% mulheres"}
    rotulo = st.selectbox("Comparar com", list(indicadores.values()))
    escolha = next(k for k, v in indicadores.items() if v == rotulo)
    corr = np.corrcoef(pm[escolha], pm["crescimento"])[0, 1]
    fig = px.scatter(pm, x=escolha, y="crescimento", size="aptos", color="regiao",
                     hover_name="municipio", size_max=30, opacity=0.6,
                     labels={escolha: indicadores[escolha], "crescimento": "Lula ganhou (% dos aptos)",
                             "regiao": "Região"})
    fig.update_layout(height=520)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Correlação entre os municípios do recorte: **{corr:.2f}** "
               "(−1 a 1; perto de 0 = sem relação).")

# ---------------------------------------------------------------------------
# 9) Municípios onde Lula mais ganhou votos
# ---------------------------------------------------------------------------
st.header("Municípios onde Lula mais ganhou votos")
top = mun.assign(ganho_lula=mun["t2_Lula"] - mun["t1_Lula"],
                 ganho_flavio=mun["t2_Flávio"] - mun["t1_Flávio"],
                 eliminados=mun[[f"t1_{g}" for g in ORIGENS[2:6]]].sum(axis=1))
top = top.nlargest(20, "ganho_lula")[["municipio", "uf", "t1_Lula", "t2_Lula", "ganho_lula",
                                       "ganho_flavio", "eliminados"]]
top.columns = ["Município", "UF", "Lula 1º", "Lula 2º", "Ganho Lula", "Ganho Flávio",
               "Votos dos eliminados (1º)"]
st.dataframe(top.style.format({c: "{:,.0f}" for c in top.columns[2:]}),
             width="stretch", hide_index=True)
