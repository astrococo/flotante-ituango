"""Vegetación flotante dentro del contorno de análisis (contorno_analisis.kml, entregado por el usuario el 2-nov-2026),
con distancia medida A LO LARGO DEL RÍO desde la línea de la barrera (no en línea recta) y grilla UTM 18N de 10 m.

Sensores (Microsoft Planetary Computer, acceso público):
  s2  Sentinel-2 L2A, 10 m: NDVI (B04, B08) con umbrales 0,20 / 0,30 / 0,40, índice de algas flotantes FAI (B04, B08, B11)
      y NDVI 0,30 agregado a 20 m (para medir el efecto del tamaño del píxel). Nubes: SCL 4–7.
  s1  Sentinel-1 RTC (radar, ve a través de nubes), 10 m: VH ≥ −16 … −12 dB.
  ls  Landsat 8/9 Colección 2 L2, 30 m: NDVI 0,30 / 0,40. Nubes: QA_PIXEL bits 1–4.
Zona de agua: MNDWI (B03, B11) > 0 en ≥ 50 % (núcleo, z50) o ≥ 25 % (ampliada, z25) de 60 fechas despejadas, dentro del
contorno, erosionada 10 m. Distancia: camino más corto por la zona de agua desde la línea de la barrera; − = aguas arriba.
Tramos de 2,5 km; «ret» = 0–2,5 km aguas arriba; «bar» = 0–100 m aguas arriba de la barrera.
Uso: python contorno.py explorar | zona | s2 | s1 | ls | serie        Salidas en datos/satelite/contorno/."""
import os, sys, re, json, collections, datetime as dt, numpy as np, pandas as pd, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from pyproj import Transformer
from comun import catalogo, firmar, BARRERA_LINEA

OUT = "datos/satelite/contorno"; os.makedirs(OUT, exist_ok=True)
PREV = "../datos/satelite/contorno"
CRS = "EPSG:32618"; RES = 10.0; HA = RES * RES / 1e4
KML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contorno_analisis.kml")
_txt = open(KML, encoding="utf-8").read()
POLY = [tuple(map(float, t.split(",")[:2])) for t in re.search(r"<coordinates>(.*?)</coordinates>", _txt, re.S).group(1).split()]
T = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
px, py = T.transform([p[0] for p in POLY], [p[1] for p in POLY])
B = 300.0
x0 = np.floor((min(px) - B) / 20) * 20; x1 = np.ceil((max(px) + B) / 20) * 20
y0 = np.floor((min(py) - B) / 20) * 20; y1 = np.ceil((max(py) + B) / 20) * 20
SH = (int((y1 - y0) / RES), int((x1 - x0) / RES)); TR = from_origin(x0, y1, RES, RES)
lon_min, lon_max = min(p[0] for p in POLY) - 0.004, max(p[0] for p in POLY) + 0.004
lat_min, lat_max = min(p[1] for p in POLY) - 0.004, max(p[1] for p in POLY) + 0.004
BBOX = (lon_min, lat_min, lon_max, lat_max)
DENTRO = rasterize([({"type": "Polygon", "coordinates": [list(zip(px, py))]}, 1)], out_shape=SH, transform=TR, fill=0).astype(bool)
# línea de la barrera en la grilla
(la1, lo1), (la2, lo2) = BARRERA_LINEA
bx, by = T.transform([lo1, lo2], [la1, la2])
XX = x0 + (np.arange(SH[1]) + 0.5) * RES; YY = y1 - (np.arange(SH[0]) + 0.5) * RES
GX, GY = np.meshgrid(XX, YY)
dxl, dyl = bx[1] - bx[0], by[1] - by[0]; L = np.hypot(dxl, dyl)
lado = (dxl * (GY - by[0]) - dyl * (GX - bx[0])) / L            # > 0 al norte de la línea (aguas abajo)
tt = ((GX - bx[0]) * dxl + (GY - by[0]) * dyl) / L**2
LINEA = (np.abs(lado) <= RES * 0.75) & (tt >= -0.05) & (tt <= 1.05)

