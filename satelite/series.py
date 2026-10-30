"""Fase 2: serie temporal de cobertura flotante alrededor de la barrera (Sentinel-2 L2A, 10 m).
Salidas (datos/satelite/series/):
  escenas.csv          una fila por escena: píxeles válidos de la zona de agua y conteos por clase (aguas arriba / abajo)
  hist_<fecha>.npy     histograma 2D NDVI×FDI de los píxeles válidos de la zona de agua (para fijar umbrales a posteriori)
  zona_agua.npy        frecuencia de agua (MNDWI>0) por píxel; zona = frecuencia >= 0,20 dentro de 2,5 km
  frec_veg_<año>.npy   frecuencia anual de vegetación flotante por píxel
  ql_<fecha>.jpg       vista previa RGB de escenas despejadas (control visual)
Índices: NDVI=(B8−B4)/(B8+B4); MNDWI=(B3−B11)/(B3+B11);
FDI (Biermann et al., 2020) = R_B8 − [R_B6 + (R_B11 − R_B6)·(λ8−λ4)/(λ11−λ4)·10], λ4=665, λ8=833, λ11=1614 nm."""
import os, json, numpy as np, pandas as pd
from PIL import Image
from comun import *
OUT = "datos/satelite/series"; os.makedirs(OUT, exist_ok=True)
lat, lon = BARRERA; HALF = 2.6
bbox = bbox_grados(lat, lon, HALF)
cat = catalogo()
items = [i for i in cat.search(collections=["sentinel-2-l2a"], intersects={"type": "Point", "coordinates": [lon, lat]},
                                datetime="2019-01-01/2026-10-31").items() if i.properties.get("s2:mgrs_tile") == "18NUN"]
items = sorted(items, key=lambda x: x.datetime); print("escenas:", len(items), flush=True)
# grilla de 10 m (desde B04)
it0 = firmar(items[-1]); a, tr10, crs = leer(it0.assets["B04"].href, bbox); SH = a.shape; print("grilla", SH, crs, flush=True)
from rasterio.transform import rowcol
from pyproj import Transformer
X, Y = Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat); r0, c0 = rowcol(tr10, X, Y)
yy, xx = np.mgrid[0:SH[0], 0:SH[1]]; dist = np.hypot((yy - r0) * 10, (xx - c0) * 10); dentro = dist <= 2500
sur = yy > r0                                   # el flujo va de sur a norte: aguas arriba = sur (filas mayores)
L4, L8, L11 = 665.0, 833.0, 1614.0
cubo = []                                        # (fecha, id, valid, ndvi, fdi, mndwi) en int16
for k, it in enumerate(items):
    try:
        it = firmar(it)
        scl, _, _ = leer(it.assets["SCL"].href, bbox, out_shape=SH)
        cubre = scl > 0
        if cubre[dentro].mean() < 0.5: continue
        val = np.isin(scl, [4, 5, 6, 7]) & dentro
        fv = val[dentro].sum() / max(1, (cubre & dentro).sum())
        if fv < 0.30: continue
        B = {b: reflectancia(it, b, bbox, SH) for b in ("B02", "B03", "B04", "B06", "B08", "B11")}
        ndvi = (B["B08"] - B["B04"]) / (B["B08"] + B["B04"] + 1e-6)
        mndwi = (B["B03"] - B["B11"]) / (B["B03"] + B["B11"] + 1e-6)
        fdi = B["B08"] - (B["B06"] + (B["B11"] - B["B06"]) * (L8 - L4) / (L11 - L4) * 10)
        bad = np.isnan(ndvi) | np.isnan(fdi) | np.isnan(mndwi); val &= ~bad
        q = lambda v, s: np.where(val, np.clip(np.round(v * s), -32000, 32000), -32768).astype("int16")
        d = it.datetime.strftime("%Y-%m-%d")
        cubo.append((d, it.id, q(ndvi, 10000), q(fdi, 100000), q(mndwi, 10000)))
        if fv > 0.85:
            rgb = np.dstack([B["B04"], B["B03"], B["B02"]]); rgb = (np.clip(np.nan_to_num(rgb) / 0.25, 0, 1) ** (1 / 1.8) * 255).astype("uint8")
            Image.fromarray(rgb).save(f"{OUT}/ql_{d}.jpg", quality=82)
        if k % 25 == 0: print(k, d, round(float(fv), 2), flush=True)
    except Exception as e:
        print("error", it.id, e, flush=True)
print("escenas usadas:", len(cubo), flush=True)
# zona de agua: frecuencia de MNDWI>0 entre observaciones válidas
nv = np.zeros(SH, "int32"); nw = np.zeros(SH, "int32")
for _, _, nd, fd, mw in cubo:
    v = mw != -32768; nv += v; nw += v & (mw > 0)
freq = np.where(nv > 0, nw / np.maximum(nv, 1), 0).astype("float32")
np.save(f"{OUT}/zona_agua.npy", freq); np.save(f"{OUT}/n_obs.npy", nv)
json.dump(dict(bbox=bbox, shape=list(SH), transform=list(tr10)[:6], crs=str(crs), barrera_px=[int(r0), int(c0)]), open(f"{OUT}/grilla.json", "w"))
ZONAS = {f"z{int(t*100)}": (freq >= t) & dentro for t in (0.10, 0.20, 0.50)}
NB = np.linspace(-0.5, 1.0, 61); FB = np.linspace(-0.10, 0.20, 61)
rows = []; fveg = {}
for d, iid, nd, fd, mw in cubo:
    v = nd != -32768; ndvi = nd / 10000.0; fdi = fd / 100000.0
    Z = ZONAS["z20"]; vz = v & Z
    H, _, _ = np.histogram2d(ndvi[vz], fdi[vz], bins=[NB, FB]); np.save(f"{OUT}/hist_{d}.npy", H.astype("int32"))
    row = dict(fecha=d, id=iid)
    for zn, Zm in ZONAS.items():
        for lado, M in (("arriba", sur), ("abajo", ~sur), ("total", np.ones(SH, bool))):
            m = Zm & M; vv = v & m
            row[f"{zn}_{lado}_area_px"] = int(m.sum()); row[f"{zn}_{lado}_valid_px"] = int(vv.sum())
            for t in (0.10, 0.20, 0.30, 0.40, 0.50):
                row[f"{zn}_{lado}_ndvi{int(t*100)}"] = int((vv & (ndvi >= t)).sum())
            for t in (0.00, 0.01, 0.02, 0.03, 0.05):
                row[f"{zn}_{lado}_fdi{int(t*100)}_nv"] = int((vv & (fdi >= t) & (ndvi < 0.30)).sum())
    rows.append(row)
    y = d[:4]; fv_ = fveg.setdefault(y, [np.zeros(SH, "int32"), np.zeros(SH, "int32")])
    fv_[0] += v & ZONAS["z10"]; fv_[1] += v & ZONAS["z10"] & (ndvi >= 0.30)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas.csv", index=False)
for y, (n, c) in fveg.items():
    np.save(f"{OUT}/frec_veg_{y}.npy", np.where(n > 0, c / np.maximum(n, 1), np.nan).astype("float32"))
print("listo", len(rows), flush=True)
