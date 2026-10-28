import pandas as pd
import plotly.express as px
import streamlit as st

from analise import (CORES_ESCOLARIDADE, CORES_IDADE, FAIXAS_ESCOLARIDADE, FAIXAS_IDADE, carregar,
                     como_ler, fmt, fmt_pct, grafico, perfil_por_uf, tem_perfil_completo)

# Cores para comparar estados: longe do azul e do vermelho dos candidatos
CORES_ESTADOS = ["#17A2B8", "#E8A33D", "#8E6BBF", "#2E8B57", "#8C564B"]
IDADES = list(FAIXAS_IDADE.values())
ESCOLARIDADES = list(FAIXAS_ESCOLARIDADE)


def quebra(texto: str) -> str:
    """'Sem fundamental completo' -> 'Sem fundamental<br>completo', para caber no eixo."""
    return "<br>".join(texto.rsplit(" ", 1)) if " " in texto and len(texto) > 10 else texto

_, _, perfil = carregar()
st.title("Perfil do eleitorado")
st.markdown("#### Quem é o eleitor de cada estado: idade e escolaridade")
st.caption("Esta página **descreve** o eleitorado. Ela não mostra em quem cada grupo votou, "
           "porque o voto é secreto. Os votos aparecem só como contexto de cada estado.")

if not tem_perfil_completo(perfil):
    st.info("Rode `python preparar_dados.py --perfil` para gerar os dados de idade e escolaridade.")
    st.stop()

todos = perfil_por_uf()
regiao = st.session_state.get("regiao", "Brasil")
uf_filtro = st.session_state.get("uf", "Todos")
ufs = todos if regiao == "Brasil" else todos[todos["regiao"] == regiao]
nome = "Brasil" if regiao == "Brasil" else regiao
if uf_filtro != "Todos":
    nome = uf_filtro


def resumo(df: pd.DataFrame) -> pd.Series:
    """Soma estados e recalcula os percentuais."""
    s = df[["eleitores", "mulheres", *ESCOLARIDADES, *IDADES]].sum()
    out = pd.Series(dtype=float)
    out["eleitores"] = s["eleitores"]
    out["% mulheres"] = s["mulheres"] / s["eleitores"] * 100
    for f in IDADES:
        out[f] = s[f] / s[IDADES].sum() * 100
    for f in ESCOLARIDADES:
        out[f] = s[f] / s[ESCOLARIDADES].sum() * 100
    return out


r = resumo(todos.loc[[uf_filtro]] if uf_filtro != "Todos" else ufs)
br = resumo(todos)

# ---------------------------------------------------------------------------
# 1) Resumo
# ---------------------------------------------------------------------------
st.divider()
st.subheader(f"Resumo · {nome}")
c = st.columns(5)
c[0].metric("Eleitores", fmt(r["eleitores"]))
c[1].metric("Mulheres", fmt_pct(r["% mulheres"]))
c[2].metric("Até 24 anos", fmt_pct(r["16 e 17"] + r["18 a 24"]))
c[3].metric("60 anos ou mais", fmt_pct(r["60 a 69"] + r["70 ou mais"]))
c[4].metric("Superior completo", fmt_pct(r["Superior completo"]))


def barras_recorte(cats: list, cor: str, chave: str):
    """Distribuição do recorte comparada com o Brasil."""
    df = pd.DataFrame({"faixa": cats, nome: [r[f] for f in cats], "Brasil": [br[f] for f in cats]})
    longo = df.melt(id_vars="faixa", var_name="local", value_name="pct")
    if nome == "Brasil":
        longo = longo[longo["local"] == "Brasil"].drop_duplicates()
    longo["faixa"] = longo["faixa"].map(quebra)
    fig = px.bar(longo, x="faixa", y="pct", color="local", barmode="group",
                 color_discrete_map={nome: cor, "Brasil": cor if nome == "Brasil" else "#B0B0B0"},
                 text=longo["pct"].map(lambda v: f"{v:.0f}%"),
                 category_orders={"faixa": [quebra(c) for c in cats], "local": [nome, "Brasil"]})
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=340, yaxis=dict(visible=False, range=[0, longo["pct"].max() * 1.2]),
                      xaxis=dict(title="", tickangle=0), showlegend=nome != "Brasil",
                      legend=dict(orientation="h", y=1.1, title=""),
                      margin=dict(l=0, r=0, t=30, b=10))
    grafico(fig, key=chave)


def barras_estados(cats: list, cores: dict, ordenar_por: str, chave: str):
    """Uma barra de 100% por estado, ordenada pelo indicador escolhido."""
    df = ufs.sort_values(ordenar_por)
    longo = df[[f"% {f}" for f in cats]].rename(columns=lambda c: c[2:]).reset_index(names="uf") \
        .melt(id_vars="uf", var_name="faixa", value_name="pct")
    fig = px.bar(longo, x="pct", y="uf", color="faixa", orientation="h",
                 color_discrete_map=cores, category_orders={"uf": list(df.index), "faixa": cats},
                 text=longo["pct"].map(lambda v: f"{v:.0f}" if v >= 9 else ""),
                 hover_data={"pct": ":.1f"})
    fig.update_traces(textposition="inside", insidetextanchor="middle", textangle=0, textfont_size=10)
    fig.update_layout(height=max(220, 24 * len(df) + 80), xaxis=dict(visible=False, range=[0, 100]),
                      yaxis_title="", legend=dict(orientation="h", y=1.02, yanchor="bottom", title=""),
                      margin=dict(l=0, r=0, t=10, b=10), bargap=0.25)
    grafico(fig, key=chave)


