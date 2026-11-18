#!/usr/bin/env python3
"""
HOCVOLTBR — atualização diária da base Brasil de eletropostos.

Fonte principal: o mapa completo do Brasil no OpenStreetMap (arquivo diário da Geofabrik,
filtrado pelo osmium no GitHub Actions; variável OSM_GEOJSONSEQ). Se ele faltar, varre os
27 estados pela Overpass API. Se houver chave, soma os pontos do Open Charge Map. O estado
de cada ponto vem da malha oficial do IBGE. Gera:
  data/brasil.json  -> todos os pontos (eletropostos + postos de combustível com recarga)
  data/meta.json    -> data/hora da atualização e totais

Regras de segurança:
  - Se um estado falhar em todas as tentativas, mantém os dados de ontem desse estado.
  - Se TODOS os estados falharem, não sobrescreve nada e sai com erro.

Só usa a biblioteca padrão do Python; se o pacote shapely estiver instalado, fica mais rápido.
Variáveis de ambiente opcionais:
  OCM_KEY        chave gratuita do Open Charge Map (se faltar, usa a gravada no index.html)
  OSM_GEOJSONSEQ arquivo do osmium export (-f geojsonseq -u type_id)
  OVERPASS_URL   força um servidor Overpass específico (testes)
  OCM_URL        força um endereço do Open Charge Map (testes)
"""
import json, math, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "brasil.json")
META = os.path.join(DATA, "meta.json")

UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
       "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
UF_NOMES = {"acre":"AC","alagoas":"AL","amapa":"AP","amazonas":"AM","bahia":"BA","ceara":"CE",
  "distrito federal":"DF","espirito santo":"ES","goias":"GO","maranhao":"MA","mato grosso":"MT",
  "mato grosso do sul":"MS","minas gerais":"MG","para":"PA","paraiba":"PB","parana":"PR",
  "pernambuco":"PE","piaui":"PI","rio de janeiro":"RJ","rio grande do norte":"RN",
  "rio grande do sul":"RS","rondonia":"RO","roraima":"RR","santa catarina":"SC",
  "sao paulo":"SP","sergipe":"SE","tocantins":"TO"}