def erosion(Z):
    E = Z.copy(); E[1:] &= Z[:-1]; E[:-1] &= Z[1:]; E[:, 1:] &= Z[:, :-1]; E[:, :-1] &= Z[:, 1:]; return E
def dilata(Z, n=1):
    E = Z.copy()
    for _ in range(n):
        F = E.copy(); F[1:] |= E[:-1]; F[:-1] |= E[1:]; F[:, 1:] |= E[:, :-1]; F[:, :-1] |= E[:, 1:]; E = F
    return E

def a_grilla(href, res=Resampling.bilinear, dtype="float32", nod=0, dst_nod=0):
    dst = np.full(SH, dst_nod, dtype)
    with rasterio.open(href) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=TR, dst_crs=CRS, resampling=res, src_nodata=nod, dst_nodata=dst_nod)
    return dst

def por_fecha(coll, extra=None):
    q = dict(collections=[coll], bbox=BBOX, datetime=f"2019-01-01/{dt.date.today()}")
    if extra: q.update(extra)
    g = collections.defaultdict(list)
    for it in catalogo().search(**q).items(): g[it.datetime.strftime("%Y-%m-%d")].append(it)
    return g

def s2_mosaico(its, bandas):
    """Reflectancias en la grilla, solo píxeles SCL 4–7 (vegetación, suelo, agua, sin clasificar)."""
    val = np.zeros(SH, bool); out = {b: np.full(SH, np.nan, "float32") for b in bandas}
    for it in sorted(its, key=lambda i: i.properties.get("eo:cloud_cover", 100)):
        it = firmar(it)
        scl = a_grilla(it.assets["SCL"].href, Resampling.nearest, "uint8")
        ok = np.isin(scl, [4, 5, 6, 7]) & ~val
        if (ok & DENTRO).sum() < 0.005 * DENTRO.sum(): continue
        off = -1000.0 if float(it.properties.get("s2:processing_baseline", "0")) >= 4 else 0.0
        for b in bandas:
            raw = a_grilla(it.assets[b].href, Resampling.bilinear)
            x = (raw + off) / 1e4; x[raw == 0] = np.nan; out[b][ok] = x[ok]
        val |= ok
    return val, out

# ---------------- zona de agua y distancia por el río ----------------
def distancia(Zc):
    """Camino más corto (8 vecinos) por la zona de agua desde la línea de la barrera, por separado a cada lado."""
    from skimage.graph import MCP_Geometric
    D = np.full(SH, np.nan, "float32")
    for s in (-1, 1):
        lad = (lado * s >= -RES)                       # el propio lado (con la línea)
        M = Zc & lad
        cost = np.where(M, 1.0, np.inf)
        seeds = np.argwhere(M & LINEA)
        if not len(seeds): continue
        mcp = MCP_Geometric(cost, fully_connected=True)
        c, _ = mcp.find_costs([tuple(p) for p in seeds])
        c = c * RES / 1000.0
        sel = M & np.isfinite(c) & (lado * s >= 0)
        D[sel] = s * c[sel]
    return D

