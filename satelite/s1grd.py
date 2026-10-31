"""Sentinel-1 GRD (público, sin corrección de terreno) proyectado con sus GCP y corregido con un desplazamiento
empírico por escena: se busca el corrimiento (±1,2 km) que mejor alinea el agua del radar (VV bajo) con la
frecuencia de agua de Sentinel-2. Se reporta la calidad de la alineación (correlación) para filtrar escenas."""
import os, numpy as np, pandas as pd, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from scipy.ndimage import median_filter
from comun import catalogo, firmar, BARRERA
from comun_grilla import *
OUT = "datos/satelite/s1"; os.makedirs(OUT, exist_ok=True)
PAD = 120                                         # 1,2 km de margen para buscar el corrimiento
SHP = (SH[0] + 2 * PAD, SH[1] + 2 * PAD); TRP = TR * Affine.translation(-PAD, -PAD)
lat, lon = BARRERA
items = sorted(catalogo().search(collections=["sentinel-1-grd"], intersects={"type": "Point", "coordinates": [lon, lat]},
                                 datetime="2019-01-01/2026-10-31").items(), key=lambda i: i.datetime)
print("escenas S1 GRD:", len(items), flush=True)
ref = np.where(DENTRO | True, FREQ, 0).astype("float32"); ref = (ref - ref.mean()) / (ref.std() + 1e-6)
def leer(href):
    dst = np.full(SHP, np.nan, "float32")
    with rasterio.open(href) as src:
        g, gcrs = src.gcps
        reproject(rasterio.band(src, 1), dst, gcps=g, src_crs=gcrs, dst_transform=TRP, dst_crs=CRS, resampling=Resampling.average, src_nodata=0, dst_nodata=np.nan)
    return dst
rows = []
for k, it in enumerate(items):
    try:
        it = firmar(it)
        vv = leer(it.assets["vv"].href); vh = leer(it.assets["vh"].href)
        if np.isnan(vv[PAD:-PAD, PAD:-PAD][Z]).mean() > 0.2: continue
        vvd = median_filter(10 * np.log10(np.where(vv > 0, vv, np.nan)), 5); vhd = median_filter(10 * np.log10(np.where(vh > 0, vh, np.nan)), 5)
        w = -np.nan_to_num(vvd, nan=np.nanmedian(vvd))       # agua = VV bajo
        best = (-9, 0, 0)
        for dy in range(-PAD, PAD + 1, 4):
            for dx in range(-PAD, PAD + 1, 4):
                c = w[PAD + dy:PAD + dy + SH[0], PAD + dx:PAD + dx + SH[1]]
                cc = float(((c - c.mean()) / (c.std() + 1e-6) * ref).mean())
                if cc > best[0]: best = (cc, dy, dx)
        cc0, dy0, dx0 = best
        for dy in range(dy0 - 3, dy0 + 4):                    # refinamiento a 10 m
            for dx in range(dx0 - 3, dx0 + 4):
                if abs(dy) > PAD or abs(dx) > PAD: continue
                c = w[PAD + dy:PAD + dy + SH[0], PAD + dx:PAD + dx + SH[1]]
                cc = float(((c - c.mean()) / (c.std() + 1e-6) * ref).mean())
                if cc > best[0]: best = (cc, dy, dx)
        cc, dy, dx = best
        VH = vhd[PAD + dy:PAD + dy + SH[0], PAD + dx:PAD + dx + SH[1]]; VV = vvd[PAD + dy:PAD + dy + SH[0], PAD + dx:PAD + dx + SH[1]]
        v = Z & np.isfinite(VH) & np.isfinite(VV)
        row = dict(fecha=it.datetime.strftime("%Y-%m-%d"), hora=it.datetime.strftime("%H:%M"), plat=it.properties.get("platform"),
                   orbita=it.properties.get("sat:orbit_state"), rel=it.properties.get("sat:relative_orbit"), corr=round(cc, 3), dy_m=dy * 10, dx_m=dx * 10)
        for lado, M in LADOS:
            m = v & M; row[f"{lado}_valid_px"] = int(m.sum()); row[f"{lado}_area_px"] = int((Z & M).sum())
            row[f"{lado}_vh_med"] = round(float(np.nanmedian(VH[m])), 2) if m.any() else None
            for t in range(-26, -11): row[f"{lado}_vh{abs(t)}"] = int((m & (VH >= t)).sum())
        rows.append(row)
        if k % 15 == 0: print(k, row["fecha"], row["orbita"], "corr", row["corr"], "desplazamiento", row["dy_m"], row["dx_m"], flush=True)
    except Exception as e:
        print("error", it.id, str(e)[:160], flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas_s1grd.csv", index=False); print("listo", len(rows), flush=True)
