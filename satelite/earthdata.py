"""Datos de NASA Earthdata sobre el contorno de análisis (requiere el secreto EARTHDATA_TOKEN en GitHub; lo crea el usuario).
  swot   Nivel del agua medido por SWOT (KaRIn): nodos del río (≈200 m) dentro del contorno, series por Hydrocron (PO.DAAC).
  opera  OPERA DSWx-HLS y DSWx-S1 (30 m): clase de agua por fecha dentro de la zona de agua del contorno; se compara con la
         vegetación medida con Sentinel-2 la misma fecha (validación independiente).
  nisar  NISAR GCOV (radar en banda L, global desde jun-2026): retrodispersión por píxel frente a la máscara de vegetación de
         Sentinel-2 en fechas a ≤ 3 días (área bajo la curva ROC), y Sentinel-1 VH en las mismas fechas para comparar.
Uso: python earthdata.py swot | opera | nisar.   Salidas en datos/satelite/earthdata/."""
import os, sys, io, re, json, zipfile, datetime as dt, numpy as np, pandas as pd, requests
import contorno as C
from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine

OUT = "datos/satelite/earthdata"; os.makedirs(OUT, exist_ok=True)
TOKEN = os.environ.get("EARTHDATA_TOKEN", "").strip()
SES = requests.Session()
if TOKEN: SES.headers["Authorization"] = f"Bearer {TOKEN}"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
BB = ",".join(f"{v:.5f}" for v in C.BBOX)
HOY = dt.date.today().isoformat()

def cmr(short, desde="2019-01-01", extra=""):
    out, page = [], 1
    while True:
        u = f"{CMR}?short_name={short}&bounding_box={BB}&temporal={desde}T00:00:00Z,{HOY}T23:59:59Z&page_size=2000&page_num={page}{extra}"
        r = requests.get(u, timeout=120); r.raise_for_status(); e = r.json()["feed"]["entry"]
        out += e
        if len(e) < 2000: return out
        page += 1

def enlaces(g, patron):
    return [l["href"] for l in g.get("links", []) if l.get("href", "").startswith("https") and re.search(patron, l["href"]) and "s3credentials" not in l["href"]]

def bajar(url, dest):
    with SES.get(url, stream=True, timeout=600) as r:
        if r.status_code in (401, 403): raise PermissionError(f"HTTP {r.status_code}: revise EARTHDATA_TOKEN")
        r.raise_for_status()
        with open(dest, "wb") as f:
            for ch in r.iter_content(1 << 20): f.write(ch)
    return dest

def zona():
    z = np.load(f"{C.OUT}/zona.npz") if os.path.exists(f"{C.OUT}/zona.npz") else np.load(f"{C.PREV}/zona.npz")
    return z["Z50"], z["Z25"], z["D"]

def a_grilla_local(path, res=Resampling.nearest, nod=None, dtype="float32"):
    import rasterio
    dst = np.full(C.SH, np.nan if dtype.startswith("float") else 255, dtype)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=C.TR, dst_crs=C.CRS, resampling=res, src_nodata=nod if nod is not None else src.nodata, dst_nodata=dst[0, 0])
    return dst

# ---------------- SWOT ----------------
def swot():
    import shapefile                                    # pyshp
    from shapely.geometry import Point, Polygon
    poly = Polygon(C.POLY)
    gs = [g for g in cmr("SWOT_L2_HR_RiverSP_2.0", "2023-07-01") if "_Node_" in g.get("title", "")]
    print("granulos de nodos SWOT:", len(gs), flush=True)
    nodos = {}
    for g in gs[:12]:                                   # basta con unas pasadas para conocer los nodos del contorno
        for u in enlaces(g, r"\.zip$")[:1]:
            try:
                z = zipfile.ZipFile(io.BytesIO(SES.get(u, timeout=300).content))
                shp = [n for n in z.namelist() if n.endswith(".shp")][0]; base = shp[:-4]
                rd = shapefile.Reader(shp=io.BytesIO(z.read(base + ".shp")), dbf=io.BytesIO(z.read(base + ".dbf")))
                campos = [f[0] for f in rd.fields[1:]]
                for sr in rd.iterShapeRecords():
                    x, y = sr.shape.points[0]
                    if poly.contains(Point(x, y)):
                        rec = dict(zip(campos, sr.record)); nodos[str(rec["node_id"])] = dict(lon=x, lat=y, reach_id=str(rec.get("reach_id")))
            except Exception as e: print("error nodo", u[-60:], str(e)[:150], flush=True)
    print("nodos SWORD dentro del contorno:", len(nodos), flush=True)
    # distancia por el río de cada nodo (en la grilla del contorno)
    Z50, Z25, D = zona(); xs, ys = C.T.transform([n["lon"] for n in nodos.values()], [n["lat"] for n in nodos.values()])
    for (k, n), x, y in zip(nodos.items(), xs, ys):
        i = int((C.y1 - y) / C.RES); j = int((x - C.x0) / C.RES)
        w = D[max(0, i - 15):i + 16, max(0, j - 15):j + 16]
        n["km_rio"] = round(float(np.nanmedian(w)), 3) if np.isfinite(w).any() else None
    pd.DataFrame([dict(node_id=k, **v) for k, v in nodos.items()]).to_csv(f"{OUT}/swot_nodos.csv", index=False)
    filas = []
    for k in nodos:
        for campos in ("node_id,time_str,wse,wse_u,width,node_q", "node_id,time_str,wse"):
            u = ("https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries?feature=Node&feature_id=" + k +
                 "&start_time=2023-07-01T00:00:00%2b00:00&end_time=" + HOY + "T23:59:59%2b00:00&output=csv&fields=" + campos)
            try:
                r = requests.get(u, headers={"Accept": "text/csv"}, timeout=120)
                if r.status_code == 200:
                    df = pd.read_csv(io.StringIO(r.text)); df["node_id"] = k; filas.append(df); break
                elif r.status_code == 400 and campos.count(",") > 2: continue
                else: print("hydrocron", k, r.status_code, r.text[:120], flush=True); break
            except Exception as e: print("error hydrocron", k, str(e)[:120], flush=True); break
    S = pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()
    S.to_csv(f"{OUT}/swot_series.csv", index=False)
    print("SWOT: filas", len(S), "nodos con datos", S.node_id.nunique() if len(S) else 0, flush=True)

