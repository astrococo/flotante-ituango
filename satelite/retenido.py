"""Mancha retenida en la barrera y corredor del río ±30 km (aguas arriba y aguas abajo), con dos sensores:
  - Sentinel-2 L2A (óptico, 20 m): vegetación flotante NDVI ≥ 0,30 dentro de la zona de agua, solo partes despejadas.
  - Sentinel-1 RTC (radar, ve a través de nubes y en crecientes): VH ≥ −14 dB dentro de la zona de agua erosionada.
Zona de agua: MNDWI > 0 en ≥ 50 % de 90 fechas despejadas (fija, zona.npz). Para no contar orillas se usa la zona
erosionada 1 píxel (20 m). Distancias norte-sur a la línea de la barrera: negativo = aguas arriba (sur).
Métricas por fecha y sensor:
  retenida_ha    vegetación en el agua 0–2,5 km aguas arriba de la barrera (lo que la barrera retiene)
  barrera_pct    % de la franja de 0–100 m aguas arriba de la línea de la barrera cubierta (ocupación de la barrera)
  t<a>_<b>       hectáreas por tramo (km): −30…−22,5, …, 0…2,5, …, 22,5…30
Uso: python retenido.py s2 | s1 | serie        (incremental: solo fechas nuevas). Salidas en datos/satelite/retenido/."""
import os, sys, json, numpy as np, pandas as pd, collections, datetime as dt
from comun import catalogo, firmar, leer, BARRERA_LINEA
OUT = "datos/satelite/retenido"; os.makedirs(OUT, exist_ok=True)
PREV = "../datos/satelite/retenido"
lat = (BARRERA_LINEA[0][0] + BARRERA_LINEA[1][0]) / 2; lon = (BARRERA_LINEA[0][1] + BARRERA_LINEA[1][1]) / 2
KMS, KMN, KMW, KME = 31.0, 31.0, 12.0, 14.0               # km al sur, norte, oeste y este de la barrera
c = 111.32 * np.cos(np.radians(lat))
bbox = (lon - KMW / c, lat - KMS / 111.32, lon + KME / c, lat + KMN / 111.32)
RES = 0.02; SH = (int((KMS + KMN) / RES), int((KMW + KME) / RES)); HA = RES * RES * 100
km = (KMN - (np.arange(SH[0]) + 0.5) * RES)[:, None].repeat(SH[1], 1)
xkm = ((np.arange(SH[1]) + 0.5) * RES - KMW)[None, :].repeat(SH[0], 0)
# línea de la barrera en km relativos
(la1, lo1), (la2, lo2) = BARRERA_LINEA
y1, x1 = (la1 - lat) * 111.32, (lo1 - lon) * c; y2, x2 = (la2 - lat) * 111.32, (lo2 - lon) * c
yl = y1 + (xkm - x1) * (y2 - y1) / (x2 - x1)               # km de la línea a la misma x
dl = km - yl                                               # distancia norte-sur a la línea (− = aguas arriba)
FRANJA = (dl <= 0) & (dl > -0.10) & (xkm >= min(x1, x2) - 0.02) & (xkm <= max(x1, x2) + 0.02)
TRAMOS = [(-30, -22.5), (-22.5, -15), (-15, -7.5), (-7.5, -2.5), (-2.5, 0), (0, 2.5), (2.5, 7.5), (7.5, 15), (15, 22.5), (22.5, 30)]
def erosion(Z):
    E = Z.copy(); E[1:] &= Z[:-1]; E[:-1] &= Z[1:]; E[:, 1:] &= Z[:, :-1]; E[:, :-1] &= Z[:, 1:]; return E

def items_s2():
    its = list(catalogo().search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"2019-01-01/{dt.date.today()}").items())
    g = collections.defaultdict(list)
    for it in its: g[it.datetime.strftime("%Y-%m-%d")].append(it)
    return g
def banda(it, b): return leer(it.assets[b].href, bbox, out_shape=SH)[0].astype("float32")
GCRS = {"crs": None}
def mosaico(its, bandas):
    val = np.zeros(SH, bool); out = {b: np.full(SH, np.nan, "float32") for b in bandas}
    for it in sorted(its, key=lambda i: i.properties.get("eo:cloud_cover", 100)):
        it = firmar(it); scl, _, crs = leer(it.assets["SCL"].href, bbox, out_shape=SH)
        if GCRS["crs"] is None: GCRS["crs"] = str(crs)
        if str(crs) != GCRS["crs"]: continue            # mosaicos de otra zona UTM: se omiten para no mezclar geometrías
        ok = np.isin(scl, [4, 5, 6, 7]) & ~val
        if ok.mean() < 0.005: continue
        off = -1000.0 if float(it.properties.get("s2:processing_baseline", "0")) >= 4 else 0.0
        for b in bandas: x = (banda(it, b) + off) / 1e4; out[b][ok] = x[ok]
        val |= ok
    return val, out

