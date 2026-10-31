"""Lluvia diaria satelital desde ClimateSERV (NASA/USAID SERVIR): CHIRPS v2.0 (datatype 0) e IMERG (datatype 26).
Promedio areal (operationtype 5) sobre los polígonos 'cola' y 'media', un trabajo por año y por fuente."""
import json, os, time, urllib.parse, urllib.request, datetime as dt, pandas as pd
OUT = "../datos/lluvia"; os.makedirs(OUT, exist_ok=True)
BASE = "https://climateserv.servirglobal.net/chirps/"
AREAS = {"cola": (-76.00, 6.55, -75.60, 7.00), "media": (-76.10, 5.70, -75.40, 7.00)}   # lon0, lat0, lon1, lat1
FUENTES = {"chirps": 0, "imerg": 26}
def call(metodo, **p):
    url = BASE + metodo + "/?" + urllib.parse.urlencode(p)
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "flotante-ituango"}), timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print("   reintento", metodo, e, flush=True); time.sleep(15 * (k + 1))
    raise RuntimeError("sin respuesta " + metodo)
def poligono(b):
    x0, y0, x1, y1 = b
    return json.dumps({"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]})
series = {}
hoy = dt.date.today()
for fuente, code in FUENTES.items():
    for area, b in AREAS.items():
        partes = []
        for y in range(2019, hoy.year + 1):
            ini = f"01/01/{y}"; fin = f"12/31/{y}" if y < hoy.year else (hoy - dt.timedelta(days=2)).strftime("%m/%d/%Y")
            try:
                jid = call("submitDataRequest", datatype=code, begintime=ini, endtime=fin, intervaltype=0, operationtype=5, geometry=poligono(b))
                jid = jid[0] if isinstance(jid, list) else jid
                t0 = time.time()
                while True:
                    pr = call("getDataRequestProgress", id=jid); pr = pr[0] if isinstance(pr, list) else pr
                    if float(pr) >= 100 or float(pr) < 0 or time.time() - t0 > 900: break
                    time.sleep(4)
                if float(pr) < 0: print(f"   {fuente} {area} {y}: error del servidor", flush=True); continue
                d = call("getDataFromRequest", id=jid)
                rows = [(dt.datetime.utcfromtimestamp(int(float(r["epochTime"]))).date(), list(r["value"].values())[0]) for r in d.get("data", [])]
                s = pd.Series({pd.Timestamp(a): (v if v is not None and v > -9000 else None) for a, v in rows}, dtype="float64")
                partes.append(s); print(f"   {fuente} {area} {y}: {s.notna().sum()} días, media {s.mean():.2f}, {time.time()-t0:.0f} s", flush=True)
            except Exception as e:
                print(f"   {fuente} {area} {y}: fallo {e}", flush=True)
        if partes:
            s = pd.concat(partes).sort_index(); series[f"{fuente}_{area}"] = s[~s.index.duplicated()]
D = pd.DataFrame(series); D.index.name = "fecha"
D.round(2).to_csv(f"{OUT}/climateserv_diario.csv"); print("total", D.shape, D.index.min(), D.index.max()); print(D.describe().round(2))
