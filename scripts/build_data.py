#!/usr/bin/env python3
"""Gera os JSON da página "Preços do Mercado · Curitiba".

Uso: python3 scripts/build_data.py
Lê:   dados/historico/*.csv.gz  (histórico compacto: data, loja, produto, preços)
      dados/diarios/*.csv.gz    (arquivos diários do Clique Economia, formato original)
      dados/lojas.json          (localização aproximada das lojas)
Grava: site/data/*.json
Falha (exit 1) se o arquivo diário mais recente não passar na validação — assim a
página publicada nunca é substituída por dados quebrados.
"""
import glob, json, math, os, re, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_TARGET = "2026-11-08"     # marco zero pedido; usa a última pesquisa até essa data
DAILY_FROM = "2025-01-01"      # antes disso a série é semanal
WINDOW_DAYS = 7
NEAR_KM = 6.5
NEAR_MIN = 6

CATS = {1: "Produtos básicos", 2: "Alimentos especiais (sem glúten, diet…)", 3: "Direto do produtor",
        4: "Pães", 5: "Carnes, frios, laticínios e ovos", 6: "Higiene",
        7: "Limpeza e utilidades", 8: "Frutas, verduras e legumes", 9: "Bebidas", 0: "Outros"}

CHAIN_FIX = {
    "atacadao": "Atacadão", "assai": "Assaí", "gabao": "Gabão", "armazem da maria": "Armazém da Maria",
    "mini preco": "Mini Preço", "araucaria": "Araucária", "italo": "Ítalo", "rede master": "Rede Master",
    "super muffato": "Super Muffato", "super boni": "Super Boni", "super dia": "Super Dia",
    "tok super": "Tok Super", "rio verde": "Rio Verde", "super curitiba": "Super Curitiba",
}

ACC = {  # palavras que a fonte publica sem acento
    "pao": "pão", "paes": "pães", "feijao": "feijão", "acucar": "açúcar", "cafe": "café", "maca": "maçã",
    "macas": "maçãs", "limao": "limão", "mamao": "mamão", "melao": "melão", "sabao": "sabão",
    "algodao": "algodão", "file": "filé", "linguica": "linguiça", "oleo": "óleo", "agua": "água",
    "graos": "grãos", "grao": "grão", "acem": "acém", "coxao": "coxão", "pedaco": "pedaço", "fuba": "fubá",
    "racao": "ração", "frances": "francês", "macarrao": "macarrão", "parmesao": "parmesão",
    "requeijao": "requeijão", "pessego": "pêssego", "maracuja": "maracujá", "abobora": "abóbora",
    "agriao": "agrião", "brocolis": "brócolis", "alcool": "álcool", "higienico": "higiênico",
    "lampada": "lâmpada", "sanitaria": "sanitária", "sanitario": "sanitário", "po": "pó",
    "liquido": "líquido", "liquida": "líquida", "suina": "suína", "suino": "suíno", "musculo": "músculo",
    "figado": "fígado", "coracao": "coração", "cha": "chá", "acai": "açaí", "guarana": "guaraná",
    "pure": "purê", "adocante": "adoçante", "gluten": "glúten", "organico": "orgânico",
    "organica": "orgânica", "lactea": "láctea", "lacteo": "lácteo", "nectar": "néctar", "lenco": "lenço",
    "lencos": "lenços", "mao": "mão", "maos": "mãos", "oregano": "orégano", "acafrao": "açafrão",
    "rucula": "rúcula", "cara": "cará", "pinhao": "pinhão", "louca": "louça", "loucas": "louças",
    "fosforo": "fósforo", "fosforos": "fósforos", "aluminio": "alumínio", "plastico": "plástico",
    "descartavel": "descartável", "pacoca": "paçoca", "soluvel": "solúvel", "capsula": "cápsula",
    "capsulas": "cápsulas", "caes": "cães", "pimentao": "pimentão", "jilo": "jiló", "salsao": "salsão",
    "moida": "moída", "miudos": "miúdos", "lingua": "língua", "salsichao": "salsichão",
    "hamburguer": "hambúrguer", "sanduiche": "sanduíche", "gas": "gás", "isotonico": "isotônico",
    "energetico": "energético", "cachaca": "cachaça", "chimarrao": "chimarrão", "terere": "tereré",
    "atencao": "atenção", "duzia": "dúzia", "aco": "aço", "la": "lã", "chao": "chão", "moveis": "móveis",
    "locao": "loção", "geriatrica": "geriátrica", "diario": "diário", "flexiveis": "flexíveis",
    "codorna": "codorna", "medio": "médio", "media": "média", "proteina": "proteína",
    "mucarela": "muçarela", "mussarela": "muçarela", "instantaneo": "instantâneo", "sirio": "sírio",
    "arabe": "árabe", "vacuo": "vácuo", "sache": "sachê", "formula": "fórmula", "tilapia": "tilápia",
    "camarao": "camarão", "agroecologica": "agroecológica", "agricola": "agrícola", "maionese": "maionese",
    "polpa": "polpa", "calda": "calda", "seleta": "seleta", "vitamina": "vitamina", "bebe": "bebê",
    "condicionador": "condicionador", "lustra": "lustra", "inseticida": "inseticida", "papel": "papel",
    "acucarado": "açucarado", "achocolatado": "achocolatado", "amendoa": "amêndoa", "cereais": "cereais",
    "integral": "integral", "lentilha": "lentilha", "grao-de-bico": "grão-de-bico", "palmito": "palmito",
    "caqui": "caqui", "tangerina": "tangerina", "melancia": "melancia", "pera": "pera", "pessegos": "pêssegos",
    "tomate": "tomate", "rapido": "rápido", "rapida": "rápida", "classico": "clássico", "classica": "clássica",
    "tradicao": "tradição", "familia": "família", "economico": "econômico", "economica": "econômica",
    "pratico": "prático", "pratica": "prática", "extrafino": "extrafino", "ate": "até", "voce": "você",
    "nao": "não", "sao": "são", "joao": "joão", "pe": "pé", "unica": "única", "unico": "único",
    "agua sanitaria": "água sanitária", "cebolao": "cebolão", "limpeza": "limpeza", "manutencao": "manutenção",
    "pos": "pós", "pre": "pré", "contem": "contém", "cozido": "cozido", "frigorifico": "frigorífico",
    "acougue": "açougue", "presunto": "presunto", "file mignon": "filé mignon", "lombinho": "lombinho",
    "lagarto": "lagarto", "almondega": "almôndega", "almondegas": "almôndegas", "empanado": "empanado",
    "coracoes": "corações", "cancao": "canção", "orquidea": "orquídea", "triangulo": "triângulo",
    "uniao": "união", "sao": "são", "joao": "joão", "camil": "camil", "coroa": "coroa", "nordestino": "nordestino",
}


