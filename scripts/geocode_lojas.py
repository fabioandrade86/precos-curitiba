#!/usr/bin/env python3
"""Descobre a posição (lat/lon) de cada loja pelo endereço, usando o geocodificador público
do OpenStreetMap (Nominatim), e guarda em dados/geocache.json.

- Só consulta endereços que ainda não estão no cache (1 consulta por segundo, como pede a
  política do Nominatim).
- Só aceita resultado com número de casa/prédio dentro de Curitiba. Se o OpenStreetMap só
  conhecer a rua (sem o número), o resultado é descartado e a página usa a posição
  aproximada de dados/lojas.json.
Uso: python3 scripts/geocode_lojas.py
"""
import glob, gzip, io, json, os, re, sys, time, urllib.parse, urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "dados", "geocache.json")
UA = "precos-curitiba/1.0 (+https://github.com/fabioandrade86/precos-curitiba)"
BBOX = (-25.65, -49.40, -25.33, -49.18)  # sul, oeste, norte, leste (Curitiba)


def clean(addr):
    a = re.sub(r"\s*-\s*Curitiba/PR\s*$", "", str(addr)).strip()
    parts = [p.strip() for p in a.split(" - ")]
    rua = parts[0]
    rua = re.sub(r"\bn[º°o]\s*", "", rua, flags=re.I)
    rua = re.sub(r"^R\.\s", "Rua ", rua)
    rua = re.sub(r"^Av\.\s", "Avenida ", rua)
    rua = re.sub(r"\bVer\b", "Vereador", rua)
    rua = re.sub(r"\bRep\.\s", "República ", rua)
    rua = re.sub(r"\bBR\s?(\d)", r"BR-\1", rua)
    rua = re.sub(r"\s+-\s+(\d+)", r", \1", rua)
    m = re.match(r"(.*?)[,\s]+(\d+)\s*$", rua)
    return (m.group(1).strip(" ,"), m.group(2)) if m else (rua.strip(" ,"), "")


def geocode(street, number):
    params = {"format": "jsonv2", "limit": "1", "countrycodes": "br", "addressdetails": "1",
              "street": f"{number} {street}".strip(), "city": "Curitiba", "state": "Paraná"}
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    if not res:
        return None
    x = res[0]
    lat, lon = float(x["lat"]), float(x["lon"])
    precise = bool(number) and (x.get("address", {}).get("house_number") or x.get("addresstype") in ("building", "place"))
    inside = BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]
    return {"lat": round(lat, 5), "lon": round(lon, 5), "ok": bool(precise and inside),
            "osm": x.get("display_name", "")[:120]}


def main():
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    cfg = json.load(open(os.path.join(ROOT, "dados", "lojas.json"), encoding="utf-8"))
    files = sorted(glob.glob(os.path.join(ROOT, "dados", "diarios", "*.csv.gz")))[-10:]
    addrs = set()
    for f in files:
        raw = gzip.open(f).read()
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError:
            txt = raw.decode("latin-1")
        df = pd.read_csv(io.StringIO(txt), sep=";", usecols=["endereco_completo"])
        addrs |= set(df["endereco_completo"].dropna())
    addrs |= {e["rua"] for e in cfg.get("extras", [])}
    novos = 0
    for a in sorted(addrs):
        if a in cache:
            continue
        street, number = clean(a)
        try:
            cache[a] = geocode(street, number) or {"ok": False}
        except Exception as e:  # sem rede: tenta na próxima execução
            print("  erro", a, e, file=sys.stderr)
            continue
        novos += 1
        print(("  ok   " if cache[a].get("ok") else "  ~    ") + a)
        time.sleep(1.2)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"geo={novos}\n")
    print(f"endereços consultados agora: {novos}; com posição exata: {sum(1 for v in cache.values() if v.get('ok'))}/{len(cache)}")


if __name__ == "__main__":
    main()
