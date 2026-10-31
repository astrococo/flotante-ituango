"""Área de vegetación flotante por margen del cauce (derecha = oriental, donde se extrae) con Sentinel-2 y Landsat 8/9,
sobre la misma grilla y zona de agua de la serie publicada. Salida: datos/satelite/margenes/escenas_{s2,landsat}.csv"""
import os, numpy as np, pandas as pd, rasterio
from rasterio.warp import reproject, Resampling
from comun import catalogo, firmar, BARRERA, reflectancia, leer as leer_s2, bbox_grados
from comun_grilla import SH, TR, CRS, Z, LADOS
from zonas_margen import SUBZ
OUT = "datos/satelite/margenes"; os.makedirs(OUT, exist_ok=True)
lat, lon = BARRERA; bbox = bbox_grados(lat, lon, 2.6)
ZONAS = dict(LADOS) | SUBZ
def fila(base, ndvi, valid, umbrales):
    for zn, M in ZONAS.items():
        m = valid & M & Z; base[f"{zn}_valid_px"] = int(m.sum()); base[f"{zn}_area_px"] = int((Z & M).sum())
        for t in umbrales: base[f"{zn}_ndvi{t}"] = int((m & (ndvi >= t / 100)).sum())
    return base
cat = catalogo()
# Sentinel-2: mismos criterios que la serie (≥ 50 % del núcleo cubierto, ≥ 30 % válido)
items = sorted([i for i in cat.search(collections=["sentinel-2-l2a"], intersects={"type": "Point", "coordinates": [lon, lat]},
               datetime="2019-01-01/2026-12-31").items() if i.properties.get("s2:mgrs_tile") == "18NUN"], key=lambda x: x.datetime)
print("S2:", len(items), flush=True); rows = []
for k, it in enumerate(items):
    try:
        it = firmar(it); scl, _, _ = leer_s2(it.assets["SCL"].href, bbox, out_shape=SH)
        if (scl > 0)[Z].mean() < 0.5: continue
        val = np.isin(scl, [4, 5, 6, 7]) & Z
        if val.sum() < 0.3 * Z.sum(): continue
        r4, r8 = reflectancia(it, "B04", bbox, SH), reflectancia(it, "B08", bbox, SH)
        ndvi = (r8 - r4) / (r8 + r4 + 1e-6); val &= np.isfinite(ndvi)
        rows.append(fila(dict(fecha=it.datetime.strftime("%Y-%m-%d"), id=it.id), ndvi, val, (30,)))
        if k % 25 == 0: print(k, rows[-1]["fecha"], flush=True)
    except Exception as e: print("error", it.id, str(e)[:160], flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas_s2.csv", index=False); print("S2 listo", len(rows), flush=True)
# Landsat 8/9 (QA_PIXEL bits 1–4 = nube/sombra), NDVI ≥ 0,40 (calibrado contra Sentinel-2)
def leer(href, res=Resampling.bilinear, dtype="float32", nod=0):
    dst = np.zeros(SH, dtype)
    with rasterio.open(href) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=TR, dst_crs=CRS, resampling=res, src_nodata=nod, dst_nodata=0)
    return dst
items = sorted(cat.search(collections=["landsat-c2-l2"], intersects={"type": "Point", "coordinates": [lon, lat]},
               datetime="2019-01-01/2026-12-31", query={"platform": {"in": ["landsat-8", "landsat-9"]}}).items(), key=lambda i: i.datetime)
print("Landsat:", len(items), flush=True); rows = []
for k, it in enumerate(items):
    try:
        it = firmar(it); qa = leer(it.assets["qa_pixel"].href, Resampling.nearest, "uint16", 1)
        ok = (qa > 1) & ((qa & 0b11110) == 0)
        if (ok & Z).sum() < 0.7 * Z.sum(): continue
        sr = lambda b: leer(it.assets[b].href) * 0.0000275 - 0.2
        red, nir = sr("red"), sr("nir08"); ndvi = (nir - red) / (nir + red + 1e-6)
        rows.append(fila(dict(fecha=it.datetime.strftime("%Y-%m-%d"), id=it.id), ndvi, ok & Z & np.isfinite(ndvi), (40,)))
    except Exception as e: print("error", it.id, str(e)[:160], flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas_landsat.csv", index=False); print("Landsat listo", len(rows), flush=True)
