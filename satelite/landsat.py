"""Landsat 8/9 Colección 2 Nivel 2 (30 m, Planetary Computer, público) sobre la grilla y zona de agua de Sentinel-2.
Vegetación flotante: NDVI ≥ 0,30 en el núcleo de la zona de agua. Nubes/sombras: QA_PIXEL bits 1–4."""
import os, numpy as np, pandas as pd, rasterio
from rasterio.warp import reproject, Resampling
from comun import catalogo, firmar, BARRERA
from comun_grilla import *
OUT = "datos/satelite/landsat"; os.makedirs(OUT, exist_ok=True)
lat, lon = BARRERA
items = [i for i in catalogo().search(collections=["landsat-c2-l2"], intersects={"type": "Point", "coordinates": [lon, lat]},
                                      datetime="2019-01-01/2026-10-31", query={"platform": {"in": ["landsat-8", "landsat-9"]}}).items()]
items = sorted(items, key=lambda i: i.datetime); print("escenas Landsat:", len(items), flush=True)
def leer(href, res=Resampling.bilinear, dtype="float32", nod=0):
    dst = np.zeros(SH, dtype)
    with rasterio.open(href) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=TR, dst_crs=CRS, resampling=res, src_nodata=nod, dst_nodata=0)
    return dst
rows = []
for k, it in enumerate(items):
    try:
        it = firmar(it)
        qa = leer(it.assets["qa_pixel"].href, Resampling.nearest, "uint16", 1)
        ok = (qa > 1) & ((qa & 0b11110) == 0)
        if (ok & Z).sum() < 0.7 * Z.sum(): continue
        sr = lambda b: leer(it.assets[b].href) * 0.0000275 - 0.2
        red, nir, grn, sw = sr("red"), sr("nir08"), sr("green"), sr("swir16")
        ndvi = (nir - red) / (nir + red + 1e-6); valid = ok & Z & np.isfinite(ndvi)
        row = dict(fecha=it.datetime.strftime("%Y-%m-%d"), plat=it.properties.get("platform"), id=it.id)
        for lado, M in LADOS:
            m = valid & M; row[f"{lado}_valid_px"] = int(m.sum()); row[f"{lado}_area_px"] = int((Z & M).sum())
            for t in (20, 30, 40): row[f"{lado}_ndvi{t}"] = int((m & (ndvi >= t / 100)).sum())
        rows.append(row); print(k, row["fecha"], row["plat"], round(row["total_ndvi30"] / max(1, row["total_valid_px"]) * row["total_area_px"] / 100, 1), "ha", flush=True)
    except Exception as e:
        print("error", it.id, str(e)[:160], flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas_landsat.csv", index=False); print("listo", len(rows), flush=True)
