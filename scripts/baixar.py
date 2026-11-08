#!/usr/bin/env python3
"""Baixa os arquivos diários do Clique Economia que ainda não estão em dados/diarios/.

Fonte: espelho do Portal de Dados Abertos de Curitiba na UFPR (C3SL), um arquivo por dia:
  http://dadosabertos.c3sl.ufpr.br/curitiba/CliqueEconomia/AAAA-MM-DD_Clique_Economia_-_Cotacoes_-_Base_de_Dados.csv
Olha os últimos 10 dias úteis. Grava gzip. Escreve 'novos=N' em $GITHUB_OUTPUT.
"""
import gzip, os, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "dados", "diarios")
URL = "http://dadosabertos.c3sl.ufpr.br/curitiba/CliqueEconomia/{d}_Clique_Economia_-_Cotacoes_-_Base_de_Dados.csv"


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "precos-curitiba (GitHub Actions)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:  # rede instável: tenta de novo
            err = e
        time.sleep(5 * (i + 1))
    print(f"  falha ao baixar {url}: {err}", file=sys.stderr)
    return None


def main():
    os.makedirs(DEST, exist_ok=True)
    today = datetime.now(timezone(timedelta(hours=-3))).date()
    novos = 0
    d = today - timedelta(days=14)
    while d <= today:
        if d.weekday() < 5:
            path = os.path.join(DEST, f"{d.isoformat()}.csv.gz")
            if not os.path.exists(path):
                data = fetch(URL.format(d=d.isoformat()))
                if data and len(data) > 1000 and data[:12].lower().startswith(b"data_pesquis"):
                    with gzip.GzipFile(path, "wb", mtime=0, compresslevel=9) as f:
                        f.write(data)
                    novos += 1
                    print(f"  novo: {d} ({len(data)//1024} KB)")
                elif data is not None:
                    print(f"  ignorado: {d} (arquivo vazio ou inesperado, {len(data)} bytes)")
        d += timedelta(days=1)
    # teste de conexão com a fonte (aparece no log do GitHub Actions)
    ultimos = sorted(f[:10] for f in os.listdir(DEST) if f.endswith(".csv.gz"))
    if ultimos:
        try:
            req = urllib.request.Request(URL.format(d=ultimos[-1]), method="HEAD",
                                         headers={"User-Agent": "precos-curitiba (GitHub Actions)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"fonte acessível (HTTP {r.status}); último dia guardado: {ultimos[-1]}")
        except Exception as e:
            print(f"ATENÇÃO: fonte inacessível: {e}", file=sys.stderr)
    print(f"arquivos novos: {novos}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"novos={novos}\n")


if __name__ == "__main__":
    main()