OVERPASS = [os.environ["OVERPASS_URL"]] if os.environ.get("OVERPASS_URL") else [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = "HOCVOLTBR/2.0 (atualizacao diaria; GitHub Actions)"
MATCH_M = 120

KEEP_EXACT = {"amenity","shop","name","brand","operator","network","opening_hours","fee","charge",
              "charge:conditional","access","motorcar","bicycle","scooter","motorcycle",
              "capacity","charging_station:output","maxpower","phone","website","description"}

def keep_tags(t):
    out = {}
    for k, v in t.items():
        if k in KEEP_EXACT or k.startswith(("socket:", "fuel:", "addr:", "payment:")):
            out[k] = v
    return out

def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return s.lower().strip()

def http_json(url, data=None, timeout=160, accept="application/json"):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

# ---------- Fonte principal: mapa do Brasil (Geofabrik) filtrado pelo osmium ----------
def _parse_id(fid):
    """'n123' -> ('node',123); 'w5' -> ('way',5); 'a20' -> área: par = via (10), ímpar = relação."""
    if not fid or len(fid) < 2 or not fid[1:].isdigit():
        return None, None
    p, n = fid[0], int(fid[1:])
    if p == "n": return "node", n
    if p == "w": return "way", n
    if p == "r": return "relation", n
    if p == "a": return ("way", n // 2) if n % 2 == 0 else ("relation", (n - 1) // 2)
    return None, None

def _geom_center(g):
    if not g:
        return None, None
    t, c = g.get("type"), g.get("coordinates")
    try:
        if t == "Point":
            return c[1], c[0]
        if t == "LineString":
            pts = c[:-1] if len(c) > 2 and c[0] == c[-1] else c
        elif t == "Polygon":
            pts = c[0][:-1] or c[0]
        elif t == "MultiPolygon":
            ring = max((p[0] for p in c), key=len)
            pts = ring[:-1] or ring
        else:
            return None, None
        return sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)
    except Exception:
        return None, None

VENUE_SHOPS = {"mall", "supermarket", "department_store"}

def osm_from_geojsonseq(path):
    """Lê o arquivo gerado por `osmium export -f geojsonseq -u type_id`."""
    out, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\x1e").strip()
            if not line:
                continue
            try:
                ft = json.loads(line)
            except Exception:
                continue
            t = ft.get("properties") or {}
            a, s = t.get("amenity"), t.get("shop")
            if a in ("charging_station", "fuel"):
                pass
            elif (a == "parking" or s in VENUE_SHOPS) and t.get("opening_hours"):
                pass
            else:
                continue
            typ, num = _parse_id(str(ft.get("id") or ""))
            if not typ:
                continue
            k = f"{typ}/{num}"
            if k in seen:
                continue
            lat, lon = _geom_center(ft.get("geometry"))
            if lat is None or not (-35 < lat < 6.5 and -75 < lon < -28):
                continue
            seen.add(k)
            out.append({"type": typ, "id": num, "lat": round(lat, 6), "lon": round(lon, 6),
                        "tags": keep_tags(t), "uf": None})
    return out

# ---------- Estado (UF) de cada ponto: malha oficial do IBGE ----------
IBGE_UF = {"11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO","21":"MA","22":"PI",
           "23":"CE","24":"RN","25":"PB","26":"PE","27":"AL","28":"SE","29":"BA","31":"MG","32":"ES",
           "33":"RJ","35":"SP","41":"PR","42":"SC","43":"RS","50":"MS","51":"MT","52":"GO","53":"DF"}

def _in_ring(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside

class UFLocator:
    """Descobre o estado de cada ponto pela malha do IBGE (shapely se houver; senão cálculo simples)."""
    def __init__(self):
        self.feats = None
        for q in ("intermediaria", "minima"):
            try:
                url = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson"
                       f"&intrarregiao=UF&qualidade={q}")
                d = http_json(url, timeout=180, accept="application/vnd.geo+json, application/json")
                feats = []
                for f in d.get("features", []):
                    uf = IBGE_UF.get(str((f.get("properties") or {}).get("codarea", ""))[:2])
                    if uf and f.get("geometry"):
                        feats.append((uf, f["geometry"]))
                if len({u for u, _ in feats}) >= 27:
                    self.feats = feats
                    print(f"Malha dos estados (IBGE, {q}) carregada.", flush=True)
                    break
            except Exception as ex:  # noqa
                print(f"Malha IBGE ({q}) indisponível: {ex}", flush=True)
        self.ok = self.feats is not None
        self.shp = None
        if self.ok:
            try:
                import shapely
                from shapely.geometry import shape
                self.shp = shapely
                self.geoms = [shape(g) for _, g in self.feats]
                self.ufs = [u for u, _ in self.feats]
                self.tree = shapely.STRtree(self.geoms)
            except Exception:
                self.shp = None
                self.polys = []
                for uf, g in self.feats:
                    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
                    for p in polys:
                        xs = [c[0] for c in p[0]]; ys = [c[1] for c in p[0]]
                        self.polys.append((uf, (min(xs), min(ys), max(xs), max(ys)), p[0], p[1:]))

    def locate(self, pts):
        """pts = [(lat, lon), ...] -> [uf, ...]"""
        if not self.ok or not pts:
            return [None] * len(pts)
        if self.shp is not None:
            sh = self.shp
            P = sh.points([(lo, la) for la, lo in pts])
            res = [None] * len(pts)
            idx_in, idx_tree = self.tree.query(P, predicate="within")
            for i, t in zip(idx_in.tolist(), idx_tree.tolist()):
                if res[i] is None:
                    res[i] = self.ufs[t]
            falt = [i for i, r in enumerate(res) if r is None]
            if falt:  # no litoral/ilhas: estado mais próximo
                ii, tt = self.tree.query_nearest(P[falt])
                for a_, t in zip(ii.tolist(), tt.tolist()):
                    res[falt[a_]] = self.ufs[t]
            return res
        res = []
        for la, lo in pts:
            achou, perto, pd = None, None, float("inf")
            for uf, (x0, y0, x1, y1), outer, holes in self.polys:
                if x0 <= lo <= x1 and y0 <= la <= y1:
                    if _in_ring(lo, la, outer) and not any(_in_ring(lo, la, h) for h in holes):
                        achou = uf; break
                d = max(x0 - lo, 0, lo - x1) + max(y0 - la, 0, la - y1)
                if d < pd: perto, pd = uf, d
            res.append(achou or perto)
        return res

def overpass_uf(uf):
    # consulta leve: só o que fica junto dos carregadores (postos de combustível, shoppings, mercados, estacionamentos)
    q = f"""[out:json][timeout:150];
area["ISO3166-2"="BR-{uf}"]->.a;
nwr["amenity"="charging_station"](area.a)->.ev;
nwr["amenity"="fuel"](around.ev:{MATCH_M})->.fn;
nwr["amenity"="fuel"]["fuel:electricity"="yes"](area.a)->.fe;
nwr["shop"~"^(mall|supermarket|department_store)$"]["opening_hours"](around.ev:450)->.v;
nwr["amenity"="parking"]["opening_hours"](around.ev:150)->.p;
(.ev;.fn;.fe;.v;.p;);
out center tags;"""
    body = urllib.parse.urlencode({"data": q}).encode()
    last = None
    vazios = 0
    for tentativa in range(2):
        for ep in OVERPASS:
            try:
                d = http_json(ep, body)
                if "elements" not in d:
                    raise RuntimeError("resposta sem elements")
                if d.get("remark") and "runtime error" in d["remark"].lower():
                    raise RuntimeError(d["remark"])
                if d["elements"]:
                    return d["elements"]
                # resposta vazia: só aceita se outro servidor confirmar
                vazios += 1
                print(f"  [{uf}] {ep} respondeu vazio ({vazios})", flush=True)
                if vazios >= 2:
                    return []
                continue
            except Exception as e:  # noqa
                last = e
                print(f"  [{uf}] falha em {ep}: {e}", flush=True)
                time.sleep(0 if os.environ.get("OVERPASS_URL") else 5)
        time.sleep(0 if os.environ.get("OVERPASS_URL") else 15)
    raise RuntimeError(f"{uf}: {last}")

def coord(e):
    if "lat" in e and "lon" in e:
        return e["lat"], e["lon"]
    c = e.get("center")
    return (c["lat"], c["lon"]) if c else (None, None)

def hav(a_lat, a_lon, b_lat, b_lon):
    R = 6371000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))

