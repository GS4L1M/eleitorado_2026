"""
Prepara os dados do dashboard (app.py) a partir dos arquivos do TSE.

Lê os arquivos grandes em pedaços (pouca memória RAM) e grava em dados/
apenas tabelas agregadas por município, que ocupam poucos MB.

Entradas (em _brutos/, baixadas automaticamente se faltarem):
  - votacao_secao_2026_BR.zip          votos para presidente por seção, 1º e 2º turno
  - detalhe_votacao_munzona_2026.zip   aptos, comparecimento, abstenção, brancos e nulos
  - municipios_tse_ibge.csv            código TSE -> código IBGE (para o mapa)
  - malha_municipios.json / malha_ufs.json   malhas do IBGE
  - <UF>.csv na pasta do projeto       perfil do eleitorado (opcional, use --perfil)

Uso:
  python preparar_dados.py            # votos, comparecimento e mapas
  python preparar_dados.py --perfil   # também agrega o perfil do eleitorado (demora)
"""

import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1) Configuração
# ---------------------------------------------------------------------------
PASTA = Path(__file__).resolve().parent
BRUTOS = PASTA / "_brutos"
DADOS = PASTA / "dados"

TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
IBGE = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao="
DOWNLOADS = {
    "votacao_secao_2026_BR.zip": f"{TSE}/votacao_secao/votacao_secao_2026_BR.zip",
    "detalhe_votacao_munzona_2026.zip": f"{TSE}/detalhe_votacao_munzona/detalhe_votacao_munzona_2026.zip",
    "municipios_tse_ibge.csv": "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv",
    "malha_municipios.json": IBGE + "municipio",
    "malha_ufs.json": IBGE + "UF",
}

REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
UF_REGIAO = {uf: reg for reg, ufs in REGIOES.items() for uf in ufs}
UF_REGIAO["ZZ"] = "Exterior"

# Códigos IBGE de UF (os dois primeiros dígitos do código do município)
UF_IBGE = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
           "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
           "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
           "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}

CHUNK = 500_000         # linhas por pedaço; diminua se faltar memória