def accentify(text):
    def fix(m):
        w = m.group(0)
        r = ACC.get(w.lower())
        if not r:
            return w
        return r[0].upper() + r[1:] if w[0].isupper() else r
    return re.sub(r"[A-Za-zÀ-ÿ\-]+", fix, text)


def parse_desc(desc):
    d = re.sub(r"\s+", " ", str(desc).replace("\\", "")).strip().lower()
    parts = [p.strip(" .-") for p in re.split(r"\s-\s?|\s-(?=\S)", d)]
    parts = [p for p in parts if p]
    name = parts[0] if parts else d
    brand, size = "", ""
    if len(parts) >= 3:
        brand, size = parts[1], " ".join(parts[2:])
    elif len(parts) == 2:
        if re.search(r"\d|^(un|bj|dz|kg|pct|unidade|mç|maço)\b", parts[1]):
            size = parts[1]
        else:
            brand = parts[1]
    if re.fullmatch(r"\(\s*\+\s*\)\s*barato", brand.strip()):
        brand = "marca mais barata"
    elif brand:
        brand = " ".join(w.capitalize() if len(w) > 2 or i == 0 else w for i, w in enumerate(brand.split()))
        brand = accentify(brand)
    name = accentify(name)
    name = name[:1].upper() + name[1:]
    # a fonte às vezes escreve "1 GR" para pacotes de 1 kg
    if re.match(r"(farinha|arroz|açúcar|feijão|sal |fubá)", name.lower()) and re.fullmatch(r"(1|2|5)\s*gr?", size.strip()):
        size = size.strip().split()[0].rstrip("gr") + " kg"
    size = re.sub(r"(\d)\s*gr?\b", r"\1 g", size)
    size = re.sub(r"(\d)\s*kg\b", r"\1 kg", size)
    size = re.sub(r"(\d)\s*ml\b", r"\1 ml", size)
    size = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*litro\b", lambda m: m.group(1) + (" litro" if m.group(1) in ("1",) else " litros"), size)
    name = name.replace('\\"', '"').replace("\\", "")
    return name, brand, size