class Grid:
    """Índice espacial simples (~1 km) para buscar vizinhos rápido."""
    def __init__(self):
        self.g = {}
    def _k(self, lat, lon):
        return (int(math.floor(lat * 100)), int(math.floor(lon * 100)))
    def add(self, lat, lon, item):
        self.g.setdefault(self._k(lat, lon), []).append((lat, lon, item))
    def near(self, lat, lon, max_m):
        ki, kj = self._k(lat, lon)
        best, bd = None, float("inf")
        for i in (ki-1, ki, ki+1):
            for j in (kj-1, kj, kj+1):
                for (la, lo, it) in self.g.get((i, j), []):
                    d = hav(lat, lon, la, lo)
                    if d < bd:
                        best, bd = it, d
        return (best, bd) if bd <= max_m else (None, bd)

# ---------- Open Charge Map (opcional) ----------
OCM_SOCKET = [  # (trecho do título, tag OSM)
    ("ccs", "type2_combo"), ("combo", "type2_combo"), ("chademo", "chademo"),
    ("tesla", "tesla_supercharger"), ("gb-t", "gb_t"), ("gbt", "gb_t"),
    ("type 2", "type2"), ("mennekes", "type2"), ("type 1", "type1"), ("j1772", "type1"),
    ("schuko", "schuko"), ("nbr", "nbr14136"), ("tomada", "nbr14136"),
]

