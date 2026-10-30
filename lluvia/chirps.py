"""CHIRPS v2.0 diario (0,05°) desde el servidor del Climate Hazards Center (UCSB), lectura por ventana de los COG.
Promedio areal por día en las áreas 'cola' y 'media'. Los días aún no publicados en la versión final se omiten."""
import os, time, datetime as dt, numpy as np, pandas as pd, rasterio
from rasterio.windows import from_bounds
from concurrent.futures import ThreadPoolExecutor
OUT = "../datos/lluvia"; os.makedirs(OUT, exist_ok=True)
AREAS = {"cola": (-76.00, 6.55, -75.60, 7.00), "media": (-76.10, 5.70, -75.40, 7.00)}   # lon0, lat0, lon1, lat1
BASE = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/{y}/chirps-v2.0.{y}.{m:02d}.{d:02d}.cog"
prev = f"{OUT}/chirps_diario.csv"
hecho = pd.read_csv(prev, parse_dates=["fecha"]).set_index("fecha") if os.path.exists(prev) else pd.DataFrame()
def uno(day):
    url = BASE.format(y=day.year, m=day.month, d=day.day)
    for k in range(3):
        try:
            with rasterio.Env(GDAL_HTTP_TIMEOUT=30, GDAL_HTTP_MAX_RETRY=2), rasterio.open(url) as src:
                r = {}
                for n, b in AREAS.items():
                    a = src.read(1, window=from_bounds(*b, transform=src.transform)).astype(float)
                    a[a < 0] = np.nan; r["chirps_" + n] = float(np.nanmean(a))
                return day, r
        except Exception as e:
            if "404" in str(e) or "not recognized" in str(e) or "No such file" in str(e): return day, None
            time.sleep(3 * (k + 1))
    return day, None
dias = pd.date_range("2019-01-01", dt.date.today() - dt.timedelta(days=3))
faltan = [d for d in dias if d not in hecho.index]
print("días por descargar:", len(faltan))
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
res = {}
with ThreadPoolExecutor(12) as ex:
    for i, (d, r) in enumerate(ex.map(uno, faltan)):
        if r: res[d] = r
        if i % 250 == 0:
            print(i, d.date(), r, flush=True)
            if res:   # guardado parcial: una ejecución lenta no pierde lo descargado
                tmp = pd.DataFrame.from_dict(res, orient="index"); tmp.index.name = "fecha"
                pd.concat([hecho, tmp]).sort_index().round(2).to_csv(prev)
new = pd.DataFrame.from_dict(res, orient="index"); new.index.name = "fecha"
D = pd.concat([hecho, new]).sort_index(); D = D[~D.index.duplicated(keep="last")]
D.round(2).to_csv(prev); print("total días:", len(D), D.index.min(), D.index.max()); print(D.describe().round(2))
