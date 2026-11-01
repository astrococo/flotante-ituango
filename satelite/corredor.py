"""Corredor del río: 30 km aguas arriba (sur) y 15 km aguas abajo de la barrera, Sentinel-2 L2A a 20 m.
Mosaicos 18NTN, 18NUN y 18NVN. La zona de agua (MNDWI > 0 en ≥ 50 % de las escenas despejadas) se calcula una vez
y queda fija en zona.npz; cada corrida procesa solo las fechas que aún no están en escenas.csv (incremental).
Tramos por distancia norte-sur a la barrera (negativo = aguas arriba / sur). Salidas en datos/satelite/corredor/."""
import os, json, numpy as np, pandas as pd, collections, datetime as dt
from PIL import Image
from comun import catalogo, firmar, leer, BARRERA_LINEA
OUT = "datos/satelite/corredor"; os.makedirs(OUT, exist_ok=True)
PREV = "../datos/satelite/corredor"                       # resultados ya publicados en el repositorio
lat = (BARRERA_LINEA[0][0] + BARRERA_LINEA[1][0]) / 2; lon = (BARRERA_LINEA[0][1] + BARRERA_LINEA[1][1]) / 2
KMS, KMN, KMW, KME = 31.0, 15.5, 11.0, 4.5                 # extensión del recuadro (km)
c = 111.32 * np.cos(np.radians(lat))
bbox = (lon - KMW / c, lat - KMS / 111.32, lon + KME / c, lat + KMN / 111.32)
RES = 0.02; SH = (int((KMS + KMN) / RES), int((KMW + KME) / RES))
km = (KMN - (np.arange(SH[0]) + 0.5) * RES)[:, None].repeat(SH[1], 1)   # + norte, − sur
TRAMOS = [(-30, -22.5), (-22.5, -15), (-15, -7.5), (-7.5, -2.5), (-2.5, 0), (0, 2.5), (2.5, 7.5), (7.5, 15)]
PUERTO = (6.893912, -75.829260)                            # punto de extracción (margen derecha)
xkm = ((np.arange(SH[1]) + 0.5) * RES - KMW)[None, :].repeat(SH[0], 0)
py, px = (PUERTO[0] - lat) * 111.32, (PUERTO[1] - lon) * c
dpu = np.hypot(km - py, xkm - px)
TILES = ("18NTN", "18NUN", "18NVN")
items = [i for i in catalogo().search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"2019-01-01/{dt.date.today()}").items()
         if i.properties.get("s2:mgrs_tile") in TILES]
por_fecha = collections.defaultdict(list)
for it in items: por_fecha[it.datetime.strftime("%Y-%m-%d")].append(it)
print("fechas en catálogo:", len(por_fecha), flush=True)
def banda(it, b): return leer(it.assets[b].href, bbox, out_shape=SH)[0].astype("float32")
def mosaico(its, bandas):
    val = np.zeros(SH, bool); out = {b: np.full(SH, np.nan, "float32") for b in bandas}
    for it in sorted(its, key=lambda i: i.properties.get("eo:cloud_cover", 100)):
        it = firmar(it); scl = leer(it.assets["SCL"].href, bbox, out_shape=SH)[0]
        ok = np.isin(scl, [4, 5, 6, 7]) & ~val
        if ok.mean() < 0.01: continue
        off = -1000.0 if float(it.properties.get("s2:processing_baseline", "0")) >= 4 else 0.0
        for b in bandas: x = (banda(it, b) + off) / 1e4; out[b][ok] = x[ok]
        val |= ok
    return val, out
# 1) zona de agua fija
zp = f"{PREV}/zona.npz"
if os.path.exists(zp) and tuple(np.load(zp)["shape"]) == SH:
    Z = np.load(zp)["Z"]; print("zona existente", int(Z.sum()), flush=True)