def ocm_to_elements(pois):
    out = []
    for p in pois:
        st = p.get("StatusType") or {}
        if st.get("IsOperational") is False:
            continue
        ut = p.get("UsageType") or {}
        if ut.get("IsPrivateIndividual") or (ut.get("ID") in (2, 3, 6)):
            continue
        a = p.get("AddressInfo") or {}
        lat, lon = a.get("Latitude"), a.get("Longitude")
        if lat is None or lon is None:
            continue
        t = {"amenity": "charging_station"}
        if a.get("Title"): t["name"] = a["Title"].strip()
        op = (p.get("OperatorInfo") or {}).get("Title")
        if op and "unknown" not in op.lower() and "desconhecido" not in op.lower():
            t["operator"] = op.strip()
        cost = (p.get("UsageCost") or "").strip()
        lc = norm(cost)
        if lc and any(w in lc for w in ("free", "gratis", "gratuito", "sem custo")):
            t["fee"] = "no"
        elif lc or ut.get("IsPayAtLocation"):
            t["fee"] = "yes"
            if cost: t["charge"] = cost[:80]
        if ut.get("ID") == 4: t["rv:membership"] = "yes"
        if a.get("AccessComments"): t["rv:access_note"] = str(a["AccessComments"]).strip()[:160]
        if a.get("AddressLine1"): t["addr:street"] = a["AddressLine1"].strip()
        if a.get("Town"): t["addr:city"] = a["Town"].strip()
        if a.get("Postcode"): t["addr:postcode"] = str(a["Postcode"]).strip()
        acc = norm(a.get("AccessComments") or "") + " " + norm(p.get("GeneralComments") or "")
        if "24h" in acc or "24 h" in acc or "24 hor" in acc or "24/7" in acc:
            t["opening_hours"] = "24/7"
        socks = {}
        for c in p.get("Connections") or []:
            title = norm(((c.get("ConnectionType") or {}).get("Title")) or "")
            tag = next((v for k, v in OCM_SOCKET if k in title), None)
            if not tag:
                continue
            q = c.get("Quantity") or 1
            socks.setdefault(tag, [0, 0])
            socks[tag][0] += int(q)
            kw = c.get("PowerKW") or 0
            socks[tag][1] = max(socks[tag][1], float(kw))
        for tag, (q, kw) in socks.items():
            t[f"socket:{tag}"] = str(q)
            if kw: t[f"socket:{tag}:output"] = f"{kw:g} kW"
        uf = None
        stp = a.get("StateOrProvince") or ""
        if stp.strip().upper() in UFS: uf = stp.strip().upper()
        else: uf = UF_NOMES.get(norm(stp))
        out.append({"type": "ocm", "id": p.get("ID"), "lat": round(lat, 6), "lon": round(lon, 6),
                    "tags": t, "uf": uf, "src": "ocm"})
    return out

def fetch_ocm(key):
    base = os.environ.get("OCM_URL") or "https://api.openchargemap.io/v3/poi/"
    qs = urllib.parse.urlencode({"output": "json", "countrycode": "BR", "maxresults": 100000,
                                 "compact": "false", "verbose": "false", "key": key})
    return http_json(f"{base}?{qs}", timeout=240)

