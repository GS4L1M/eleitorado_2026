"""
Funções e constantes compartilhadas pelas páginas do dashboard.

Carrega os resumos gerados pelo preparar_dados.py, monta a tabela por município,
estima a transferência de votos e desenha os mapas.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy.optimize import minimize

DADOS = Path(__file__).resolve().parent / "dados"

# ---------------------------------------------------------------------------
# 1) Cores e grupos
# ---------------------------------------------------------------------------
VERMELHO = "#C8102E"    # Lula
AZUL = "#1F5AA6"        # Flávio
CINZA = "#9AA0A6"

# Agrupa os candidatos do 1º turno; quem não está aqui entra em "Outros"
GRUPOS = {13: "Lula", 22: "Flávio", 70: "Augusto Cury", 14: "Renan Santos",
          55: "Ronaldo Caiado", 95: "Branco/Nulo", 96: "Branco/Nulo"}
CANDIDATOS_T1 = ["Flávio", "Lula", "Augusto Cury", "Renan Santos", "Ronaldo Caiado", "Outros"]
ELIMINADOS = CANDIDATOS_T1[2:]
ORIGENS = ["Lula", "Flávio"] + ELIMINADOS + ["Branco/Nulo", "Abstenção"]
DESTINOS = ["Lula", "Flávio", "Branco/Nulo", "Abstenção"]
CORES = {"Lula": VERMELHO, "Flávio": AZUL, "Augusto Cury": "#E8A33D", "Renan Santos": "#6B4C9A",
         "Ronaldo Caiado": "#2E8B57", "Outros": "#B0B0B0", "Branco/Nulo": "#707070",
         "Abstenção": "#C9C9C9", "Demais candidatos": "#E8A33D"}
REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
# Cores das regiões longe do azul e do vermelho, para não confundir com os candidatos
CORES_REGIAO = {"Norte": "#2E8B57", "Nordeste": "#E8A33D", "Centro-Oeste": "#8E6BBF",
                "Sudeste": "#17A2B8", "Sul": "#8C564B"}


# ---------------------------------------------------------------------------
# 2) Carga dos dados
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
def tabela_municipios() -> pd.DataFrame:
    """Uma linha por município, com os grupos do 1º turno (t1_*) e do 2º (t2_*)."""
    votos, comp, _ = carregar()
    chaves = ["cd_tse", "cd_ibge", "uf", "regiao", "municipio"]
    votos = votos.assign(cd_ibge=votos["cd_ibge"].fillna(""))   # exterior não tem código IBGE
    largo = votos.pivot_table(index=chaves, columns=["turno", "grupo"], values="votos",
                              aggfunc="sum", fill_value=0)
    largo.columns = [f"t{t}_{g}" for t, g in largo.columns]
    largo = largo.reset_index()
    aptos = comp[comp["turno"] == 1].groupby("cd_tse")["aptos"].sum()
    largo["aptos"] = largo["cd_tse"].map(aptos)
    largo = largo.dropna(subset=["aptos"])
    for col in [f"t{t}_{g}" for t in (1, 2) for g in ORIGENS]:
        if col not in largo:
            largo[col] = 0
    # Abstenção = aptos que não aparecem em nenhum voto, para a conta fechar
    for t in (1, 2):
        cols = [f"t{t}_{g}" for g in ORIGENS if g != "Abstenção"]
        largo[f"t{t}_Abstenção"] = (largo["aptos"] - largo[cols].sum(axis=1)).clip(lower=0)
    largo["t1_validos"] = largo[[f"t1_{g}" for g in CANDIDATOS_T1]].sum(axis=1)
    largo["t2_validos"] = largo["t2_Lula"] + largo["t2_Flávio"]
    return largo


# ---------------------------------------------------------------------------
# 3) Filtro de região/estado (os widgets ficam no app.py, valem para todas as páginas)
# ---------------------------------------------------------------------------
def recorte():
    mun = tabela_municipios()
    regiao = st.session_state.get("regiao", "Brasil")
    uf = st.session_state.get("uf", "Todos")
    if regiao != "Brasil":
        mun = mun[mun["regiao"] == regiao]
    if uf != "Todos":
        mun = mun[mun["uf"] == uf]
    return mun, (uf if uf != "Todos" else regiao)


# ---------------------------------------------------------------------------
# 4) Inferência ecológica
#    Para cada município i:  resultado[i, k] ≈ Σ_j grupo[i, j] · P[j, k]
#    com P >= 0 e cada linha de P somando 1. Estimada por mínimos quadrados
#    ponderados pelo tamanho do município.
# ---------------------------------------------------------------------------
def ajustar_proporcoes(grupos: np.ndarray, resultado: np.ndarray) -> np.ndarray:
    """P[j, k] = parcela do grupo j que terminou no resultado k (cada linha soma 1).

    grupos e resultado são contagens por município; cada um é convertido em proporção
    do próprio total, para que fontes diferentes (perfil x votação) possam ser comparadas.
    """
    total = grupos.sum(axis=1)
    total_res = resultado.sum(axis=1)
    ok = (total > 0) & (total_res > 0)
    a, b, total = grupos[ok] / total[ok, None], resultado[ok] / total_res[ok, None], total[ok]
    peso = np.sqrt(total / total.mean())[:, None]
    J, K = a.shape[1], b.shape[1]

    def erro(p):
        return (((a @ p.reshape(J, K) - b) * peso) ** 2).sum()

    restricoes = [{"type": "eq", "fun": lambda p, j=j: p.reshape(J, K)[j].sum() - 1}
                  for j in range(J)]
    r = minimize(erro, np.full(J * K, 1 / K), bounds=[(0, 1)] * (J * K),
                 constraints=restricoes, method="SLSQP",
                 options={"maxiter": 1000, "ftol": 1e-12})
    return r.x.reshape(J, K)


@st.cache_data
def matriz_transferencia(mun: pd.DataFrame) -> pd.DataFrame:
    """Para onde foi, no 2º turno, cada grupo de eleitores do 1º."""
    P = ajustar_proporcoes(mun[[f"t1_{g}" for g in ORIGENS]].to_numpy(float),
                           mun[[f"t2_{g}" for g in DESTINOS]].to_numpy(float))
    return pd.DataFrame(P, index=ORIGENS, columns=DESTINOS)


# ---------------------------------------------------------------------------
# 4b) Escolaridade
# ---------------------------------------------------------------------------
NIVEIS_ESCOLARIDADE = {
    "esc_analfabeto": "Analfabeto",
    "esc_le_escreve": "Lê e escreve",
    "esc_fund_incompleto": "Fundamental incompleto",
    "esc_fund_completo": "Fundamental completo",
    "esc_medio_incompleto": "Médio incompleto",
    "esc_medio_completo": "Médio completo",
    "esc_sup_incompleto": "Superior incompleto",
    "esc_sup_completo": "Superior completo",
}
# Os 8 níveis agrupados em 4 faixas, para os gráficos ficarem legíveis
FAIXAS_ESCOLARIDADE = {
    "Sem fundamental completo": ["esc_analfabeto", "esc_le_escreve", "esc_fund_incompleto"],
    "Fundamental completo": ["esc_fund_completo", "esc_medio_incompleto"],
    "Médio completo": ["esc_medio_completo", "esc_sup_incompleto"],
    "Superior completo": ["esc_sup_completo"],
}
# Escala de roxo: longe do azul e do vermelho dos candidatos
CORES_ESCOLARIDADE = dict(zip(FAIXAS_ESCOLARIDADE, ["#D9CCEB", "#AE93D4", "#7A55B0", "#45267A"]))
# O modelo usa só 2 faixas: com 4, elas variam juntas entre os municípios e a
# estimativa cai em extremos (0% ou 100%) sem sentido
FAIXAS_MODELO = {
    "Até ensino fundamental": FAIXAS_ESCOLARIDADE["Sem fundamental completo"]
                              + FAIXAS_ESCOLARIDADE["Fundamental completo"],
    "Ensino médio ou mais": FAIXAS_ESCOLARIDADE["Médio completo"]
                            + FAIXAS_ESCOLARIDADE["Superior completo"],
}
CORES_ESCOLARIDADE.update(zip(FAIXAS_MODELO, ["#AE93D4", "#45267A"]))


def tem_escolaridade(perfil) -> bool:
    return perfil is not None and all(c in perfil for c in NIVEIS_ESCOLARIDADE)


@st.cache_data
def voto_por_escolaridade(mun: pd.DataFrame, perfil: pd.DataFrame) -> pd.DataFrame:
    """Estima como votou cada faixa de escolaridade em cada turno.

    Retorna uma linha por faixa com a parcela dos eleitores que votou em Lula, Flávio,
    nos demais candidatos ou não votou validamente (branco, nulo ou abstenção).
    """
    d = mun.merge(perfil[["cd_tse"] + list(NIVEIS_ESCOLARIDADE)], on="cd_tse")
    grupos = np.column_stack([d[cols].sum(axis=1) for cols in FAIXAS_MODELO.values()])
    fora1 = d["t1_Branco/Nulo"] + d["t1_Abstenção"]
    fora2 = d["t2_Branco/Nulo"] + d["t2_Abstenção"]
    demais = d[[f"t1_{g}" for g in ELIMINADOS]].sum(axis=1)
    t1 = np.column_stack([d["t1_Lula"], d["t1_Flávio"], demais, fora1]).astype(float)
    t2 = np.column_stack([d["t2_Lula"], d["t2_Flávio"], fora2]).astype(float)
    P1 = ajustar_proporcoes(grupos.astype(float), t1)
    P2 = ajustar_proporcoes(grupos.astype(float), t2)
    res = pd.DataFrame(index=list(FAIXAS_MODELO))
    res["eleitores"] = grupos.sum(axis=0)
    for i, nome in enumerate(["Lula", "Flávio", "Demais", "Não votou"]):
        res[f"t1_{nome}"] = P1[:, i]
    for i, nome in enumerate(["Lula", "Flávio", "Não votou"]):
        res[f"t2_{nome}"] = P2[:, i]
    return res


# ---------------------------------------------------------------------------
# 5) Mapas
# ---------------------------------------------------------------------------
def _anti_horario(anel) -> bool:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(anel, anel[1:])) > 0


@st.cache_data
def malha(nivel: str):
    """Malha do IBGE com os anéis no sentido que o Plotly espera.

    O IBGE segue o padrão GeoJSON (contorno externo anti-horário), mas o mapa do Plotly
    (d3-geo) espera o contrário: sem a inversão, cada estado vira "o mundo menos o estado"
    e o mapa some.
    """
    nome = "municipios.geojson" if nivel == "Município" else "ufs.geojson"
    geo = json.loads((DADOS / nome).read_text(encoding="utf-8"))
    for f in geo["features"]:
        g = f["geometry"]
        poligonos = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for pol in poligonos:
            for i, anel in enumerate(pol):
                externo = i == 0
                if _anti_horario(anel) == externo:   # externo horário, buracos anti-horário
                    anel.reverse()
    return geo


def tabela_mapa(mun: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Agrega por estado ou mantém por município, e adiciona as colunas usadas nos mapas."""
    base = mun[mun["uf"] != "ZZ"]
    if nivel == "Estado":
        d = base.groupby(["uf", "regiao"], as_index=False).sum(numeric_only=True)
        d["local"], d["id"] = d["uf"], d["uf"]
    else:
        d = base[base["cd_ibge"] != ""].copy()
        d["local"], d["id"] = d["municipio"] + " (" + d["uf"] + ")", d["cd_ibge"]
    for g in CANDIDATOS_T1:
        d[f"pct1_{g}"] = d[f"t1_{g}"] / d["t1_validos"] * 100
    d["pct1_Demais"] = d[[f"pct1_{g}" for g in ELIMINADOS]].sum(axis=1)
    d["pct2_Lula"] = d["t2_Lula"] / d["t2_validos"] * 100
    d["pct2_Flávio"] = 100 - d["pct2_Lula"]
    d["margem1"] = d["pct1_Lula"] - d["pct1_Flávio"]
    d["margem2"] = d["pct2_Lula"] - d["pct2_Flávio"]
    d["vencedor1"] = d[[f"t1_{g}" for g in CANDIDATOS_T1[:5]]].idxmax(axis=1).str[3:]
    d["vencedor2"] = np.where(d["t2_Lula"] >= d["t2_Flávio"], "Lula", "Flávio")
    d["ganho_lula_pct"] = (d["t2_Lula"] - d["t1_Lula"]) / d["aptos"] * 100
    return d


