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

## O que o dashboard mostra

1. **Indicadores**: votos de cada candidato nos dois turnos, abstenção, brancos e nulos.
2. **Transferência de votos**: estimativa de quanto do voto de cada candidato eliminado, dos
   brancos/nulos e da abstenção do 1º turno foi para Lula, para Flávio ou ficou de fora no 2º
   turno (gráfico em cascata, matriz e diagrama de fluxo).
3. **Mapa** por estado ou por município: margem no 2º turno, vencedor de cada turno e
   crescimento de Lula. **Azul = Flávio Bolsonaro · Vermelho = Lula.**
4. **Por região**: quanto cada candidato ganhou entre os turnos em cada região e de onde vieram
   os votos novos de Lula.
5. **Perfil do eleitorado**: relação entre o crescimento de Lula e escolaridade, idade e gênero
   dos eleitores de cada município.
6. **Ranking** dos municípios onde Lula mais ganhou votos.

Todas as seções respondem aos filtros de **região** e **estado** na barra lateral.

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
| `app.py` | O dashboard Streamlit |
| `dados/` | Resumos prontos para o dashboard (gerados pelo `preparar_dados.py`) |

Os arquivos brutos (CSVs por UF e `_brutos/`) não vão para o repositório por causa do tamanho.

## Fontes

- TSE · Portal de Dados Abertos: [votação por seção eleitoral](https://dadosabertos.tse.jus.br),
  detalhe da votação por município e zona, perfil do eleitorado por seção 2026
- IBGE · [API de malhas territoriais](https://servicodados.ibge.gov.br/api/docs/malhas)
- Correspondência de códigos TSE ↔ IBGE:
  [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE)