else:
    claras = sorted(por_fecha, key=lambda d: np.mean([i.properties.get("eo:cloud_cover", 100) for i in por_fecha[d]]))[:90]
    nv = np.zeros(SH, "int16"); nw = np.zeros(SH, "int16")
    for k, d in enumerate(claras):
        try:
            v, B = mosaico(por_fecha[d], ("B03", "B11")); m = (B["B03"] - B["B11"]) / (B["B03"] + B["B11"] + 1e-6)
            nv += v; nw += v & (m > 0)
            if k % 15 == 0: print("zona", k, d, flush=True)
        except Exception as e: print("error zona", d, str(e)[:120], flush=True)
    Z = (nv >= 8) & (nw >= 0.5 * nv)
    np.savez_compressed(f"{OUT}/zona.npz", Z=Z, shape=np.array(SH), bbox=np.array(bbox))
    img = np.zeros(SH + (3,), "uint8"); img[Z] = (40, 90, 160); img[np.abs(km) < 0.05] = (255, 0, 0)
    Image.fromarray(img).save(f"{OUT}/zona.png")
    print("zona nueva", int(Z.sum()), flush=True)
# 2) escenas nuevas
ep = f"{PREV}/escenas.csv"
prev = pd.read_csv(ep) if os.path.exists(ep) and os.path.exists(zp) and tuple(np.load(zp)["shape"]) == SH else pd.DataFrame(columns=["fecha"])
hechas = set(prev.fecha.astype(str)) if "p500_area_px" in prev.columns else set(); nuevas = sorted(d for d in por_fecha if d not in hechas)
print("fechas nuevas:", len(nuevas), flush=True)
rows = []
for k, d in enumerate(nuevas):
    try:
        v, B = mosaico(por_fecha[d], ("B04", "B08")); nd = (B["B08"] - B["B04"]) / (B["B08"] + B["B04"] + 1e-6)
        row = dict(fecha=d)
        for n_, m in (("p500", Z & (dpu <= 0.5)), ("bp", Z & (km < 0) & (km > py - 0.02))):
            row[f"{n_}_area_px"] = int(m.sum()); row[f"{n_}_valid_px"] = int((m & v).sum()); row[f"{n_}_veg_px"] = int((m & v & (nd >= 0.30)).sum())
        for a, b in TRAMOS:
            m = Z & (km >= a) & (km < b); row[f"t{a}_{b}_area_px"] = int(m.sum()); row[f"t{a}_{b}_valid_px"] = int((m & v).sum()); row[f"t{a}_{b}_veg_px"] = int((m & v & (nd >= 0.30)).sum())
        rows.append(row)
        if k % 20 == 0: print(k, d, flush=True)
    except Exception as e: print("error", d, str(e)[:120], flush=True)
E = pd.concat([prev, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("fecha", keep="last").sort_values("fecha")
E.to_csv(f"{OUT}/escenas.csv", index=False)
# 3) serie para la app: hectáreas por tramo cuando el tramo está ≥ 60 % despejado
ser = []
for r in E.to_dict("records"):
    o = dict(f=str(r["fecha"]))
    for a, b in TRAMOS:
        k = f"t{a}_{b}".replace("-", "_").replace(".", "p")
        ar, vl, vg = r.get(f"t{a}_{b}_area_px"), r.get(f"t{a}_{b}_valid_px"), r.get(f"t{a}_{b}_veg_px")
        if ar and vl == vl and vl >= 0.6 * ar: o[f"{a}..{b}"] = round(vg / vl * ar * RES * RES * 100, 1)
    for n_ in ("p500", "bp"):
        ar, vl, vg = r.get(f"{n_}_area_px"), r.get(f"{n_}_valid_px"), r.get(f"{n_}_veg_px")
        if ar and vl == vl and vl >= 0.6 * ar: o[n_] = round(vg / vl * ar * RES * RES * 100, 2)
    if len(o) > 1: ser.append(o)
json.dump(dict(generado=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), tramos=[f"{a}..{b}" for a, b in TRAMOS],
               agua_ha={f"{a}..{b}": round(float((Z & (km >= a) & (km < b)).sum()) * RES * RES * 100, 1) for a, b in TRAMOS},
               serie=ser, nuevas=len(rows), puerto=list(PUERTO), zonas_extra={"p500": "agua a ≤ 500 m del punto de extracción", "bp": "agua entre el puerto y la barrera"}), open(f"{OUT}/serie.json", "w"), separators=(",", ":"))
print("listo: nuevas", len(rows), "total", len(E), flush=True)