def mapa(d: pd.DataFrame, nivel: str, altura: int = 520, **kwargs):
    """Mapa coroplético (SVG, sem depender de WebGL), enquadrado nas áreas presentes em d."""
    fig = px.choropleth(
        d, geojson=malha(nivel), locations="id",
        featureidkey="properties." + ("codarea" if nivel == "Município" else "uf"),
        hover_name="local", **kwargs)
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator",
                    bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_width=0.1 if nivel == "Município" else 0.8,
                      marker_line_color="white")
    fig.update_layout(height=altura, margin=dict(l=0, r=0, t=0, b=0),
                      legend=dict(orientation="h", y=-0.02, title=""))
    return fig


def grafico(fig, **kwargs) -> None:
    """Mostra o gráfico com números no padrão brasileiro (vírgula decimal, ponto no milhar)."""
    fig.update_layout(separators=",.", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", **kwargs)


# ---------------------------------------------------------------------------
# 6) Formatação
# ---------------------------------------------------------------------------
def fmt(n: float) -> str:
    """12.345.678 -> '12,35 mi'"""
    if abs(n) < 1e6:
        return f"{n / 1e3:,.0f} mil".replace(",", ".")
    return f"{n / 1e6:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(n: float, casas: int = 1) -> str:
    return f"{n:.{casas}f}%".replace(".", ",")


def transparente(hex_cor: str, alfa: float = 0.35) -> str:
    r, g, b = (int(hex_cor[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def como_ler(texto: str) -> None:
    st.caption(f"**Como ler:** {texto}")