def chain_name(r):
    k = re.sub(r"\s+", " ", str(r)).strip().lower()
    if k in CHAIN_FIX:
        return CHAIN_FIX[k]
    return " ".join(w if w in ("da", "de", "do", "e") else w.capitalize() for w in k.split())


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def read_daily(path):
    try:
        df = pd.read_csv(path, sep=";", dtype={"id_produto": str}, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, sep=";", dtype={"id_produto": str}, encoding="latin-1")
    need = {"data_pesquisa", "id_empresa", "rede", "codigo_categoria", "id_produto", "descricao",
            "preco_regular", "preco_promocao"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"{os.path.basename(path)}: colunas ausentes {sorted(miss)}")
    return df


def validate_latest(daily, known_products, path):
    """Confere se o arquivo diário mais recente tem a cara dos anteriores."""
    errs = []
    if len(daily) < 800:
        errs.append(f"só {len(daily)} linhas")
    ids = set(daily["id_produto"].dropna())
    if known_products:
        overlap = len(ids & known_products) / max(len(ids), 1)
        if overlap < 0.6:
            errs.append(f"só {overlap:.0%} dos códigos de produto são conhecidos")
    p = pd.to_numeric(daily["preco_regular"], errors="coerce")
    if p.isna().mean() > 0.05 or (p <= 0).mean() > 0.2:
        errs.append("preços inválidos demais")
    if pd.to_datetime(daily["data_pesquisa"], errors="coerce").isna().mean() > 0.01:
        errs.append("datas inválidas")
    if errs:
        raise SystemExit(f"VALIDAÇÃO FALHOU em {os.path.basename(path)}: " + "; ".join(errs))