def zona(g):
    zp = f"{PREV}/zona.npz"
    if os.path.exists(zp) and tuple(np.load(zp)["shape"]) == SH:
        z = np.load(zp); Z = z["Z"]; GCRS["crs"] = str(z["crs"]) if "crs" in z else None
        np.savez_compressed(f"{OUT}/zona.npz", Z=Z, shape=np.array(SH), bbox=np.array(bbox), crs=np.array(GCRS["crs"] or "")); return Z
    claras = sorted(g, key=lambda d: np.mean([i.properties.get("eo:cloud_cover", 100) for i in g[d]]))[:90]
    nv = np.zeros(SH, "int16"); nw = np.zeros(SH, "int16")
    for k, d in enumerate(claras):
        try:
            v, B = mosaico(g[d], ("B03", "B11")); m = (B["B03"] - B["B11"]) / (B["B03"] + B["B11"] + 1e-6)
            nv += v; nw += v & (m > 0)
            if k % 15 == 0: print("zona", k, d, flush=True)
        except Exception as e: print("error zona", d, str(e)[:120], flush=True)
    Z = (nv >= 8) & (nw >= 0.5 * nv)
    np.savez_compressed(f"{OUT}/zona.npz", Z=Z, shape=np.array(SH), bbox=np.array(bbox), crs=np.array(GCRS["crs"] or "")); print("zona nueva", int(Z.sum()), GCRS["crs"], flush=True)
    from PIL import Image
    img = np.zeros(SH + (3,), "uint8"); img[Z] = (40, 90, 160); img[FRANJA] = (255, 0, 0); img[np.abs(dl) < 0.03] = (255, 0, 0)
    Image.fromarray(img).save(f"{OUT}/zona.png")
    return Z

def metricas(veg, v, Ze, row):
    m = Ze & (dl > -2.5) & (dl <= 0); row["ret_area_px"] = int(m.sum()); row["ret_valid_px"] = int((m & v).sum()); row["ret_veg_px"] = int((m & v & veg).sum())
    f = FRANJA & Ze; row["bar_area_px"] = int(f.sum()); row["bar_valid_px"] = int((f & v).sum()); row["bar_veg_px"] = int((f & v & veg).sum())
    for a, b in TRAMOS:
        m = Ze & (dl >= a) & (dl < b); row[f"t{a}_{b}_area_px"] = int(m.sum()); row[f"t{a}_{b}_valid_px"] = int((m & v).sum()); row[f"t{a}_{b}_veg_px"] = int((m & v & veg).sum())
    return row

def previo(nombre):
    p = f"{PREV}/{nombre}"
    if os.path.exists(p) and os.path.exists(f"{PREV}/zona.npz") and tuple(np.load(f"{PREV}/zona.npz")["shape"]) == SH: return pd.read_csv(p)
    return pd.DataFrame(columns=["fecha"])