# ---------------- OPERA DSWx ----------------
def opera():
    Z50, Z25, D = zona(); M = C.mascaras(Z50, Z25, D); A = M["arriba"]; R = M["ret"]
    filas = []
    for short in ("OPERA_L3_DSWX-HLS_V1", "OPERA_L3_DSWX-S1_V1"):
        gs = cmr(short, "2019-01-01"); print(short, "gránulos:", len(gs), flush=True)
        prev = pd.read_csv(f"{OUT}/opera.csv") if os.path.exists(f"{OUT}/opera.csv") else pd.DataFrame(columns=["id"])
        hechos = set(prev.get("id", pd.Series(dtype=str)).astype(str))
        porfecha = {}
        for g in gs:
            if g["title"] in hechos: continue
            u = enlaces(g, r"B01_WTR\.tif$")
            if u: porfecha.setdefault(g["time_start"][:10], []).append((g["title"], u[0]))
        for k, (f, lst) in enumerate(sorted(porfecha.items())):
            wtr = np.full(C.SH, 255, "uint8")
            for tit, u in lst:
                try:
                    p = bajar(u, "/tmp/wtr.tif"); x = a_grilla_local(p, Resampling.nearest, 255, "uint8"); wtr = np.where(wtr == 255, x, wtr)
                except PermissionError as e: print(e, flush=True); return
                except Exception as e: print("error", tit[-40:], str(e)[:120], flush=True)
            for nombre, m in (("arriba", A), ("ret", R)):
                ok = m & (wtr <= 2)                         # 0 no agua, 1 agua abierta, 2 agua parcial; 252–255 nube/nieve/sin dato
                filas.append(dict(id=lst[0][0], producto=short.split("_")[2], fecha=f, zona=nombre, area_px=int(m.sum()), clara_px=int(ok.sum()),
                                  agua_px=int((ok & (wtr == 1)).sum()), parcial_px=int((ok & (wtr == 2)).sum()), no_agua_px=int((ok & (wtr == 0)).sum())))
            if k % 50 == 0:
                print(short, k, f, flush=True); pd.concat([prev, pd.DataFrame(filas)]).to_csv(f"{OUT}/opera.csv", index=False)
        prev = pd.concat([prev, pd.DataFrame(filas)]); prev.to_csv(f"{OUT}/opera.csv", index=False); filas = []
    print("OPERA listo", flush=True)