def zona(force=False):
    zp = f"{OUT}/zona.npz"
    for p in (zp, f"{PREV}/zona.npz"):
        if not force and os.path.exists(p):
            z = np.load(p)
            if tuple(z["shape"]) == SH:
                if p != zp: np.savez_compressed(zp, **{k: z[k] for k in z.files})
                return z["Z50"], z["Z25"], z["D"]
    g = por_fecha("sentinel-2-l2a")
    claras = sorted(g, key=lambda d: np.mean([i.properties.get("eo:cloud_cover", 100) for i in g[d]]))[:60]
    nv = np.zeros(SH, "int16"); nw = np.zeros(SH, "int16")
    for k, d in enumerate(claras):
        try:
            v, Bd = s2_mosaico(g[d], ("B03", "B11")); m = (Bd["B03"] - Bd["B11"]) / (Bd["B03"] + Bd["B11"] + 1e-6)
            ok = v & np.isfinite(m); nv += ok; nw += ok & (m > 0)
            if k % 10 == 0: print("zona", k, d, flush=True)
        except Exception as e: print("error zona", d, str(e)[:150], flush=True)
    base = DENTRO & (nv >= 8)
    Z50 = base & (nw >= 0.5 * nv); Z25 = base & (nw >= 0.25 * nv)
    Dz = distancia(dilata(Z25, 1) & DENTRO)            # la conectividad usa la zona ampliada (puentes de 1 píxel)
    np.savez_compressed(zp, Z50=Z50, Z25=Z25, D=Dz, nv=nv, nw=nw, shape=np.array(SH), tr=np.array(TR)[:6], crs=np.array(CRS))
    print("zona nueva: z50", int(Z50.sum()), "z25", int(Z25.sum()), "km aguas arriba", float(np.nanmin(Dz)), "aguas abajo", float(np.nanmax(Dz)), flush=True)
    imagen(Z50, Z25, Dz)
    return Z50, Z25, Dz

def imagen(Z50, Z25, D):
    from PIL import Image
    img = np.zeros(SH + (3,), "uint8"); img[DENTRO] = (30, 30, 30)
    img[Z25] = (80, 120, 170); img[Z50] = (40, 90, 160)
    for k in range(-40, 41):                            # marcas cada 2,5 km
        if k == 0: continue
        m = np.isfinite(D) & (np.abs(D - k * 2.5) < 0.03); img[m] = (255, 210, 0)
    img[LINEA] = (255, 0, 0)
    Image.fromarray(img).save(f"{OUT}/zona.png")

def tramos(D):
    up = np.nanmin(D); dn = np.nanmax(D)
    T_ = [(-a - 2.5, -a) for a in np.arange(0, -up, 2.5)][::-1] + [(a, a + 2.5) for a in np.arange(0, dn, 2.5)]
    return [(float(round(a, 1)) + 0.0, float(round(b, 1)) + 0.0) for a, b in T_]

def mascaras(Z50, Z25, D):
    Ze, Ze25 = erosion(Z50), erosion(Z25); fin = np.isfinite(D)
    M = {"ret": Ze & fin & (D > -2.5) & (D <= 0), "bar": Ze & fin & (D > -0.1) & (D <= 0)}
    for a, b in tramos(D): M[f"t{a}_{b}"] = Ze & fin & (D >= a) & (D < b)
    M["arriba"] = Ze & fin & (D <= 0); M["arriba25"] = Ze25 & fin & (D <= 0); M["ret25"] = Ze25 & fin & (D > -2.5) & (D <= 0)
    ter = terreno_cargar()
    if ter is not None:                                 # agua lejos de laderas empinadas (menos sombra y rebote de radar)
        L_ = ter["ladera"]; M["arriba_ll"] = M["arriba"] & ~L_; M["ret_ll"] = M["ret"] & ~L_
    return M

def terreno_cargar():
    for p in (f"{OUT}/terreno.npz", f"{PREV}/terreno.npz"):
        if os.path.exists(p):
            t = np.load(p)
            if tuple(t["dem"].shape) == SH: return t
    return None

