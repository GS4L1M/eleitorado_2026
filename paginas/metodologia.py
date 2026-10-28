import pandas as pd
import streamlit as st

from analise import carregar, fmt, tabela_municipios

st.title("Metodologia e dados")
st.markdown("A análise segue as etapas de um pipeline de dados, da coleta à conclusão.")

etapas = [
    ("1. Pergunta", "De onde vieram os votos que Lula ganhou entre o 1º e o 2º turno?"),
    ("2. Coleta", "Download automático dos dados abertos do TSE e das malhas do IBGE "
                  "(`preparar_dados.py`)."),
    ("3. Tratamento", "Leitura em pedaços dos arquivos grandes e agregação por município, "
                      "turno e candidato. Código TSE convertido para código IBGE para o mapa."),
    ("4. Validação", "Conferência de totais e de consistência entre as fontes (tabela abaixo)."),
    ("5. Exploração", "Resultados de cada turno por candidato, região, estado e município "
                      "(páginas 1º e 2º turno)."),
    ("6. Modelagem", "Matriz de transferência de votos e mudança de voto por faixa de "
                     "escolaridade, estimadas por inferência ecológica (páginas Comparação e "
                     "Escolaridade)."),
    ("7. Conclusão", "Fontes dos votos novos de Lula, regiões e perfis onde ele mais cresceu."),
]
for titulo, texto in etapas:
    st.markdown(f"**{titulo}** · {texto}")

# ---------------------------------------------------------------------------
st.divider()
st.subheader("Fontes")
st.markdown("""
| Dado | Arquivo | Uso |
|---|---|---|
| Votação por seção (presidente) | TSE · `votacao_secao_2026_BR.zip` | Votos de cada candidato, por município e turno |
| Detalhe da votação | TSE · `detalhe_votacao_munzona_2026.zip` | Eleitores aptos, comparecimento e abstenção |
| Perfil do eleitorado por seção | TSE · `perfil_eleitor_secao_2026_<UF>.zip` | Gênero, idade e escolaridade por município |
| Malhas territoriais | IBGE · API de malhas v3 | Contornos de estados e municípios |
| Códigos TSE ↔ IBGE | [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE) | Ligar os votos ao mapa |
""")

# ---------------------------------------------------------------------------
st.divider()
st.subheader("Validações")
votos, comp, perfil = carregar()
mun = tabela_municipios()
tot_votos = votos.groupby("turno")["votos"].sum()
tot_comp = comp.groupby("turno")[["aptos", "comparecimento"]].sum()
sem_ibge = mun.loc[(mun["cd_ibge"] == "") & (mun["uf"] != "ZZ"), "municipio"].tolist()

checagens = [
    ("Eleitores aptos iguais nos dois turnos",
     tot_comp.loc[1, "aptos"] == tot_comp.loc[2, "aptos"], f"{fmt(tot_comp.loc[1, 'aptos'])}"),
    ("Votos somados = comparecimento (1º turno)",
     abs(tot_votos[1] - tot_comp.loc[1, "comparecimento"]) / tot_votos[1] < 0.001,
     f"{fmt(tot_votos[1])} votos x {fmt(tot_comp.loc[1, 'comparecimento'])} comparecimentos"),
    ("Votos somados = comparecimento (2º turno)",
     abs(tot_votos[2] - tot_comp.loc[2, "comparecimento"]) / tot_votos[2] < 0.001,
     f"{fmt(tot_votos[2])} votos x {fmt(tot_comp.loc[2, 'comparecimento'])} comparecimentos"),
    ("Municípios com votos",
     len(mun[mun["uf"] != "ZZ"]) >= 5570, f"{len(mun[mun['uf'] != 'ZZ']):,}".replace(",", ".")),
    ("Municípios sem código IBGE (ficam fora do mapa)",
     len(sem_ibge) <= 1, ", ".join(sem_ibge) or "nenhum"),
]
if perfil is not None:
    checagens.append(("Eleitores no perfil x aptos na votação",
                      abs(perfil["eleitores"].sum() / tot_comp.loc[1, "aptos"] - 1) < 0.01,
                      f"{fmt(perfil['eleitores'].sum())} x {fmt(tot_comp.loc[1, 'aptos'])} "
                      "(o perfil não inclui o exterior)"))
st.dataframe(pd.DataFrame([{"Checagem": c, "OK": "✅" if ok else "⚠️", "Detalhe": d}
                           for c, ok, d in checagens]), width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
st.divider()
st.subheader("Limites da análise")
st.markdown("""
- **Inferência ecológica**: a transferência de votos é estimada a partir de resultados por
  município, não de eleitores individuais. Os números são ordem de grandeza.
- **Correlação não é causa**: a relação entre perfil do eleitorado e crescimento de Lula
  mostra associação, não explica por que alguém mudou o voto.
- **Exterior**: os votos no exterior entram nos totais do Brasil, mas não no mapa nem na
  análise de perfil.
""")