def corre_s2():
    g = items_s2(); print("fechas S2:", len(g), flush=True)
    Ze = erosion(zona(g)); prev = previo("escenas_s2.csv"); hechas = set(prev.fecha.astype(str))
    rows = []
    for k, d in enumerate(sorted(x for x in g if x not in hechas)):
        try:
            v, B = mosaico(g[d], ("B04", "B08")); nd = (B["B08"] - B["B04"]) / (B["B08"] + B["B04"] + 1e-6)
            rows.append(metricas(nd >= 0.30, v, Ze, dict(fecha=d)))
            if k % 25 == 0:
                print("s2", k, d, flush=True)
                pd.concat([prev, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("fecha", keep="last").sort_values("fecha").to_csv(f"{OUT}/escenas_s2.csv", index=False)
        except Exception as e: print("error s2", d, str(e)[:120], flush=True)
    E = pd.concat([prev, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("fecha", keep="last").sort_values("fecha")
    E.to_csv(f"{OUT}/escenas_s2.csv", index=False); print("S2 listo: nuevas", len(rows), "total", len(E), flush=True)

def corre_s1():
    from rasterio.enums import Resampling
    zp = f"{OUT}/zona.npz" if os.path.exists(f"{OUT}/zona.npz") else f"{PREV}/zona.npz"
    Ze = erosion(np.load(zp)["Z"]); CRS2 = str(np.load(zp)["crs"]) if "crs" in np.load(zp) else "EPSG:32618"
    its = list(catalogo().search(collections=["sentinel-1-rtc"], bbox=bbox, datetime=f"2019-01-01/{dt.date.today()}").items())
    g = collections.defaultdict(list)
    for it in its: g[it.datetime.strftime("%Y-%m-%d")].append(it)
    print("fechas S1:", len(g), flush=True)
    prev = previo("escenas_s1.csv"); hechas = set(prev.fecha.astype(str)); rows = []
    for k, d in enumerate(sorted(x for x in g if x not in hechas)):
        try:
            acc = np.full(SH, np.nan, "float32")
            for it in g[d]:
                it = firmar(it)
                arr, _, crs = leer(it.assets["vh"].href, bbox, out_shape=SH, resampling=Resampling.average)
                if str(crs) != CRS2: print("otro CRS", d, crs, flush=True); continue
                arr = arr.astype("float32"); arr[arr <= 0] = np.nan
                acc = np.where(np.isnan(acc), arr, acc)
            vh = 10 * np.log10(np.where(acc > 0, acc, np.nan)); v = np.isfinite(vh)
            row = dict(fecha=d, plat=g[d][0].properties.get("platform"), orbita=g[d][0].properties.get("sat:orbit_state"))
            row["vh_agua_mediana"] = round(float(np.nanmedian(vh[Ze & v])), 2) if (Ze & v).any() else None
            for t in (-16, -15, -14, -13, -12):
                r = metricas(vh >= t, v, Ze, {}); row.update({f"{kk}_vh{abs(t)}" if kk.endswith("veg_px") else kk: vv for kk, vv in r.items()})
            rows.append(row)
            if k % 25 == 0:
                print("s1", k, d, row["vh_agua_mediana"], flush=True)
                pd.concat([prev, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("fecha", keep="last").sort_values("fecha").to_csv(f"{OUT}/escenas_s1.csv", index=False)
        except Exception as e: print("error s1", d, str(e)[:120], flush=True)
    E = pd.concat([prev, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("fecha", keep="last").sort_values("fecha")
    E.to_csv(f"{OUT}/escenas_s1.csv", index=False); print("S1 listo: nuevas", len(rows), "total", len(E), flush=True)

def serie():
    """Une ambos sensores. Óptico: zona ≥ 60 % despejada. Radar: umbral VH elegido por concordancia con el óptico (±3 días)."""
    s2 = pd.read_csv(f"{OUT}/escenas_s2.csv") if os.path.exists(f"{OUT}/escenas_s2.csv") else pd.DataFrame()
    s1 = pd.read_csv(f"{OUT}/escenas_s1.csv") if os.path.exists(f"{OUT}/escenas_s1.csv") else pd.DataFrame()
    keys = ["ret", "bar"] + [f"t{a}_{b}" for a, b in TRAMOS]
    def val(r, k, suf=""):
        ar, vl, vg = r.get(f"{k}_area_px"), r.get(f"{k}_valid_px"), r.get(f"{k}_veg_px{suf}")
        if not ar or vl != vl or vg != vg or vl < 0.6 * ar: return None
        return vg / vl * (100.0 if k == "bar" else ar * HA)
    O = {}
    for r in s2.to_dict("records"):
        o = {k: val(r, k) for k in keys}; o = {k: round(v, 2) for k, v in o.items() if v is not None}
        if o: O[str(r["fecha"])] = o
    # calibración del radar contra el óptico en la zona retenida y por tramo (fechas a ≤ 3 días)
    cal = {}
    if len(s1) and len(O):
        f2 = pd.to_datetime(pd.Series(list(O.keys()))); best = None
        for t in (16, 15, 14, 13, 12):
            pares = []
            for r in s1.to_dict("records"):
                f = pd.Timestamp(r["fecha"]); j = (f2 - f).abs(); i = int(j.values.argmin())
                if j.iloc[i] > pd.Timedelta(days=3): continue
                a = O[f2.iloc[i].strftime("%Y-%m-%d")].get("ret"); b = val(r, "ret", f"_vh{t}")
                if a is not None and b is not None: pares.append((a, b))
            if len(pares) >= 15:
                P = np.array(pares); rho = pd.Series(P[:, 0]).corr(pd.Series(P[:, 1]), method="spearman")
                sesgo = float(np.median(P[:, 1] - P[:, 0])); mae = float(np.mean(np.abs(P[:, 1] - P[:, 0])))
                cal[f"vh{t}"] = dict(n=len(pares), rho=round(float(rho), 3), sesgo_ha=round(sesgo, 2), mae_ha=round(mae, 2))
                if best is None or rho > cal[best]["rho"]: best = f"vh{t}"
        cal["elegido"] = best
    R = {}
    if cal.get("elegido"):
        suf = "_" + cal["elegido"]
        for r in s1.to_dict("records"):
            o = {k: val(r, k, suf) for k in keys}; o = {k: round(v, 2) for k, v in o.items() if v is not None}
            if o: R[str(r["fecha"])] = o
    agua = {k: round(float(((erosion(np.load(f'{OUT}/zona.npz')['Z'])) & (dl >= a) & (dl < b)).sum()) * HA, 1) for k, (a, b) in zip(keys[2:], TRAMOS)} if os.path.exists(f"{OUT}/zona.npz") else {}
    json.dump(dict(generado=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), tramos=[f"{a}..{b}" for a, b in TRAMOS], claves=keys, agua_ha=agua,
                   franja_barrera="0–100 m aguas arriba de la línea de la barrera", retenida="0–2,5 km aguas arriba de la barrera",
                   optico=O, radar=R, calibracion_radar=cal), open(f"{OUT}/serie.json", "w"), separators=(",", ":"))
    print("serie: ópticas", len(O), "radar", len(R), "calibración", cal, flush=True)

if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if modo in ("s2", "todo"): corre_s2()
    if modo in ("s1", "todo"): corre_s1()
    if modo in ("serie", "todo", "s1", "s2"): serie()
