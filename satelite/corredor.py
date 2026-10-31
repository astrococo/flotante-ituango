"""Corredor del río ±15 km alrededor de la barrera (Sentinel-2 L2A, 20 m): área de vegetación flotante por tramo,
para probar si lo que se ve aguas arriba anticipa lo que llega a la barrera. Se combinan los mosaicos 18NUN y 18NVN.
Tramos por distancia en dirección norte-sur desde la barrera (negativo = aguas arriba / sur).
Salidas: datos/satelite/corredor/escenas.csv, zona.npy, ql_<fecha>.png (vista NDVI de control)."""
import os, numpy as np, pandas as pd, collections
from PIL import Image
from comun import catalogo, firmar, leer, BARRERA
OUT = "datos/satelite/corredor"; os.makedirs(OUT, exist_ok=True)
lat, lon = BARRERA
dlat = 15.5 / 111.32; dlon = 4.5 / (111.32 * np.cos(np.radians(lat)))
bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
SH = (int(31000 / 20), int(9000 / 20))                     # grilla de 20 m
yy = np.arange(SH[0])[:, None].repeat(SH[1], 1); km = (SH[0] / 2 - yy) * 0.02   # + norte, − sur
TRAMOS = [(-15, -7.5), (-7.5, -2.5), (-2.5, 0), (0, 2.5), (2.5, 7.5), (7.5, 15)]
items = [i for i in catalogo().search(collections=["sentinel-2-l2a"], intersects={"type": "Point", "coordinates": [lon, lat]},
         bbox=bbox, datetime="2019-01-01/2026-12-31").items() if i.properties.get("s2:mgrs_tile") in ("18NUN", "18NVN")]
por_fecha = collections.defaultdict(list)
for it in items: por_fecha[it.datetime.strftime("%Y-%m-%d")].append(it)
print("fechas:", len(por_fecha), "escenas:", len(items), flush=True)
def banda(it, b):
    a, _, _ = leer(it.assets[b].href, bbox, out_shape=SH); return a.astype("float32")
guard = []                                                   # (fecha, válido, agua, veg) empaquetados
for k, (d, its) in enumerate(sorted(por_fecha.items())):
    try:
        val = np.zeros(SH, bool); nd = np.full(SH, np.nan, "float32"); mw = np.full(SH, np.nan, "float32")
        for it in its:
            it = firmar(it); scl = leer(it.assets["SCL"].href, bbox, out_shape=SH)[0]
            ok = np.isin(scl, [4, 5, 6, 7]) & ~val
            if ok.mean() < 0.02: continue
            off = -1000.0 if float(it.properties.get("s2:processing_baseline", "0")) >= 4 else 0.0
            r = {b: (banda(it, b) + off) / 1e4 for b in ("B03", "B04", "B08", "B11")}
            n_ = (r["B08"] - r["B04"]) / (r["B08"] + r["B04"] + 1e-6); m_ = (r["B03"] - r["B11"]) / (r["B03"] + r["B11"] + 1e-6)
            nd[ok] = n_[ok]; mw[ok] = m_[ok]; val |= ok
        if val.mean() < 0.3: continue
        guard.append((d, np.packbits(val), np.packbits(val & (mw > 0)), np.packbits(val & (nd >= 0.30))))
        if k % 20 == 0: print(k, d, round(float(val.mean()), 2), flush=True)
    except Exception as e:
        print("error", d, str(e)[:150], flush=True)
un = lambda a: np.unpackbits(a)[:SH[0] * SH[1]].reshape(SH).astype(bool)
nv = np.zeros(SH, "int32"); nw = np.zeros(SH, "int32")
for d, v, w, g in guard: nv += un(v); nw += un(w)
freq = np.where(nv > 0, nw / np.maximum(nv, 1), 0); Z = (freq >= 0.5) & (nv >= 10)
np.save(f"{OUT}/zona.npy", Z)
rows = []
for d, v, w, g in guard:
    v = un(v); g = un(g); row = dict(fecha=d)
    for a, b in TRAMOS:
        m = Z & (km >= a) & (km < b); row[f"t{a}_{b}_area_px"] = int(m.sum()); row[f"t{a}_{b}_valid_px"] = int((m & v).sum()); row[f"t{a}_{b}_veg_px"] = int((m & v & g).sum())
    rows.append(row)
pd.DataFrame(rows).to_csv(f"{OUT}/escenas.csv", index=False)
img = np.zeros(SH + (3,), "uint8"); img[Z] = (40, 90, 160); img[(np.abs(km) < 0.06)] = (255, 0, 0)
Image.fromarray(img).save(f"{OUT}/zona.png")
print("listo", len(rows), "área por tramo (ha):", {f"{a}..{b}": round(float((Z & (km >= a) & (km < b)).sum()) * 0.04, 1) for a, b in TRAMOS}, flush=True)