def main():
    out = os.path.join(ROOT, "site", "data")
    os.makedirs(out, exist_ok=True)
    cfg = json.load(open(os.path.join(ROOT, "dados", "lojas.json"), encoding="utf-8"))

    hist = pd.concat([pd.read_csv(f, sep=";", dtype={"id_produto": str})
                      for f in sorted(glob.glob(os.path.join(ROOT, "dados", "historico", "*.csv.gz")))])
    dfiles = sorted(glob.glob(os.path.join(ROOT, "dados", "diarios", "*.csv.gz")))
    dailies = [read_daily(f) for f in dfiles]
    known = set(hist["id_produto"]) | set().union(*[set(d["id_produto"]) for d in dailies[:-1]]) if dailies else set()
    if dailies:
        validate_latest(dailies[-1], known, dfiles[-1])
    daily = pd.concat(dailies, ignore_index=True)
    daily["id_produto"] = daily["id_produto"].str.replace(r"\.0$", "", regex=True)
    daily["id_empresa"] = pd.to_numeric(daily["id_empresa"], errors="coerce")

    cols = ["data_pesquisa", "id_empresa", "id_produto", "preco_regular", "preco_promocao"]
    df = pd.concat([hist[cols], daily[cols]], ignore_index=True)
    df["d"] = pd.to_datetime(df["data_pesquisa"], errors="coerce")
    df = df.dropna(subset=["d", "id_produto", "id_empresa"])
    df["id_empresa"] = df["id_empresa"].astype(int)
    for c in ("preco_regular", "preco_promocao"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    promo = df["preco_promocao"].where(df["preco_promocao"] > 0, np.inf)
    reg = df["preco_regular"].where(df["preco_regular"] > 0, np.inf)
    df["p"] = np.minimum(reg, promo)
    df["promo"] = (df["preco_promocao"] > 0) & (df["preco_promocao"] < df["preco_regular"])
    df = df[np.isfinite(df["p"]) & (df["p"] > 0)]
    df = df.drop_duplicates(subset=["d", "id_empresa", "id_produto"], keep="last")
    last_date = df["d"].max()
    print("linhas", len(df), "de", df["d"].min().date(), "até", last_date.date())

    # cadastro de produtos e lojas a partir dos diários (mais recentes)
    dsort = daily.sort_values("data_pesquisa")
    prodinfo = dsort.groupby("id_produto").agg(desc=("descricao", "last"), cat=("codigo_categoria", "last"))
    storeinfo = dsort.groupby("id_empresa").agg(rede=("rede", "last"), end=("endereco_completo", "last"))
    storeinfo.index = storeinfo.index.astype(int)

    recent = df[df["d"] >= last_date - pd.Timedelta(days=60)]
    vc = recent["id_produto"].value_counts()
    active = [p for p in vc[vc >= 3].index if p in prodinfo.index]
    df = df[df["id_produto"].isin(active)].copy()
    df["ym"] = df["d"].dt.to_period("M")
    med = df.groupby(["id_produto", "ym"])["p"].transform("median")
    df = df[(df["p"] <= med * 3) & (df["p"] >= med / 3)]

    # lojas ativas (vistas nos últimos 21 dias)
    act_stores = sorted(set(df.loc[df["d"] > last_date - pd.Timedelta(days=21), "id_empresa"]) & set(storeinfo.index))
    places = cfg["lugares"]
    atac = set(cfg.get("atacarejos", []))
    stores, sidx = [], {}
    for sid in act_stores:
        r = storeinfo.loc[sid]
        chain = chain_name(r.rede)
        end = str(r.end or "")
        street = re.sub(r"\s*-\s*Curitiba/PR\s*$", "", end).strip()
        parts = [p.strip() for p in street.split(" - ")]
        conf = cfg["lojas"].get(str(sid), {})
        bairro = conf.get("bairro") or (parts[-1] if len(parts) > 1 else "")
        rua = parts[0] if parts else street
        lat, lon = conf.get("lat"), conf.get("lon")
        if lat is None and bairro in cfg["bairros"]:
            lat, lon = cfg["bairros"][bairro]
        dist = {k: (round(hav((lat, lon), (v["lat"], v["lon"])), 1) if lat is not None else None)
                for k, v in places.items()}
        sidx[sid] = len(stores)
        stores.append({"id": int(sid), "rede": chain, "rua": rua, "bairro": bairro,
                       "atac": chain in atac, "km": dist})
    chains = sorted({s["rede"] for s in stores})

    all_dates = pd.Series(sorted(df["d"].unique()))
    old = all_dates[all_dates < DAILY_FROM]
    weekly = old.groupby(old.dt.to_period("W")).max()
    axis = pd.DatetimeIndex(list(weekly) + list(all_dates[all_dates >= DAILY_FROM]))
    cal = pd.date_range(df["d"].min(), last_date, freq="D")
    base_target = pd.Timestamp(BASE_TARGET)
    base_date = axis[axis <= base_target][-1]

    yr = df[df["d"] > last_date - pd.Timedelta(days=365)].copy()
    yr["rel"] = yr["p"] / yr.groupby(["id_empresa", "id_produto", "ym"])["p"].transform("median")
    yr["dow"] = yr["d"].dt.dayofweek
    yr["nm"] = yr.groupby(["id_empresa", "id_produto", "ym"])["p"].transform("size")
    yrw = yr[yr["nm"] >= 3]

    def pick(s, dt, tol=7):
        s2 = s.loc[:dt].dropna()
        if s2.empty or (dt - s2.index[-1]).days > tol:
            return None
        return float(s2.iloc[-1])

    prods, series = [], {}
    for pid, g in df.groupby("id_produto"):
        piv = g.pivot_table(index="d", columns="id_empresa", values="p", aggfunc="last")
        piv = piv.reindex(cal).ffill(limit=WINDOW_DAYS - 1)
        typ, low = piv.median(axis=1, skipna=True), piv.min(axis=1, skipna=True)
        now = pick(typ, last_date)
        if now is None:
            continue
        name, brand, size = parse_desc(prodinfo.loc[pid, "desc"])
        cat = int(prodinfo.loc[pid, "cat"]) if pd.notna(prodinfo.loc[pid, "cat"]) else 0
        var = {}
        for k, days in (("v7", 7), ("v10", 10), ("v30", 30), ("v90", 91), ("v365", 365)):
            past = pick(typ, last_date - pd.Timedelta(days=days))
            var[k] = round((now / past - 1) * 100, 1) if past else None
        rec = g[(g["d"] > last_date - pd.Timedelta(days=21)) & g["id_empresa"].isin(sidx)].sort_values("d")
        rec = rec.groupby("id_empresa").last()
        st = sorted(([sidx[s], int(round(r.p * 100)), int((last_date - r.d).days), int(bool(r.promo))]
                     for s, r in rec.iterrows()), key=lambda x: x[1])
        w = yrw[yrw["id_produto"] == pid].groupby("dow")["rel"].agg(["mean", "size"])
        wk = None
        if len(w) >= 4 and w["size"].min() >= 8:
            raw = [(float(w["mean"][i]) - 1) * 100 if i in w.index else None for i in range(5)]
            avg = np.mean([x for x in raw if x is not None])
            wk = [None if x is None else round(x - avg, 2) for x in raw]
        ty = typ[typ.index > last_date - pd.Timedelta(days=365)].dropna()
        hist_days = (last_date - typ.dropna().index[0]).days if typ.notna().any() else 0
        low12 = bool(hist_days >= 180 and len(ty) and now <= float(ty.min()) + 0.005 and now < float(ty.max()) * 0.97)
        prods.append({"id": pid, "n": name, "b": brand, "q": size, "c": cat, "now": round(now, 2),
                      "ns": len(st), **var, "s": st, "w": wk, "low12": low12,
                      "lo": [ty.idxmin().strftime("%Y-%m-%d"), round(float(ty.min()), 2)] if len(ty) else None,
                      "hi": [ty.idxmax().strftime("%Y-%m-%d"), round(float(ty.max()), 2)] if len(ty) else None})
        enc = lambda s: [None if pd.isna(x) else int(round(x * 100)) for x in s]
        series.setdefault(cat, {})[pid] = {"t": enc(typ.reindex(axis)), "m": enc(low.reindex(axis))}

    prods.sort(key=lambda p: (p["c"], p["n"], p["b"]))
    dump = lambda name, obj: json.dump(obj, open(os.path.join(out, name), "w", encoding="utf-8"),
                                       ensure_ascii=False, separators=(",", ":"))
    for f in glob.glob(os.path.join(out, "serie-*.json")):
        os.remove(f)
    for cat, s in series.items():
        dump(f"serie-{cat}.json", s)

    # ---------- insights ----------
    P = pd.DataFrame(prods)
    def top(col, n=10, asc=False):
        q = P.dropna(subset=[col])
        q = q[q["ns"] >= 4].sort_values(col, ascending=asc).head(n)
        return [[r.id, r[col]] for _, r in q.iterrows() if (r[col] < 0 if asc else r[col] > 0)]
    counts = {}
    for k in ("v7", "v30", "v365"):
        v = P[k].dropna()
        counts[k] = {"up": int((v > 0.05).sum()), "down": int((v < -0.05).sum()), "eq": int((v.abs() <= 0.05).sum())}
    cat_idx = {int(c): {k: (round(float(g[k].median()), 1) if g[k].notna().sum() >= 5 else None)
                        for k in ("v30", "v90", "v365")} for c, g in P.groupby("c")}

    m30 = df[(df["d"] > last_date - pd.Timedelta(days=30)) & df["id_empresa"].isin(sidx)].copy()
    m30 = m30.sort_values("d").groupby(["id_empresa", "id_produto"]).last().reset_index()
    m30["rel"] = m30["p"] / m30.groupby("id_produto")["p"].transform("median")
    sr = m30.groupby("id_empresa").agg(rel=("rel", "mean"), n=("id_produto", "nunique"))
    sr = sr[sr["n"] >= 120].sort_values("rel")
    store_rank = [[sidx[s], round((r.rel - 1) * 100, 1), int(r.n)] for s, r in sr.iterrows()]

    wall = yrw.groupby("dow")["rel"].mean()
    week_all = [(float(wall.get(i, np.nan)) - 1) * 100 for i in range(5)]
    week_all = [round(x - np.nanmean(week_all), 2) for x in week_all]
    lows = P[P["low12"] & (P["ns"] >= 5)].sort_values("ns", ascending=False)
    insights = {"up7": top("v7"), "down7": top("v7", asc=True), "up30": top("v30"), "down30": top("v30", asc=True),
                "up365": top("v365"), "down365": top("v365", asc=True), "counts": counts, "cat": cat_idx,
                "stores": store_rank, "week": week_all, "lows": lows["id"].tolist()[:40]}
    days_cov = sorted({d.strftime("%Y-%m-%d") for d in df["d"][df["d"] > last_date - pd.Timedelta(days=14)]})
    meta = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
            "last": last_date.strftime("%Y-%m-%d"), "first": axis[0].strftime("%Y-%m-%d"),
            "base_target": BASE_TARGET, "base": base_date.strftime("%Y-%m-%d"),
            "axis": [d.strftime("%Y-%m-%d") for d in axis], "recent_days": days_cov,
            "stores": stores, "places": {k: v["nome"] for k, v in places.items()},
            "near_km": NEAR_KM, "near_min": NEAR_MIN, "cats": CATS, "n": len(prods),
            "source": "Clique Economia — SMSAN / Prefeitura de Curitiba (Dados Abertos)"}
    dump("meta.json", meta)
    dump("produtos.json", prods)
    dump("insights.json", insights)
    print("produtos", len(prods), "lojas", len(stores), "marco zero", meta["base"], "contagens", counts)


if __name__ == "__main__":
    main()