# ---------------- NISAR ----------------
def nisar():
    import h5py, rasterio
    from sklearn.metrics import roc_auc_score
    Z50, Z25, D = zona(); M = C.mascaras(Z50, Z25, D); A = M["arriba"]
    gs = []
    for sn in ("NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_GCOV_BETA_V1"): gs += [(sn, g) for g in cmr(sn, "2025-08-01")]
    print("gránulos NISAR GCOV:", len(gs), flush=True)
    s2 = C.por_fecha("sentinel-2-l2a"); s1 = C.por_fecha("sentinel-1-rtc"); filas = []
    for sn, g in gs:
        f = g["time_start"][:10]; ft = pd.Timestamp(f)
        cand = sorted([d for d in s2 if abs((pd.Timestamp(d) - ft).days) <= 3], key=lambda d: abs((pd.Timestamp(d) - ft).days))
        u = enlaces(g, r"\.h5$")
        if not u: continue
        fila = dict(fecha=f, producto=sn, gr=g["title"], s2=None)
        try:
            p = bajar(u[0], "/tmp/gcov.h5"); fila["mb"] = round(os.path.getsize(p) / 1e6)
            with h5py.File(p, "r") as h:
                grupos = []
                h.visititems(lambda n, o: grupos.append(n) if isinstance(o, h5py.Group) and "xCoordinates" in o and "yCoordinates" in o else None)
                fr = [x for x in grupos if x.endswith("frequencyA")] or grupos
                gr = h[fr[0]]; pols = [k for k in gr.keys() if re.fullmatch(r"(HH|HV|VV|VH){2}", k)]
                fila["pols"] = ",".join(pols)
                xc, yc = gr["xCoordinates"][:], gr["yCoordinates"][:]
                epsg = None
                for k in ("projection",):
                    if k in gr: epsg = int(gr[k][()]) if np.ndim(gr[k][()]) == 0 else None
                if epsg is None and "projection" in gr: epsg = int(gr["projection"].attrs.get("epsg_code", 0)) or None
                dx, dy = xc[1] - xc[0], yc[1] - yc[0]
                src_crs = f"EPSG:{epsg}" if epsg else C.CRS
                from rasterio.warp import transform_bounds
                bx = transform_bounds(C.CRS, src_crs, C.x0, C.y0, C.x1, C.y1)
                ix = np.where((xc >= bx[0] - 200) & (xc <= bx[2] + 200))[0]; iy = np.where((yc >= bx[1] - 200) & (yc <= bx[3] + 200))[0]
                if not len(ix) or not len(iy): print("NISAR fuera del contorno", f, flush=True); continue
                i0, i1, j0, j1 = iy.min(), iy.max() + 1, ix.min(), ix.max() + 1
                trs = Affine(dx, 0, xc[j0] - dx / 2, 0, dy, yc[i0] - dy / 2)
                for pol in pols:
                    arr = gr[pol][i0:i1, j0:j1].astype("float32"); arr[~np.isfinite(arr) | (arr <= 0)] = np.nan
                    dst = np.full(C.SH, np.nan, "float32")
                    reproject(arr, dst, src_transform=trs, src_crs=src_crs, dst_transform=C.TR, dst_crs=C.CRS, resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
                    fila[pol] = dst
            os.remove(p)
        except PermissionError as e: print(e, flush=True); return
        except Exception as e: print("error NISAR", f, str(e)[:200], flush=True); continue
        if not cand: fila.update(nota="sin Sentinel-2 a ≤ 3 días"); filas.append({k: v for k, v in fila.items() if not isinstance(v, np.ndarray)}); continue
        try:
            v, Bd = C.s2_mosaico(s2[cand[0]], ("B04", "B08")); nd = (Bd["B08"] - Bd["B04"]) / (Bd["B08"] + Bd["B04"] + 1e-6)
            ok = A & v & np.isfinite(nd); y = (nd >= 0.30)[ok]; fila["s2"] = cand[0]; fila["px"] = int(ok.sum()); fila["veg_frac"] = round(float(y.mean()), 4) if ok.any() else None
            for pol in [k for k in fila if isinstance(fila.get(k), np.ndarray)]:
                x = 10 * np.log10(fila[pol][ok]); m = np.isfinite(x)
                if m.sum() > 500 and 0 < y[m].mean() < 1: fila[f"auc_{pol}"] = round(float(roc_auc_score(y[m], x[m])), 3)
            c1 = sorted([d for d in s1 if abs((pd.Timestamp(d) - pd.Timestamp(cand[0])).days) <= 3], key=lambda d: abs((pd.Timestamp(d) - pd.Timestamp(cand[0])).days))
            if c1:
                acc = np.full(C.SH, np.nan, "float32")
                for it in s1[c1[0]]:
                    it = C.firmar(it); a_ = C.a_grilla(it.assets["vh"].href, Resampling.average, "float32", 0, np.nan); a_[a_ <= 0] = np.nan; acc = np.where(np.isnan(acc), a_, acc)
                x = 10 * np.log10(acc[ok]); m = np.isfinite(x)
                if m.sum() > 500 and 0 < y[m].mean() < 1: fila["s1"] = c1[0]; fila["auc_S1_VH"] = round(float(roc_auc_score(y[m], x[m])), 3)
        except Exception as e: print("error comparación", f, str(e)[:150], flush=True)
        filas.append({k: v for k, v in fila.items() if not isinstance(v, np.ndarray)}); print("NISAR", {k: v for k, v in fila.items() if not isinstance(v, np.ndarray)}, flush=True)
    pd.DataFrame(filas).to_csv(f"{OUT}/nisar.csv", index=False)

if __name__ == "__main__":
    if not TOKEN: sys.exit("Falta el secreto EARTHDATA_TOKEN en GitHub (Settings → Secrets and variables → Actions).")
    {"swot": swot, "opera": opera, "nisar": nisar}[sys.argv[1]]()