# ---------- principal ----------
def main():
    os.makedirs(DATA, exist_ok=True)
    anterior = {}
    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        for e in old.get("elements", []):
            if e.get("src") != "ocm":
                anterior.setdefault(e.get("uf"), []).append(e)
    except Exception:
        pass

    vistos, elements, falhas, por_uf = set(), [], [], {}
    fonte_osm = "overpass"
    ontem_ev = sum(1 for es in anterior.values() for e in es if e["tags"].get("amenity") == "charging_station")

    # 1) Fonte principal: mapa completo do Brasil (Geofabrik + osmium), sem depender do Overpass
    gpath = os.environ.get("OSM_GEOJSONSEQ", "")
    if gpath and os.path.exists(gpath) and os.path.getsize(gpath) > 0:
        try:
            geo = osm_from_geojsonseq(gpath)
            n_ev = sum(1 for e in geo if e["tags"].get("amenity") == "charging_station")
            print(f"Mapa do Brasil (Geofabrik): {len(geo)} elementos, {n_ev} eletropostos", flush=True)
            if n_ev < 50 or (ontem_ev > 200 and n_ev < 0.6 * ontem_ev):
                raise RuntimeError(f"poucos eletropostos ({n_ev}; ontem {ontem_ev})")
            elements, fonte_osm = geo, "geofabrik"
        except Exception as ex:
            print(f"Mapa do Brasil indisponível ({ex}): usando Overpass.", flush=True)
            elements = []
    else:
        print("Mapa do Brasil não baixado: usando Overpass.", flush=True)

    limite = time.time() + 60 * float(os.environ.get("OVERPASS_LIMITE_MIN") or 600)
    for i, uf in enumerate(UFS if fonte_osm == "overpass" else []):
        print(f"[{i+1}/27] {uf}…", flush=True)
        try:
            if time.time() > limite:
                raise RuntimeError("tempo do plano B esgotado")
            raw = overpass_uf(uf)
            novos = []
            for e in raw:
                lat, lon = coord(e)
                if lat is None:
                    continue
                novos.append({"type": e["type"], "id": e["id"], "lat": round(lat, 6), "lon": round(lon, 6),
                              "tags": keep_tags(e.get("tags", {})), "uf": uf})
            print(f"  {len(novos)} elementos", flush=True)
            if not novos and anterior.get(uf):
                raise RuntimeError("veio vazio, mas ontem havia dados")
        except Exception as ex:
            print(f"  ERRO: {ex} — mantendo dados anteriores de {uf}", flush=True)
            falhas.append(uf)
            novos = anterior.get(uf, [])
        for e in novos:
            k = f'{e["type"]}/{e["id"]}'
            if k in vistos:
                continue
            vistos.add(k)
            elements.append(e)
        time.sleep(3 if not os.environ.get("OVERPASS_URL") else 0)

    if len(falhas) == len(UFS):
        print("Todos os estados falharam: base de ontem mantida.", flush=True)
        sys.exit(1)

    # Open Charge Map (opcional) — só entra o que não existe no OSM (raio de 60 m)
    ocm_add = 0
    key = os.environ.get("OCM_KEY", "").strip()
    if not key:  # sem segredo no GitHub: usa a chave gravada no próprio site (index.html)
        try:
            import re
            with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
                mk = re.search(r'const OCM_KEY_DEFAULT = "([A-Za-z0-9-]{8,80})"', f.read())
            key = mk.group(1) if mk else ""
        except Exception:
            key = ""
    if key:
        try:
            pois = fetch_ocm(key)
            ocm = ocm_to_elements(pois)
            g = Grid(); gall = Grid()
            for e in elements:
                gall.add(e["lat"], e["lon"], e)
                if e["tags"].get("amenity") == "charging_station":
                    g.add(e["lat"], e["lon"], e)
            for e in ocm:
                dup, _ = g.near(e["lat"], e["lon"], 60)
                if dup:
                    continue
                if not e["uf"]:
                    viz, _ = gall.near(e["lat"], e["lon"], 50000)
                    e["uf"] = viz["uf"] if viz else None
                elements.append(e); g.add(e["lat"], e["lon"], e); ocm_add += 1
            print(f"Open Charge Map: +{ocm_add} pontos novos", flush=True)
        except Exception as ex:
            print(f"Open Charge Map indisponível hoje: {ex}", flush=True)
    else:
        print("OCM_KEY não configurada: usando só OpenStreetMap.", flush=True)

    # Enxuga a base: mantém todo eletroposto, mas só os postos de combustível com recarga
    # (ou a até 120 m de um carregador) e só os shoppings/mercados/estacionamentos com horário
    # que ficam junto de um carregador (usados para informar o horário do local).
    gch = Grid()
    for e in elements:
        if e["tags"].get("amenity") == "charging_station":
            gch.add(e["lat"], e["lon"], e)
    enxuta = []
    for e in elements:
        t = e["tags"]
        if t.get("amenity") == "charging_station":
            enxuta.append(e); continue
        if t.get("amenity") == "fuel":
            own = t.get("fuel:electricity") == "yes" or any(k.startswith("socket:") for k in t)
            if own or gch.near(e["lat"], e["lon"], MATCH_M)[0]:
                enxuta.append(e)
            continue
        lim = 450 if t.get("shop") == "mall" else 150
        if gch.near(e["lat"], e["lon"], lim)[0]:
            enxuta.append(e)
    print(f"Base enxuta: {len(enxuta)} de {len(elements)} elementos", flush=True)
    elements = enxuta

    # Estado (UF) de cada ponto pela malha do IBGE: pontos do mapa do Brasil e do Open Charge Map
    precisa = [e for e in elements if e.get("uf") is None or e.get("src") == "ocm"]
    if precisa:
        loc = UFLocator()
        if loc.ok:
            for e, uf in zip(precisa, loc.locate([(e["lat"], e["lon"]) for e in precisa])):
                if uf: e["uf"] = uf
        else:  # sem malha hoje: usa o estado do ponto mais próximo da base de ontem (~30 km)
            cel = {}
            for es in anterior.values():
                for o in es:
                    if o.get("uf"): cel.setdefault((int(o["lat"] * 10), int(o["lon"] * 10)), o["uf"])
            for e in precisa:
                if e.get("uf"): continue
                ci, cj = int(e["lat"] * 10), int(e["lon"] * 10)
                for r in range(4):
                    viz = [cel.get((ci + a, cj + b)) for a in range(-r, r + 1) for b in range(-r, r + 1)]
                    viz = [v for v in viz if v]
                    if viz:
                        e["uf"] = max(set(viz), key=viz.count); break
        sem = sum(1 for e in elements if not e.get("uf"))
        print(f"Estados atribuídos: {len(precisa) - sem} de {len(precisa)} (sem estado: {sem})", flush=True)

    for e in elements:
        por_uf.setdefault(e.get("uf") or "?", {"eletropostos": 0, "postos_combustivel": 0})
        a_ = e["tags"].get("amenity")
        if a_ in ("charging_station", "fuel"):
            por_uf[e.get("uf") or "?"]["eletropostos" if a_ == "charging_station" else "postos_combustivel"] += 1

    brt = timezone(timedelta(hours=-3))
    agora = datetime.now(brt)
    meta = {
        "atualizado_em": agora.isoformat(timespec="minutes"),
        "total_elementos": len(elements),
        "eletropostos": sum(1 for e in elements if e["tags"].get("amenity") == "charging_station"),
        "postos_combustivel_proximos_ou_com_recarga": sum(1 for e in elements if e["tags"].get("amenity") == "fuel"),
        "open_charge_map_adicionados": ocm_add,
        "estados_com_falha_hoje": falhas,
        "fonte_osm": "mapa completo do Brasil (Geofabrik)" if fonte_osm == "geofabrik" else "Overpass API",
        "por_uf": dict(sorted(por_uf.items())),
        "fontes": ["OpenStreetMap (ODbL)"] + (["Open Charge Map (CC BY-SA 4.0)"] if ocm_add else []),
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "elements": elements}, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    with open(META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"OK: {meta['eletropostos']} eletropostos, {meta['postos_combustivel_proximos_ou_com_recarga']} postos de combustível. Falhas: {falhas or 'nenhuma'}", flush=True)

if __name__ == "__main__":
    main()