def terreno():
    """Copernicus DEM GLO-30 (elevación y pendiente), JRC Global Surface Water (frecuencia de agua 1984–2021) y ESA WorldCover 2021,
    todos remuestreados a la grilla de 10 m. El DEM es anterior al llenado del embalse (2011–2015): muestra el cañón original."""
    z = np.load(f"{OUT}/zona.npz") if os.path.exists(f"{OUT}/zona.npz") else np.load(f"{PREV}/zona.npz")
    Z25, D = z["Z25"], z["D"]
    it = firmar(next(iter(catalogo().search(collections=["cop-dem-glo-30"], bbox=BBOX).items())))
    dem = a_grilla(it.assets["data"].href, Resampling.bilinear, "float32", -32767, np.nan)
    gy, gx = np.gradient(dem, RES); pend = np.degrees(np.arctan(np.hypot(gx, gy))).astype("float32")
    gsw = np.full(SH, 255, "uint8"); wc = np.zeros(SH, "uint8")
    try:
        for it in catalogo().search(collections=["jrc-gsw"], bbox=BBOX).items():
            it = firmar(it); x = a_grilla(it.assets["occurrence"].href, Resampling.nearest, "uint8", 255, 255); gsw = np.where(gsw == 255, x, gsw)
    except Exception as e: print("error gsw", str(e)[:120], flush=True)
    try:
        for it in catalogo().search(collections=["esa-worldcover"], bbox=BBOX).items():
            it = firmar(it); x = a_grilla(it.assets["map"].href, Resampling.nearest, "uint8", 0, 0); wc = np.where(wc == 0, x, wc)
    except Exception as e: print("error worldcover", str(e)[:120], flush=True)
    ladera = dilata((pend >= 35) & ~Z25 & DENTRO, 3) & Z25    # agua a ≤ 30 m de una ladera de 35° o más
    np.savez_compressed(f"{OUT}/terreno.npz", dem=dem, pend=pend, gsw=gsw, wc=wc, ladera=ladera)
    # perfil del cauce original (mínimo del DEM por cada 250 m de río) y pendiente de las laderas junto al agua
    perfil = []
    for a in np.arange(np.floor(np.nanmin(D) * 4) / 4, np.nanmax(D), 0.25):
        m = np.isfinite(D) & (D >= a) & (D < a + 0.25) & np.isfinite(dem)
        if m.sum() < 20: continue
        perfil.append(dict(km=round(float(a + 0.125), 3), lecho_m=round(float(np.nanpercentile(dem[m], 2)), 1), agua_ha=round(float(m.sum()) * HA, 2)))
    print("terreno: elevación del agua (mediana)", round(float(np.nanmedian(dem[Z25])), 1), "m · laderas ≥35° junto al agua", int(ladera.sum()), "px de", int(Z25.sum()),
          "· GSW>50 % en zona", round(float(((gsw > 50) & (gsw <= 100) & Z25).sum() / max(1, Z25.sum())), 3), flush=True)
    json.dump(dict(perfil=perfil, ladera_px=int(ladera.sum()), zona25_px=int(Z25.sum()),
                   gsw_zona=dict(mayor50=round(float(((gsw > 50) & (gsw <= 100) & Z25).sum() / max(1, Z25.sum())), 3), nunca=round(float(((gsw == 0) & Z25).sum() / max(1, Z25.sum())), 3)),
                   worldcover_zona={int(k): int(((wc == k) & Z25).sum()) for k in np.unique(wc[Z25])}),
              open(f"{OUT}/terreno.json", "w"), indent=1)

def cuenta(row, M, v, inds):
    for k, m in M.items():
        mv = m & v; row[f"{k}_area_px"] = int(m.sum()); row[f"{k}_valid_px"] = int(mv.sum())
        for n, ind in inds.items(): row[f"{k}_{n}"] = int((mv & ind).sum())
    return row

def previo(nombre):
    for p in (f"{OUT}/{nombre}", f"{PREV}/{nombre}"):
        if os.path.exists(p):
            try: return pd.read_csv(p)
            except Exception: pass
    return pd.DataFrame(columns=["fecha"])

