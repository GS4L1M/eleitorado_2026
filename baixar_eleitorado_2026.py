"""
Baixa o "Perfil do eleitorado por seção eleitoral - 2026" (TSE) de todas as UFs,
extrai o CSV de cada ZIP e salva em C:\\eleitorado_2026\\<UF>.csv

Requisitos: só a biblioteca padrão do Python (3.8+). Nada para instalar.
Uso:  python baixar_eleitorado_2026.py
"""

import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# 1) Configuração
# ---------------------------------------------------------------------------
URL_BASE = ("https://cdn.tse.jus.br/estatistica/sead/odsele/"
            "perfil_eleitor_secao/perfil_eleitor_secao_2026_{uf}.zip")

PASTA_DESTINO = Path(r"C:\eleitorado_2026")
PASTA_ZIPS = PASTA_DESTINO / "_zips"          # ZIPs temporários

UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
       "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
       "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

TENTATIVAS = 3          # quantas vezes tentar de novo se a conexão cair
APAGAR_ZIPS = True      # apaga os ZIPs depois de extrair


# ---------------------------------------------------------------------------
# 2) Download em streaming (não carrega o arquivo inteiro na memória;
#    importante porque o ZIP de SP/MG passa de centenas de MB)
# ---------------------------------------------------------------------------
def baixar(url: str, destino: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        baixado = 0
        with open(destino, "wb") as f:
            while bloco := resp.read(1024 * 1024):      # lê 1 MB por vez
                f.write(bloco)
                baixado += len(bloco)
                if total:
                    pct = baixado / total * 100
                    print(f"\r   {baixado/1e6:7.1f} / {total/1e6:.1f} MB ({pct:5.1f}%)",
                          end="", flush=True)
    print()


# ---------------------------------------------------------------------------
# 3) Extrai apenas o .csv de dentro do ZIP e renomeia para <UF>.csv
#    (o ZIP também traz um leiame .pdf que não interessa ao Power BI)
# ---------------------------------------------------------------------------
def extrair_csv(zip_path: Path, uf: str) -> Path:
    with zipfile.ZipFile(zip_path) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            raise ValueError("nenhum CSV dentro do ZIP")
        saida = PASTA_DESTINO / f"{uf}.csv"
        with z.open(csvs[0]) as origem, open(saida, "wb") as destino:
            shutil.copyfileobj(origem, destino)
    return saida


# ---------------------------------------------------------------------------
# 4) Loop principal
# ---------------------------------------------------------------------------
def main() -> None:
    PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
    PASTA_ZIPS.mkdir(exist_ok=True)
    falhas = []

    for i, uf in enumerate(UFS, start=1):
        csv_final = PASTA_DESTINO / f"{uf}.csv"
        if csv_final.exists():                          # permite retomar
            print(f"[{i:02}/{len(UFS)}] {uf}: já existe, pulando")
            continue

        url = URL_BASE.format(uf=uf)
        zip_path = PASTA_ZIPS / f"{uf}.zip"
        print(f"[{i:02}/{len(UFS)}] {uf}: baixando...")

        for tentativa in range(1, TENTATIVAS + 1):
            try:
                baixar(url, zip_path)
                saida = extrair_csv(zip_path, uf)
                print(f"   OK -> {saida} ({saida.stat().st_size/1e6:.1f} MB)")
                if APAGAR_ZIPS:
                    zip_path.unlink()
                break
            except Exception as e:
                print(f"   erro (tentativa {tentativa}/{TENTATIVAS}): {e}")
                time.sleep(5 * tentativa)               # espera crescente
        else:
            falhas.append(uf)

    if APAGAR_ZIPS and not any(PASTA_ZIPS.iterdir()):
        PASTA_ZIPS.rmdir()

    print("\nConcluído.")
    if falhas:
        print("Falharam (rode o script de novo para tentar só esses):", ", ".join(falhas))


if __name__ == "__main__":
    main()
