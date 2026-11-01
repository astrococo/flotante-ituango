"""Radar Sentinel-1 RTC calibrado píxel a píxel contra Sentinel-2: un clasificador aprende a reconocer la vegetación
flotante con VV, VH y su textura, usando como verdad las máscaras de Sentinel-2 de fechas cercanas (±2 días).
Validación: dejando un año fuera. Salidas: datos/satelite/s1/escenas_s1ml.csv, validacion_s1ml.json y vistas VH para el visor."""
import os, json, numpy as np, pandas as pd, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from scipy import ndimage
from scipy.stats import spearmanr
from PIL import Image
from sklearn.ensemble import HistGradientBoostingClassifier
from comun import catalogo, firmar, BARRERA
from comun_grilla import SH, TR, CRS, Z, SUR, G
OUT = "datos/satelite/s1"; VIS = "datos/satelite/visor"; os.makedirs(OUT, exist_ok=True); os.makedirs(VIS, exist_ok=True)
M = np.load("../datos/satelite/series/mascaras.npz")
un = lambda a: np.unpackbits(a)[:SH[0] * SH[1]].reshape(SH).astype(bool)
s2 = {pd.Timestamp(f): (un(v), un(g)) for f, v, g in zip(M["fechas"], M["val"], M["veg"])}
lat, lon = BARRERA
items = sorted(catalogo().search(collections=["sentinel-1-rtc"], intersects={"type": "Point", "coordinates": [lon, lat]},
               datetime="2019-01-01/2026-12-31").items(), key=lambda i: i.datetime)
print("escenas S1:", len(items), "máscaras S2:", len(s2), flush=True)
def leer(href):
    dst = np.full(SH, np.nan, "float32")
    with rasterio.open(href) as src:
        reproject(source=rasterio.band(src, 1), destination=dst, dst_transform=TR, dst_crs=CRS, resampling=Resampling.average, src_nodata=0, dst_nodata=np.nan)
    return dst
def feats(vh, vv):
    f = lambda a: ndimage.uniform_filter(np.nan_to_num(a, nan=-25), 3)
    m3 = f(vh); s3 = np.sqrt(np.clip(f(np.nan_to_num(vh, nan=-25) ** 2) - m3 ** 2, 0, None))
    return np.stack([vh, vv, vh - vv, m3, s3, f(vv)], -1)
esc = []; X = []; Y = []; GRP = []
for k, it in enumerate(items):
    try:
        it = firmar(it); vh = leer(it.assets["vh"].href); vv = leer(it.assets["vv"].href)
        vh = 10 * np.log10(np.where(vh > 0, vh, np.nan)); vv = 10 * np.log10(np.where(vv > 0, vv, np.nan))
        v = Z & np.isfinite(vh) & np.isfinite(vv)
        if v.sum() < 0.8 * Z.sum(): continue
        d = pd.Timestamp(it.datetime.strftime("%Y-%m-%d")); F = feats(vh, vv)
        esc.append(dict(fecha=d, F=F[v].astype("float32"), v=v, thr=(vh >= -14)[v]))
        near = [t for t in s2 if abs((t - d).days) <= 2]
        if near:
            t = min(near, key=lambda t: abs((t - d).days)); sv, sg = s2[t]; m = v & sv
            if m.sum() > 0.7 * Z.sum():
                X.append(F[m].astype("float32")); Y.append(sg[m]); GRP.append(np.full(m.sum(), d.year)); esc[-1]["par"] = t
        if d >= pd.Timestamp("2024-01-01"):
            img = (np.clip((np.nan_to_num(vh, nan=-25) + 25) / 20, 0, 1) * 255).astype("uint8")
            Image.fromarray(img).save(f"{VIS}/s1_{d.date()}.jpg", quality=70)
        if k % 25 == 0: print(k, d.date(), len(X), flush=True)
    except Exception as e:
        print("error", it.id, str(e)[:120], flush=True)
X = np.concatenate(X); Y = np.concatenate(Y); GRP = np.concatenate(GRP)
print("píxeles de entrenamiento", len(Y), "vegetación", round(float(Y.mean()), 3), "pares", sum(1 for e in esc if "par" in e), flush=True)
mk = lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)
# validación dejando un año fuera: área por escena (suma de probabilidades) frente a Sentinel-2
filas = []
for yr in sorted(set(GRP)):
    tr = GRP != yr
    if tr.sum() < 1000 or (~tr).sum() < 100: continue
    clf = mk().fit(X[tr][::3], Y[tr][::3])
    for e in esc:
        if "par" not in e or e["fecha"].year != yr: continue
        sv, sg = s2[e["par"]]; v = e["v"]; m = v & sv
        p = clf.predict_proba(e["F"])[:, 1]; P = np.zeros(SH); P[v] = p; T = np.zeros(SH, bool); T[v] = e["thr"]
        for lado, L in (("total", np.ones(SH, bool)), ("arriba", SUR), ("abajo", ~SUR)):
            zz = Z & L; mm = m & L
            filas.append(dict(fecha=e["fecha"], lado=lado, s2=sg[mm].sum() / max(1, mm.sum()) * zz.sum() / 100,
                              ml=P[mm].sum() / max(1, mm.sum()) * zz.sum() / 100, umbral=T[mm].sum() / max(1, mm.sum()) * zz.sum() / 100))
V = pd.DataFrame(filas); val = {}
for lado, g in V.groupby("lado"):
    val[lado] = dict(n=len(g), rho_ml=round(spearmanr(g.s2, g.ml).statistic, 3), mae_ml=round(float((g.ml - g.s2).abs().mean()), 2), sesgo_ml=round(float((g.ml - g.s2).mean()), 2),
                     rho_umbral=round(spearmanr(g.s2, g.umbral).statistic, 3), mae_umbral=round(float((g.umbral - g.s2).abs().mean()), 2))
print("validación:", val, flush=True)
json.dump(val, open(f"{OUT}/validacion_s1ml.json", "w"), indent=1)
clf = mk().fit(X[::2], Y[::2]); rows = []
for e in esc:
    p = clf.predict_proba(e["F"])[:, 1]; P = np.zeros(SH); P[e["v"]] = p; r = dict(fecha=e["fecha"].strftime("%Y-%m-%d"))
    for lado, L in (("t", np.ones(SH, bool)), ("a", SUR), ("b", ~SUR)):
        mm = e["v"] & L; r[lado] = round(float(P[mm].sum() / max(1, mm.sum()) * (Z & L).sum() / 100), 2)
    rows.append(r)
pd.DataFrame(rows).drop_duplicates("fecha", keep="last").to_csv(f"{OUT}/escenas_s1ml.csv", index=False); print("listo", len(rows), flush=True)