def guardar(prev, rows, nombre):
    E = pd.concat([prev, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("fecha", keep="last").sort_values("fecha")
    E.to_csv(f"{OUT}/{nombre}", index=False); return E

# ---------------- sensores ----------------
def corre_s2():
    Z50, Z25, D = zona(); M = mascaras(Z50, Z25, D)
    g = por_fecha("sentinel-2-l2a"); print("fechas S2:", len(g), flush=True)
    prev = previo("escenas_s2.csv"); hechas = set(prev.fecha.astype(str)); rows = []
    for k, d in enumerate(sorted(x for x in g if x not in hechas)):
        try:
            v, Bd = s2_mosaico(g[d], ("B04", "B08", "B11"))
            r, n, s = Bd["B04"], Bd["B08"], Bd["B11"]
            nd = (n - r) / (n + r + 1e-6)
            fai = n - (r + (s - r) * (842 - 665) / (1610 - 665))
            v = v & np.isfinite(nd) & np.isfinite(fai)
            v20 = v.copy(); veg20 = np.zeros(SH, bool)
            h, w = SH[0] // 2 * 2, SH[1] // 2 * 2       # NDVI ≥ 0,30 en píxeles de 20 m (promedio de 2×2)
            blk = lambda a: a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
            nd20 = blk(np.where(v, nd, np.nan)); veg20[:h, :w] = np.repeat(np.repeat(nd20 >= 0.30, 2, 0), 2, 1)
            inds = {"ndvi20": nd >= 0.20, "ndvi30": nd >= 0.30, "ndvi40": nd >= 0.40, "fai02": fai >= 0.02, "fai05": fai >= 0.05, "ndvi30_20m": veg20}
            rows.append(cuenta(dict(fecha=d), M, v, inds))
            if k % 25 == 0: print("s2", k, d, flush=True); guardar(prev, rows, "escenas_s2.csv")
        except Exception as e: print("error s2", d, str(e)[:150], flush=True)
    E = guardar(prev, rows, "escenas_s2.csv"); print("S2 listo: nuevas", len(rows), "total", len(E), flush=True)

def corre_s1():
    Z50, Z25, D = zona(); M = {k: v for k, v in mascaras(Z50, Z25, D).items() if not k.endswith("25")}
    g = por_fecha("sentinel-1-rtc"); print("fechas S1:", len(g), flush=True)
    prev = previo("escenas_s1.csv"); hechas = set(prev.fecha.astype(str)); rows = []
    for k, d in enumerate(sorted(x for x in g if x not in hechas)):
        try:
            acc = np.full(SH, np.nan, "float32")
            for it in g[d]:
                it = firmar(it); arr = a_grilla(it.assets["vh"].href, Resampling.average, "float32", 0, np.nan)
                arr[arr <= 0] = np.nan; acc = np.where(np.isnan(acc), arr, acc)
            vh = 10 * np.log10(acc); v = np.isfinite(vh)
            row = dict(fecha=d, plat=g[d][0].properties.get("platform"), orbita=g[d][0].properties.get("sat:orbit_state"))
            row["vh_agua_mediana"] = round(float(np.nanmedian(vh[M["arriba"] & v])), 2) if (M["arriba"] & v).any() else None
            rows.append(cuenta(row, M, v, {f"vh{abs(t)}": vh >= t for t in (-16, -15, -14, -13, -12)}))
            if k % 25 == 0: print("s1", k, d, row["vh_agua_mediana"], flush=True); guardar(prev, rows, "escenas_s1.csv")
        except Exception as e: print("error s1", d, str(e)[:150], flush=True)
    E = guardar(prev, rows, "escenas_s1.csv"); print("S1 listo: nuevas", len(rows), "total", len(E), flush=True)

def corre_ls():
    Z50, Z25, D = zona(); M = {k: v for k, v in mascaras(Z50, Z25, D).items() if not k.endswith("25")}
    g = por_fecha("landsat-c2-l2", {"query": {"platform": {"in": ["landsat-8", "landsat-9"]}}}); print("fechas Landsat:", len(g), flush=True)
    prev = previo("escenas_ls.csv"); hechas = set(prev.fecha.astype(str)); rows = []
    for k, d in enumerate(sorted(x for x in g if x not in hechas)):
        try:
            val = np.zeros(SH, bool); red = np.full(SH, np.nan, "float32"); nir = red.copy()
            for it in g[d]:
                it = firmar(it)
                qa = a_grilla(it.assets["qa_pixel"].href, Resampling.nearest, "uint16", 1, 1)
                ok = (qa > 1) & ((qa & 0b11110) == 0) & ~val
                if not ok.any(): continue
                rr = a_grilla(it.assets["red"].href) * 0.0000275 - 0.2; nn = a_grilla(it.assets["nir08"].href) * 0.0000275 - 0.2
                red[ok] = rr[ok]; nir[ok] = nn[ok]; val |= ok
            nd = (nir - red) / (nir + red + 1e-6); v = val & np.isfinite(nd)
            if (v & M["arriba"]).sum() < 0.05 * M["arriba"].sum(): continue
            rows.append(cuenta(dict(fecha=d, plat=g[d][0].properties.get("platform")), M, v, {"ndvi30": nd >= 0.30, "ndvi40": nd >= 0.40}))
            if k % 25 == 0: print("ls", k, d, flush=True); guardar(prev, rows, "escenas_ls.csv")
        except Exception as e: print("error ls", d, str(e)[:150], flush=True)
    E = guardar(prev, rows, "escenas_ls.csv"); print("Landsat listo: nuevas", len(rows), "total", len(E), flush=True)

# ---------------- serie y precisión ----------------
def serie():
    z = np.load(f"{OUT}/zona.npz"); Z50, Z25, D = z["Z50"], z["Z25"], z["D"]; M = mascaras(Z50, Z25, D)
    TRM = tramos(D); keys = ["ret", "bar", "arriba"] + [f"t{a}_{b}" for a, b in TRM]
    rd = lambda n: pd.read_csv(f"{OUT}/{n}") if os.path.exists(f"{OUT}/{n}") else pd.DataFrame()
    s2, s1, ls = rd("escenas_s2.csv"), rd("escenas_s1.csv"), rd("escenas_ls.csv")
    def val(r, k, ind, minv=0.6):
        ar, vl, vg = r.get(f"{k}_area_px"), r.get(f"{k}_valid_px"), r.get(f"{k}_{ind}")
        if not ar or vl != vl or vg != vg or vl < minv * ar: return None
        return vg / vl * (100.0 if k == "bar" else ar * HA)
    def tabla(df, ind, ks=keys):
        O = {}
        for r in df.to_dict("records"):
            o = {k: val(r, k, ind) for k in ks}; o = {k: round(v, 2) for k, v in o.items() if v is not None}
            if o: O[str(r["fecha"])] = o
        return O
    O = tabla(s2, "ndvi30")
    def pares(A, Bt, k, dias):
        fa = pd.to_datetime(pd.Series(list(A.keys()))); P = []
        if not len(fa): return np.zeros((0, 2))
        for f, o in Bt.items():
            if k not in o: continue
            j = (fa - pd.Timestamp(f)).abs(); i = int(j.values.argmin())
            if j.iloc[i] <= pd.Timedelta(days=dias) and k in A[fa.iloc[i].strftime("%Y-%m-%d")]: P.append((A[fa.iloc[i].strftime("%Y-%m-%d")][k], o[k]))
        return np.array(P) if P else np.zeros((0, 2))
    def acuerdo(P):
        if len(P) < 10: return dict(n=int(len(P)))
        return dict(n=int(len(P)), rho=round(float(pd.Series(P[:, 0]).corr(pd.Series(P[:, 1]), method="spearman")), 3),
                    sesgo_ha=round(float(np.median(P[:, 1] - P[:, 0])), 2), mae_ha=round(float(np.mean(np.abs(P[:, 1] - P[:, 0]))), 2),
                    mediana_ref_ha=round(float(np.median(P[:, 0])), 2))
    cal = {}
    R = {}; Lt = {}
    if len(s1):
        for t in (16, 15, 14, 13, 12): cal[f"vh{t}"] = acuerdo(pares(O, tabla(s1, f"vh{t}", ["arriba"]), "arriba", 3))
        if "arriba_ll_area_px" in s1.columns and "arriba_ll_area_px" in s2.columns:
            Oll = tabla(s2, "ndvi30", ["arriba_ll"])
            for t in (16, 15, 14, 13, 12): cal[f"lejos_laderas_vh{t}"] = acuerdo(pares(Oll, tabla(s1, f"vh{t}", ["arriba_ll"]), "arriba_ll", 3))
        ok = {k: v for k, v in cal.items() if k.startswith("vh") and v.get("rho") is not None}
        el = min(ok, key=lambda k: ok[k]["mae_ha"]) if ok else None; cal["elegido"] = el
        if el: R = tabla(s1, el)
    cl = {}
    if len(ls):
        for t in ("ndvi30", "ndvi40"): cl[t] = acuerdo(pares(O, tabla(ls, t, ["arriba"]), "arriba", 1))
        ok = {k: v for k, v in cl.items() if v.get("rho") is not None}
        el = min(ok, key=lambda k: ok[k]["mae_ha"]) if ok else None; cl["elegido"] = el
        if el: Lt = tabla(ls, el)
    # precisión del óptico
    prec = {}
    if len(s2):
        base = tabla(s2, "ndvi30", ["arriba", "ret"])
        for ind in ("ndvi20", "ndvi40", "fai02", "fai05", "ndvi30_20m"):
            alt = tabla(s2, ind, ["arriba", "ret"])
            for k in ("arriba", "ret"):
                P = np.array([(base[f][k], alt[f][k]) for f in base if f in alt and k in base[f] and k in alt[f] and base[f][k] >= 0.5])
                if len(P) >= 10:
                    prec[f"{ind}_{k}"] = dict(n=len(P), razon_mediana=round(float(np.median(P[:, 1] / P[:, 0])), 3),
                                              p10=round(float(np.percentile(P[:, 1] / P[:, 0], 10)), 3), p90=round(float(np.percentile(P[:, 1] / P[:, 0], 90)), 3),
                                              rho=round(float(pd.Series(P[:, 0]).corr(pd.Series(P[:, 1]), method="spearman")), 3))
        z25 = tabla(s2, "ndvi30", ["arriba25"])
        P = np.array([(base[f]["arriba"], z25[f]["arriba25"]) for f in base if f in z25 and "arriba" in base[f] and base[f]["arriba"] >= 0.5])
        if len(P) >= 10: prec["zona25_arriba"] = dict(n=len(P), razon_mediana=round(float(np.median(P[:, 1] / P[:, 0])), 3), p10=round(float(np.percentile(P[:, 1] / P[:, 0], 10)), 3), p90=round(float(np.percentile(P[:, 1] / P[:, 0], 90)), 3))
        # repetibilidad: dos fechas ópticas a ≤ 5 días (incluye cambio real: cota superior del ruido)
        fs = sorted(base); dd = []
        for a, b in zip(fs, fs[1:]):
            if (pd.Timestamp(b) - pd.Timestamp(a)).days <= 5 and "ret" in base[a] and "ret" in base[b]: dd.append(abs(base[b]["ret"] - base[a]["ret"]))
        if dd: prec["repetibilidad_ret_5d"] = dict(n=len(dd), mediana_ha=round(float(np.median(dd)), 2), p90_ha=round(float(np.percentile(dd, 90)), 2))
    agua = {k: round(float(M[k].sum()) * HA, 1) for k in keys if k in M}
    json.dump(dict(generado=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), contorno="contorno_analisis.kml (2-nov-2026)",
                   km_aguas_arriba=round(float(-np.nanmin(D)), 2), km_aguas_abajo=round(float(np.nanmax(D)), 2),
                   tramos=[f"{a}..{b}" for a, b in TRM], claves=keys, agua_ha=agua, optico=O, radar=R, landsat=Lt,
                   calibracion_radar=cal, calibracion_landsat=cl, precision=prec,
                   terreno=(json.load(open(f"{OUT}/terreno.json")) if os.path.exists(f"{OUT}/terreno.json") else None),
                   definiciones=dict(ret="0–2,5 km aguas arriba por el río", bar="0–100 m aguas arriba de la barrera (% cubierto)", arriba="todo el contorno aguas arriba")),
              open(f"{OUT}/serie.json", "w"), separators=(",", ":"))
    print("serie: ópticas", len(O), "radar", len(R), "landsat", len(Lt), "\nradar", cal, "\nlandsat", cl, "\nprecisión", json.dumps(prec, ensure_ascii=False), flush=True)

# ---------------- exploración de catálogos ----------------
def explorar():
    import urllib.request
    res = {}
    for c in ["sentinel-2-l2a", "sentinel-1-rtc", "sentinel-1-grd", "landsat-c2-l2", "hls2-s30", "hls2-l30", "esa-worldcover", "jrc-gsw",
              "cop-dem-glo-30", "alos-palsar-mosaic", "io-lulc-annual-v02", "modis-09Q1-061", "sentinel-3-olci-wfr-l2-netcdf", "nasadem", "alos-dem"]:
        try: res[c] = len(list(catalogo().search(collections=[c], bbox=BBOX, datetime=f"2019-01-01/{dt.date.today()}", max_items=3000).items()))
        except Exception as e: res[c] = "error: " + str(e)[:100]
        print("PC", c, res[c], flush=True)
    bb = ",".join(f"{v:.4f}" for v in BBOX); cmr = {}
    for sn in ["OPERA_L3_DSWX-HLS_V1", "OPERA_L3_DSWX-S1_V1", "OPERA_L2_RTC-S1_V1", "HLSS30", "HLSL30", "SWOT_L2_HR_RiverSP_2.0", "SWOT_L2_HR_LakeSP_2.0",
               "SWOT_L2_HR_Raster_2.0", "SWOT_L2_HR_PIXC_2.0", "EMITL2ARFL", "ECO_L2T_LSTE", "GPM_3IMERGDF"]:
        try:
            u = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name={sn}&bounding_box={bb}&temporal=2019-01-01T00:00:00Z,{dt.date.today()}T23:59:59Z&page_size=1"
            with urllib.request.urlopen(u, timeout=60) as r: cmr[sn] = int(r.headers.get("CMR-Hits", -1))
        except Exception as e: cmr[sn] = "error: " + str(e)[:100]
        print("CMR", sn, cmr[sn], flush=True)
    try:
        u = "https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NISAR&page_size=50"
        with urllib.request.urlopen(u, timeout=60) as r: nis = [e.get("short_name") for e in json.load(r)["feed"]["entry"]]
        cmr["NISAR_colecciones"] = nis
        for sn in [s for s in nis if s and ("GCOV" in s or "GSLC" in s)][:4]:
            u = f"https://cmr.earthdata.nasa.gov/search/granules.json?short_name={sn}&bounding_box={bb}&page_size=1"
            with urllib.request.urlopen(u, timeout=60) as r: cmr["NISAR:" + sn] = int(r.headers.get("CMR-Hits", -1))
    except Exception as e: cmr["NISAR"] = "error: " + str(e)[:100]
    print("NISAR", cmr.get("NISAR_colecciones"), flush=True)
    json.dump(dict(generado=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), bbox=BBOX, planetary_computer=res, nasa_cmr=cmr), open(f"{OUT}/catalogos.json", "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "s2"
    print("grilla", SH, "contorno", int(DENTRO.sum()) * HA, "ha", flush=True)
    if modo == "explorar": explorar(); zona(force=True)
    if modo == "zona": zona(force=True); terreno()
    if modo == "terreno": terreno()
    if modo == "s2": corre_s2()
    if modo == "s1": corre_s1()
    if modo == "ls": corre_ls()
    if modo == "serie": serie()
