# Consolidação de Dados de Eleitorado - Brasil 2026

Oct 28, 2026 · @Omnitrack

## Resumo Executivo

Análise consolidada do perfil do eleitorado brasileiro (2026) por seção eleitoral em todos os 27 estados. Os dados estão disponíveis no Portal de Dados Abertos do TSE em formato CSV, separados por estado.

Objetivo: visualizar no Power BI características demográficas do eleitorado (gênero, faixa etária, etc) por estado e identificar padrões gerais para o Brasil.

## Abordagem 1: Download Manual

**Processo manual direto no portal:**

1. Acesse https://dadosabertos.tse.jus.br
2. Procure por "Perfil do eleitorado por seção eleitoral - 2026"
3. Clique em "Explorar" para cada estado
4. Download do arquivo CSV
5. Salve todos os CSVs em uma pasta local (ex: `C:\eleitorado_2026\`)

**Vantagens:** Controle total, nenhuma dependência de código, rápido se poucos estados.

**Desvantagens:** Manual, repetitivo para 27 estados, propenso a erros.

## Abordagem 2: Download Automático com Python

**Identificar padrão de URL e fazer download em loop:**

Os arquivos provavelmente seguem um padrão tipo:

```
https://cdn.tse.jus.br/[...]/perfil_eleitorado_secao_2026_XX.csv
```

Onde `XX` = UF (MG, SP, RJ, RS, etc).

**Vantagens:** Automático, rápido para todos os 27 estados, reproduzível.

**Desvantagens:** Requer descobrir o padrão de URL exato, validação de download.

**Codigo no github**

## Consolidação no Power BI

**Passo 1: Organizar arquivos locais**

Crie uma pasta com todos os CSVs, ex:

```
C:\eleitorado_2026\
  ├── MG.csv
  ├── SP.csv
  ├── RJ.csv
  └── ... (todos os 27 estados)
```

**Passo 2: Importar dados**

1. Power BI → **Get Data** → **Folder**
2. Aponte para `C:\eleitorado_2026\`
3. Clique **Combine & Load**

Power BI detecta automaticamente que todos têm a mesma estrutura e consolida tudo numa tabela única.

**Passo 3: Transformar dados (se necessário)**

No Power Query, adicione coluna com o estado (extraindo do nome do arquivo ou adicionando manualmente antes do import).

**Resultado final:** Um dataset consolidado com todos os estados prontos para visualização.

## Análises Visuais e KPIs Propostos

**Dashboards sugeridos:**

1. **Perfil Demográfico Nacional**
   - Total de eleitores no Brasil
   - Distribuição por gênero (gráfico de pizza)
   - Distribuição por faixa etária (histograma)
2. **Análise por Estado**
   - Tabela: Estado, Total de eleitores, % gênero, faixa etária principal
   - Mapa do Brasil com densidade de eleitores por estado
   - Ranking de estados por total de eleitores
3. **Comparações Regionais**
   - Género: comparação Norte vs Nordeste vs Centro-Oeste vs Sudeste vs Sul
   - Faixa etária: pie charts por região
4. **Insights Gerais**
   - Qual estado tem maior concentração de jovens/idosos?
   - Qual região tem melhor equilíbrio gênero/idade?
   - Padrões de variação entre seções eleitorais

**Próximos passos:** Definir quais visualizações priorizar de acordo com os objetivos da análise.
