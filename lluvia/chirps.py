"""CHIRPS v2.0 diario (0,05°) vía NOAA ERDDAP (dataset chirps20GlobalDailyP05), recorte por área y año en CSV.
Promedio areal diario de las áreas 'cola' y 'media'. ERDDAP publica con ~4 meses de rezago."""
import io, os, time, urllib.request, datetime as dt, pandas as pd
OUT = "../datos/lluvia"; os.makedirs(OUT, exist_ok=True)
AREAS = {"cola": (6.55, 7.00, -76.00, -75.60), "media": (5.70, 7.00, -76.10, -75.40)}   # lat0, lat1, lon0, lon1
SERV = ["https://coastwatch.pfeg.noaa.gov/erddap", "https://upwell.pfeg.noaa.gov/erddap"]
def get(path):
    for k in range(6):
        for s in SERV:
            try:
                t = time.time()
                with urllib.request.urlopen(urllib.request.Request(s + path, headers={"User-Agent": "flotante-ituango"}), timeout=300) as r:
                    txt = r.read().decode(); print("  ", s.split("/")[2], f"{len(txt)/1e6:.1f} MB", f"{time.time()-t:.0f} s", flush=True); return txt
            except Exception as e:
                print("   reintento", s.split("/")[2], e, flush=True)
        time.sleep(30 * (k + 1))
    raise RuntimeError("ERDDAP sin respuesta")
res = {}
hoy = dt.date.today()
for y in range(2019, hoy.year + 1):
    t0, t1 = f"{y}-01-01", (f"{y}-12-31" if y < hoy.year else f"{y}-06-30")
    for n, (a0, a1, o0, o1) in AREAS.items():
        print(y, n, flush=True)
        try:
            txt = get(f"/griddap/chirps20GlobalDailyP05.csv?precip%5B({t0}):1:({t1})%5D%5B({a0}):1:({a1})%5D%5B({o0}):1:({o1})%5D")
        except Exception as e:
            print("   sin datos", y, n, e, flush=True); continue
        df = pd.read_csv(io.StringIO(txt), skiprows=[1])            # segunda fila = unidades
        df["fecha"] = pd.to_datetime(df["time"]).dt.tz_localize(None).dt.normalize()
        s = df.groupby("fecha")["precip"].mean()
        res.setdefault(n, []).append(s)
        print("   días", len(s), "celdas/día", int(len(df) / max(1, len(s))), "media", round(s.mean(), 2), flush=True)
D = pd.DataFrame({f"chirps_{n}": pd.concat(v) for n, v in res.items()}).sort_index(); D.index.name = "fecha"
D = D[~D.index.duplicated()]
D.round(2).to_csv(f"{OUT}/chirps_diario.csv"); print("total", len(D), D.index.min(), D.index.max()); print(D.describe().round(2))
