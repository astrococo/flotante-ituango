"""Sentinel-1 RTC (radar, sin nubes) sobre la misma grilla y zona de agua del análisis Sentinel-2.
Salida datos/satelite/s1/escenas_s1.csv: por escena, conteos de píxeles de la zona (núcleo z50) con VH por encima de
umbrales (−24 a −12 dB) y medias de VV/VH en dB, aguas arriba / abajo / total. La vegetación flotante aumenta la
retrodispersión en VH (dispersión de volumen) frente al agua lisa."""
import os, json, numpy as np, pandas as pd, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from comun import catalogo, firmar, BARRERA
R = "datos/satelite"; OUT = f"{R}/s1"; os.makedirs(OUT, exist_ok=True)
SER = "../datos/satelite/series"                       # productos de Sentinel-2 ya en el repositorio
G = json.load(open(f"{SER}/grilla.json")); SH = tuple(G["shape"]); TR = Affine(*G["transform"]); CRS = G["crs"]
freq = np.load(f"{SER}/zona_agua.npy")
r0, c0 = G["barrera_px"]; yy, xx = np.mgrid[0:SH[0], 0:SH[1]]
dentro = np.hypot((yy - r0) * 10, (xx - c0) * 10) <= 2500
Z = (freq >= 0.5) & dentro; SUR = yy > r0
lat, lon = BARRERA
items = list(catalogo().search(collections=["sentinel-1-rtc"], intersects={"type": "Point", "coordinates": [lon, lat]},
                               datetime="2019-01-01/2026-10-31").items())
items = sorted(items, key=lambda i: i.datetime); print("escenas S1:", len(items), flush=True)
def leer(href):
    dst = np.full(SH, np.nan, "float32")
    with rasterio.open(href) as src:
        reproject(source=rasterio.band(src, 1), destination=dst, dst_transform=TR, dst_crs=CRS, resampling=Resampling.average, src_nodata=0, dst_nodata=np.nan)
    return dst
rows = []
for k, it in enumerate(items):
    try:
        it = firmar(it)
        vh = leer(it.assets["vh"].href); vv = leer(it.assets["vv"].href)
        vh_db = 10 * np.log10(np.where(vh > 0, vh, np.nan)); vv_db = 10 * np.log10(np.where(vv > 0, vv, np.nan))
        v = Z & np.isfinite(vh_db) & np.isfinite(vv_db)
        if v.sum() < 0.8 * Z.sum(): continue
        row = dict(fecha=it.datetime.strftime("%Y-%m-%d"), hora=it.datetime.strftime("%H:%M"), id=it.id,
                   orbita=it.properties.get("sat:orbit_state"), rel=it.properties.get("sat:relative_orbit"), plat=it.properties.get("platform"))
        for lado, M in (("total", np.ones(SH, bool)), ("arriba", SUR), ("abajo", ~SUR)):
            m = v & M; row[f"{lado}_valid_px"] = int(m.sum()); row[f"{lado}_area_px"] = int((Z & M).sum())
            row[f"{lado}_vh_med"] = round(float(np.nanmedian(vh_db[m])), 2); row[f"{lado}_vv_med"] = round(float(np.nanmedian(vv_db[m])), 2)
            for t in range(-24, -11):
                row[f"{lado}_vh{abs(t)}"] = int((m & (vh_db >= t)).sum())
        rows.append(row)
        if k % 20 == 0: print(k, row["fecha"], row["plat"], row["total_vh_med"], flush=True)
    except Exception as e:
        print("error", it.id, e, flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas_s1.csv", index=False); print("listo", len(rows), flush=True)
