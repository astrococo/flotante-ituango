"""Fase 1: disponibilidad de escenas, frecuencia de agua y composiciones RGB alrededor de la barrera."""
import json, os, numpy as np, pandas as pd, rasterio
from PIL import Image
from comun import *
OUT = "datos/satelite/explorar"; os.makedirs(OUT, exist_ok=True)
lat, lon = BARRERA
bbox = bbox_grados(lat, lon, 6.0)                       # caja de 12 × 12 km
cat = catalogo()
items = list(cat.search(collections=["sentinel-2-l2a"], intersects={"type": "Point", "coordinates": [lon, lat]},
                        datetime="2019-01-01/2026-10-31").items())
print("escenas encontradas:", len(items))
tiles = pd.Series([i.properties.get("s2:mgrs_tile") for i in items]).value_counts(); print(tiles)
TILE = tiles.index[0]; items = [i for i in items if i.properties.get("s2:mgrs_tile") == TILE]
print("tile usado:", TILE, len(items))
rows = []; ref = None; agua = None; nval = None
for it in sorted(items, key=lambda x: x.datetime):
    try:
        it = firmar(it)
        scl, tr, crs = leer(it.assets["SCL"].href, bbox)
    except Exception as e:
        print("error", it.id, e); continue
    if ref is None: ref = scl.shape; agua = np.zeros(ref, "int32"); nval = np.zeros(ref, "int32")
    if scl.shape != ref:
        scl = np.array(Image.fromarray(scl).resize((ref[1], ref[0]), Image.NEAREST))
    ok = np.isin(scl, list(SCL_OK)); cover = float((scl > 0).mean())
    fr = float(ok.sum() / max(1, (scl > 0).sum()))
    rows.append(dict(id=it.id, fecha=it.datetime.strftime("%Y-%m-%d"), tile=it.properties.get("s2:mgrs_tile"), nube_escena=it.properties.get("eo:cloud_cover"),
                     cobertura=round(cover, 3), validos=round(fr, 3), agua=round(float((scl == 6).sum() / max(1, ok.sum())), 3)))
    if fr > 0.3:
        agua += (scl == 6); nval += ok
df = pd.DataFrame(rows); df.to_csv(f"{OUT}/escenas.csv", index=False)
print(df.groupby(df.fecha.str[:4]).agg(n=("id", "size"), claras=("validos", lambda s: int((s > 0.7).sum()))))
freq = np.where(nval > 0, agua / np.maximum(nval, 1), np.nan)
np.save(f"{OUT}/frecuencia_agua.npy", freq); np.save(f"{OUT}/n_validos.npy", nval)
img = (np.nan_to_num(freq) * 255).astype("uint8"); Image.fromarray(img).save(f"{OUT}/frecuencia_agua.png")
json.dump(dict(bbox=bbox, shape=list(ref), transform=list(tr)[:6], crs=str(crs)), open(f"{OUT}/grilla.json", "w"))
# composiciones RGB de las escenas más claras (una por año y por semestre)
df["sem"] = df.fecha.str[:4] + "-" + np.where(df.fecha.str[5:7].astype(int) <= 6, "1", "2")
best = df[(df.validos > 0.8)].sort_values("validos", ascending=False).groupby("sem").head(2).sort_values("fecha")
sel = {r.id for r in best.itertuples()}
for it in items:
    if it.id not in sel: continue
    it = firmar(it)
    bands = [reflectancia(it, b, bbox, ref) for b in ("B04", "B03", "B02")]
    rgb = np.dstack(bands); rgb = np.clip(rgb / 0.25, 0, 1); rgb = (np.nan_to_num(rgb) ** (1 / 1.8) * 255).astype("uint8")
    d = it.datetime.strftime("%Y-%m-%d"); Image.fromarray(rgb).save(f"{OUT}/rgb_{d}.png")
    nir = reflectancia(it, "B08", bbox, ref); ndvi = (nir - bands[0]) / (nir + bands[0] + 1e-6)
    Image.fromarray((np.clip((np.nan_to_num(ndvi) + 0.2) / 1.0, 0, 1) * 255).astype("uint8")).save(f"{OUT}/ndvi_{d}.png")
    print("rgb", d, it.properties.get("s2:mgrs_tile"))
best.to_csv(f"{OUT}/escenas_rgb.csv", index=False)