def baixar_se_faltar() -> None:
    BRUTOS.mkdir(exist_ok=True)
    for nome, url in DOWNLOADS.items():
        destino = BRUTOS / nome
        if destino.exists():
            continue
        print(f"baixando {nome}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(destino, "wb") as f:
            while bloco := resp.read(1024 * 1024):
                f.write(bloco)


def ler_csv_do_zip(zip_path: Path, nome_csv: str, **kwargs):
    z = zipfile.ZipFile(zip_path)
    arquivo = io.TextIOWrapper(z.open(nome_csv), encoding="latin1")
    return pd.read_csv(arquivo, sep=";", **kwargs)


# ---------------------------------------------------------------------------
# 2) Votos por município, turno e candidato
# ---------------------------------------------------------------------------
def preparar_votos() -> pd.DataFrame:
    print("agregando votos por município (1,5 GB, alguns minutos)...")
    chaves = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_VOTAVEL", "NM_VOTAVEL"]
    partes = []
    leitor = ler_csv_do_zip(BRUTOS / "votacao_secao_2026_BR.zip", "votacao_secao_2026_BR.csv",
                            usecols=chaves + ["QT_VOTOS"], dtype={"CD_MUNICIPIO": str},
                            chunksize=CHUNK)
    for i, pedaco in enumerate(leitor, start=1):
        partes.append(pedaco.groupby(chaves, as_index=False)["QT_VOTOS"].sum())
        print(f"\r   {i * CHUNK / 1e6:.1f} milhões de linhas", end="", flush=True)
    print()

    votos = pd.concat(partes).groupby(chaves, as_index=False)["QT_VOTOS"].sum()
    votos.columns = ["turno", "uf", "cd_tse", "municipio", "nr_votavel", "candidato", "votos"]
    votos["cd_tse"] = votos["cd_tse"].str.zfill(5)
    votos["candidato"] = votos["candidato"].replace({"VOTO BRANCO": "BRANCO", "VOTO NULO": "NULO"})
    return votos


# ---------------------------------------------------------------------------
# 3) Aptos, comparecimento e abstenção por município e turno
# ---------------------------------------------------------------------------
def preparar_comparecimento() -> pd.DataFrame:
    print("agregando comparecimento...")
    cols = {"NR_TURNO": "turno", "SG_UF": "uf", "CD_MUNICIPIO": "cd_tse",
            "QT_APTOS": "aptos", "QT_COMPARECIMENTO": "comparecimento",
            "QT_ABSTENCOES": "abstencoes", "QT_VOTOS_BRANCOS": "brancos",
            "QT_TOTAL_VOTOS_NULOS": "nulos", "QT_TOTAL_VOTOS_VALIDOS": "validos"}
    df = ler_csv_do_zip(BRUTOS / "detalhe_votacao_munzona_2026.zip",
                        "detalhe_votacao_munzona_2026_BR.csv",
                        usecols=list(cols), dtype={"CD_MUNICIPIO": str})
    df = df.rename(columns=cols)
    df["cd_tse"] = df["cd_tse"].str.zfill(5)
    return df.groupby(["turno", "uf", "cd_tse"], as_index=False).sum(numeric_only=True)


# ---------------------------------------------------------------------------
# 4) Perfil do eleitorado por município (lê os 27 CSVs, ~25 GB)
# ---------------------------------------------------------------------------
# Os 8 níveis de escolaridade do TSE e o nome curto da coluna em dados/
NIVEIS_ESCOLARIDADE = {
    "ANALFABETO": "esc_analfabeto",
    "LÊ E ESCREVE": "esc_le_escreve",
    "ENSINO FUNDAMENTAL INCOMPLETO": "esc_fund_incompleto",
    "ENSINO FUNDAMENTAL COMPLETO": "esc_fund_completo",
    "ENSINO MÉDIO INCOMPLETO": "esc_medio_incompleto",
    "ENSINO MÉDIO COMPLETO": "esc_medio_completo",
    "SUPERIOR INCOMPLETO": "esc_sup_incompleto",
    "SUPERIOR COMPLETO": "esc_sup_completo",
}


def preparar_perfil() -> pd.DataFrame:
    jovens = {"16 anos", "17 anos", "18 anos", "19 anos", "20 anos", "21 a 24 anos"}
    escolaridade_baixa = {"ANALFABETO", "LÊ E ESCREVE", "ENSINO FUNDAMENTAL INCOMPLETO"}
    resultado = []
    for uf in sorted(set(UF_REGIAO) - {"ZZ"}):
        arquivo = PASTA / f"{uf}.csv"
        if not arquivo.exists():
            print(f"   {uf}.csv não encontrado, pulando")
            continue
        print(f"   perfil {uf}...")
        partes = []
        for p in pd.read_csv(arquivo, sep=";", encoding="latin1", chunksize=CHUNK,
                             usecols=["CD_MUNICIPIO", "DS_GENERO", "DS_FAIXA_ETARIA",
                                      "DS_GRAU_ESCOLARIDADE", "QT_ELEITORES"],
                             dtype={"CD_MUNICIPIO": str}):
            q = p["QT_ELEITORES"]
            faixa = p["DS_FAIXA_ETARIA"].str.strip()
            idade = pd.to_numeric(faixa.str.extract(r"^(\d+)")[0], errors="coerce")
            partes.append(pd.DataFrame({
                "cd_tse": p["CD_MUNICIPIO"].str.zfill(5),
                "eleitores": q,
                "mulheres": q.where(p["DS_GENERO"] == "FEMININO", 0),
                "jovens_16_24": q.where(faixa.isin(jovens), 0),
                "idosos_60_mais": q.where(idade >= 60, 0),
                "escolaridade_baixa": q.where(p["DS_GRAU_ESCOLARIDADE"].isin(escolaridade_baixa), 0),
                "superior_completo": q.where(p["DS_GRAU_ESCOLARIDADE"] == "SUPERIOR COMPLETO", 0),
                **{col: q.where(p["DS_GRAU_ESCOLARIDADE"] == nivel, 0)
                   for nivel, col in NIVEIS_ESCOLARIDADE.items()},
            }).groupby("cd_tse").sum())
        df = pd.concat(partes).groupby(level=0).sum()
        df.insert(0, "uf", uf)
        resultado.append(df.reset_index())

    perfil = pd.concat(resultado, ignore_index=True)
    for col in ["mulheres", "jovens_16_24", "idosos_60_mais", "escolaridade_baixa", "superior_completo"]:
        perfil[f"pct_{col}"] = perfil[col] / perfil["eleitores"] * 100
    return perfil


# ---------------------------------------------------------------------------
# 5) Loop principal
# ---------------------------------------------------------------------------
def main() -> None:
    baixar_se_faltar()
    DADOS.mkdir(exist_ok=True)

    codigos = pd.read_csv(BRUTOS / "municipios_tse_ibge.csv", dtype=str)
    codigos = codigos.rename(columns={"codigo_tse": "cd_tse", "codigo_ibge": "cd_ibge"})
    codigos["cd_tse"] = codigos["cd_tse"].str.zfill(5)
    codigos = codigos[["cd_tse", "cd_ibge"]]

    votos = preparar_votos().merge(codigos, on="cd_tse", how="left")
    votos["regiao"] = votos["uf"].map(UF_REGIAO)
    votos.to_parquet(DADOS / "votos_municipio.parquet", index=False)

    comp = preparar_comparecimento().merge(codigos, on="cd_tse", how="left")
    comp["regiao"] = comp["uf"].map(UF_REGIAO)
    comp.to_parquet(DADOS / "comparecimento_municipio.parquet", index=False)

    sem_ibge = votos.loc[votos["cd_ibge"].isna() & (votos["uf"] != "ZZ"), "municipio"].unique()
    if len(sem_ibge):
        print(f"aviso: {len(sem_ibge)} municípios sem código IBGE (não aparecem no mapa):", *sem_ibge[:10])

    # Malhas: grava com a sigla da UF no lugar do código numérico
    ufs = json.loads((BRUTOS / "malha_ufs.json").read_text(encoding="utf-8"))
    for f in ufs["features"]:
        f["properties"]["uf"] = UF_IBGE[f["properties"]["codarea"]]
    (DADOS / "ufs.geojson").write_text(json.dumps(ufs), encoding="utf-8")
    mun = (BRUTOS / "malha_municipios.json").read_text(encoding="utf-8")
    (DADOS / "municipios.geojson").write_text(mun, encoding="utf-8")

    if "--perfil" in sys.argv:
        print("agregando perfil do eleitorado (vai demorar)...")
        preparar_perfil().to_parquet(DADOS / "perfil_municipio.parquet", index=False)

    print(f"\nConcluído. Arquivos em {DADOS}")


if __name__ == "__main__":
    main()
