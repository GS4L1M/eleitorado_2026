# De onde vieram os votos de Lula? · Eleições 2026

Dashboard em **Streamlit** que analisa a eleição presidencial de 2026 por região e por município,
com foco em uma pergunta:

> **Lula terminou o 1º turno atrás de Flávio Bolsonaro e venceu o 2º turno. De onde vieram
> os 10 milhões de votos a mais que ele recebeu?**

| | 1º turno | 2º turno | Diferença |
|---|---:|---:|---:|
| Lula | 53,88 mi | 64,26 mi | **+10,38 mi** |
| Flávio Bolsonaro | 56,10 mi | 59,83 mi | +3,72 mi |
| Votos dos candidatos eliminados | 9,32 mi | — | |
| Brancos e nulos | 5,97 mi | 4,15 mi | −1,82 mi |
| Abstenção | 33,47 mi | 30,51 mi | −2,96 mi |

Fonte: TSE, votação por seção eleitoral.

## Por que Streamlit e não Power BI

Os CSVs do perfil do eleitorado somam cerca de 25 GB, mais do que os 5 GB do OneDrive gratuito
usado pelo Power BI web. Aqui os arquivos grandes são lidos **uma vez**, em pedaços (sem estourar
a memória RAM), e resumidos em tabelas por município de poucos MB. O dashboard só lê esse resumo.

## Etapas da análise

| Etapa | Onde |
|---|---|
| 1. Pergunta | De onde vieram os votos novos de Lula no 2º turno? |
| 2. Coleta | `preparar_dados.py` baixa os dados do TSE e do IBGE |
| 3. Tratamento | `preparar_dados.py` agrega por município, turno e candidato |
| 4. Validação | Página **Metodologia e dados** confere totais entre as fontes |
| 5. Exploração | Páginas **1º turno** e **2º turno** |
| 6. Modelagem | Página **Comparação**: matriz de transferência de votos |
| 7. Conclusão | Página **Início** resume os achados |

## Páginas do dashboard

**Azul = Flávio Bolsonaro · Vermelho = Lula.** Todas as páginas respondem aos filtros de
**região** e **estado** na barra lateral, e os mapas podem ser vistos por estado ou por município.

- **Início**: resultado dos dois turnos lado a lado e o resumo da análise.
- **1º turno**: votos por candidato, mapa de quem ficou em 1º lugar, divisão por região e onde
  os candidatos eliminados foram mais fortes.
- **2º turno**: Lula x Flávio, mapa da vantagem de cada um, ranking dos estados e resultado
  por região.
- **Comparação entre turnos**: mapas do vencedor nos dois turnos lado a lado, de onde vieram os
  votos novos de cada candidato, para onde foi cada grupo de eleitores, crescimento por região,
  perfil dos municípios onde Lula mais cresceu e ranking de municípios.
- **Escolaridade**: escolaridade do eleitorado por região e no mapa, voto de Lula nos
  municípios mais e menos escolarizados e estimativa de quanto cada faixa de escolaridade
  mudou o voto entre os turnos.
- **Metodologia e dados**: etapas, fontes, checagens de qualidade e limites da análise.

### Como a transferência é estimada

O voto é secreto, então não existe o dado "quem votou em Cury no 1º turno votou em quem no 2º".
O dashboard usa **inferência ecológica**: compara o 1º e o 2º turno em mais de 5.500 municípios
e encontra as proporções de transferência (entre 0% e 100%, somando 100% para cada origem) que
melhor explicam todos ao mesmo tempo. O resultado é uma **estimativa média**. Ele é mais
confiável quando filtrado por região e deve ser lido como ordem de grandeza, não como contagem
exata.

## Como rodar

Requer Python 3.10 ou mais recente.

```powershell
pip install -r requirements.txt

# 1. Baixa os resultados do TSE e as malhas do IBGE e gera os resumos em dados/
python preparar_dados.py

# (opcional) também resume o perfil do eleitorado. Precisa dos CSVs por UF
# baixados com baixar_eleitorado_2026.py e demora bastante.
python preparar_dados.py --perfil

# 2. Abre o dashboard no navegador
python -m streamlit run app.py
```

## Arquivos

| Arquivo | O que faz |
|---|---|
| `baixar_eleitorado_2026.py` | Baixa o perfil do eleitorado por seção (TSE) das 27 UFs, um CSV por estado |
| `preparar_dados.py` | Baixa os resultados da eleição e resume tudo por município em `dados/` |
| `app.py` | Abre o dashboard: menu de páginas e filtros |
| `analise.py` | Funções compartilhadas: carga dos dados, modelo de transferência, mapas |
| `paginas/` | Uma página por etapa da análise |
| `dados/` | Resumos prontos para o dashboard (gerados pelo `preparar_dados.py`) |

Os arquivos brutos (CSVs por UF e `_brutos/`) não vão para o repositório por causa do tamanho.

## Fontes

- TSE · Portal de Dados Abertos: [votação por seção eleitoral](https://dadosabertos.tse.jus.br),
  detalhe da votação por município e zona, perfil do eleitorado por seção 2026
- IBGE · [API de malhas territoriais](https://servicodados.ibge.gov.br/api/docs/malhas)
- Correspondência de códigos TSE ↔ IBGE:
  [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE)