# ---------------------------------------------------------------------------
# 2) Idade
# ---------------------------------------------------------------------------
st.divider()
st.subheader("1. Faixa etária")
c1, c2 = st.columns([2, 3], gap="large")
with c1:
    st.markdown(f"**Eleitores por idade · {nome}**" + (" x Brasil" if nome != "Brasil" else ""))
    barras_recorte(IDADES, "#22867A", "idade_recorte")
    como_ler("percentual dos eleitores em cada faixa de idade.")
with c2:
    st.markdown("**Faixa etária por estado** (do mais jovem para o mais velho)")
    barras_estados(IDADES, CORES_IDADE, "% 60 ou mais", "idade_ufs")
    como_ler("cada barra soma 100% dos eleitores do estado. No topo, os estados com menos "
             "eleitores de 60 anos ou mais; embaixo, os de eleitorado mais velho.")

# ---------------------------------------------------------------------------
# 3) Escolaridade
# ---------------------------------------------------------------------------
st.divider()
st.subheader("2. Escolaridade")
c1, c2 = st.columns([2, 3], gap="large")
with c1:
    st.markdown(f"**Eleitores por escolaridade · {nome}**" + (" x Brasil" if nome != "Brasil" else ""))
    barras_recorte(ESCOLARIDADES, "#7A55B0", "esc_recorte")
    como_ler("escolaridade declarada pelo eleitor no cadastro do TSE.")
with c2:
    st.markdown("**Escolaridade por estado** (do menos para o mais escolarizado)")
    barras_estados(ESCOLARIDADES, CORES_ESCOLARIDADE, "% Superior completo", "esc_ufs")
    como_ler("cada barra soma 100% dos eleitores do estado. No topo, os estados com menos "
             "eleitores com superior completo; embaixo, os com mais.")

# ---------------------------------------------------------------------------
# 4) Comparar estados
# ---------------------------------------------------------------------------
st.divider()
st.subheader("3. Compare estados")
padrao = [uf_filtro] if uf_filtro != "Todos" else list(ufs.sort_values("eleitores").index[-3:][::-1])
escolha = st.multiselect("Escolha até 5 estados", list(todos.index), default=padrao,
                         max_selections=5, key="ufs_comparar")
if escolha:
    cores = dict(zip(escolha, CORES_ESTADOS))
    sel = todos.loc[escolha]

    c1, c2 = st.columns(2, gap="large")
    for col, cats, titulo, chave in [(c1, IDADES, "Faixa etária", "cmp_idade"),
                                     (c2, ESCOLARIDADES, "Escolaridade", "cmp_esc")]:
        with col:
            st.markdown(f"**{titulo}**")
            longo = sel[[f"% {f}" for f in cats]].rename(columns=lambda c: c[2:]) \
                .reset_index(names="uf").melt(id_vars="uf", var_name="faixa", value_name="pct")
            longo["faixa"] = longo["faixa"].map(quebra)
            fig = px.bar(longo, x="faixa", y="pct", color="uf", barmode="group",
                         color_discrete_map=cores,
                         category_orders={"faixa": [quebra(c) for c in cats], "uf": escolha},
                         hover_data={"pct": ":.1f"})
            fig.update_layout(height=340, yaxis=dict(title="% dos eleitores"),
                              xaxis=dict(title="", tickangle=0),
                              legend=dict(orientation="h", y=1.1, title=""),
                              margin=dict(l=0, r=0, t=30, b=10))
            grafico(fig, key=chave)

    st.markdown("**Eleitores e votos de cada estado**")
    tabela = pd.DataFrame({
        "Estado": escolha,
        "Eleitores": sel["eleitores"].values,
        "Lula · 1º turno": sel["t1_Lula"].values,
        "Flávio · 1º turno": sel["t1_Flávio"].values,
        "Lula · 2º turno": sel["t2_Lula"].values,
        "Flávio · 2º turno": sel["t2_Flávio"].values,
        "% Lula · 2º turno": sel["% Lula 2º"].values,
        "Venceu no 2º turno": sel["vencedor"].values,
    })
    st.dataframe(
        tabela, hide_index=True, width="stretch",
        column_config={
            **{c: st.column_config.NumberColumn(c, format="localized")
               for c in tabela.columns[1:6]},
            "% Lula · 2º turno": st.column_config.NumberColumn("% Lula · 2º turno", format="%.1f%%"),
        })

# ---------------------------------------------------------------------------
# 5) Tabela de todos os estados
# ---------------------------------------------------------------------------
st.divider()
st.subheader("4. Todos os estados")
st.caption("Clique no nome de uma coluna para ordenar.")
geral = pd.DataFrame({
    "UF": ufs.index,
    "Região": ufs["regiao"].values,
    "Eleitores": ufs["eleitores"].values,
    "% mulheres": ufs["% mulheres"].values,
    "% até 24 anos": ufs["% até 24 anos"].values,
    "% 60 anos ou mais": ufs["% 60 ou mais"].values,
    "% sem fundamental completo": ufs["% Sem fundamental completo"].values,
    "% superior completo": ufs["% Superior completo"].values,
    "Votos Lula · 2º": ufs["t2_Lula"].values,
    "Votos Flávio · 2º": ufs["t2_Flávio"].values,
    "Venceu": ufs["vencedor"].values,
}).sort_values("Eleitores", ascending=False)
pct = {c: st.column_config.NumberColumn(c, format="%.1f%%") for c in geral.columns if c.startswith("%")}
st.dataframe(geral, hide_index=True, width="stretch", height=min(40 + 35 * len(geral), 990),
             column_config={**pct, **{c: st.column_config.NumberColumn(c, format="localized")
                                      for c in ["Eleitores", "Votos Lula · 2º", "Votos Flávio · 2º"]}})
