"""Resume la serie satelital para la app: datos/satelite/app/serie.json y mapas PNG de frecuencia anual de vegetación flotante.
Criterios: núcleo de la zona de agua (agua en ≥50 % de las escenas despejadas, 2,5 km alrededor de la barrera), NDVI ≥ 0,30,
escenas con ≥70 % del núcleo despejado, una escena por fecha."""
import os, glob, json, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun_const import BARRERA as BARRERA_PUNTO, BARRERA_LINEA, BARRERA, PUERTO, DEPOSITO
from PIL import Image
R = os.path.dirname(os.path.abspath(__file__)) + "/.."
S = f"{R}/datos/satelite/series"; O = f"{R}/datos/satelite/app"; os.makedirs(O, exist_ok=True)
E = pd.read_csv(f"{S}/escenas.csv", parse_dates=["fecha"])
z = "z50"; E["vf"] = E[f"{z}_total_valid_px"] / E[f"{z}_total_area_px"]
for lado in ("total", "arriba", "abajo"):
    E[lado] = E[f"{z}_{lado}_ndvi30"] / E[f"{z}_{lado}_valid_px"].clip(lower=1) * E[f"{z}_{lado}_area_px"] / 100
    for t in (20, 40): E[f"{lado}_{t}"] = E[f"{z}_{lado}_ndvi{t}"] / E[f"{z}_{lado}_valid_px"].clip(lower=1) * E[f"{z}_{lado}_area_px"] / 100
E = E.sort_values("vf").drop_duplicates("fecha", keep="last").sort_values("fecha")
C = E[E.vf >= 0.70]
G = json.load(open(f"{S}/grilla.json"))
area = {k: round(E[f"{z}_{k}_area_px"].iloc[0] / 100, 1) for k in ("total", "arriba", "abajo")}
ql = sorted(os.path.basename(f)[3:13] for f in glob.glob(f"{S}/ql_*.jpg"))
r0, c0 = G["barrera_px"]
# mapas: base = vista previa más reciente en gris, superposición = frecuencia anual (0–1)
base_d = ql[-1]; base = np.asarray(Image.open(f"{S}/ql_{base_d}.jpg").convert("L"), dtype=float) / 255
mapas = []
for f in sorted(glob.glob(f"{S}/frec_veg_*.npy")):
    y = f[-8:-4]; fr = np.load(f)
    rgb = np.dstack([base * 0.55 + 0.2] * 3)
    a = np.clip(np.nan_to_num(fr) / 0.5, 0, 1)[..., None]
    col = np.array([0.06, 0.73, 0.51])                           # verde (macrófitas)
    rgb = rgb * (1 - a) + col * a
    img = (np.clip(rgb, 0, 1) * 255).astype("uint8")
    if "barrera_linea_px" in G:
        (a1, b1), (a2, b2) = G["barrera_linea_px"]
        for t_ in np.linspace(0, 1, 60):
            rr, cc = int(round(a1 + (a2 - a1) * t_)), int(round(b1 + (b2 - b1) * t_)); img[rr - 1:rr + 2, cc - 1:cc + 2] = [239, 68, 68]
    else:
        img[r0 - 9:r0 + 10, c0 - 1:c0 + 2] = [239, 68, 68]; img[r0 - 1:r0 + 2, c0 - 9:c0 + 10] = [239, 68, 68]
    Image.fromarray(img).save(f"{O}/frecuencia_{y}.png", optimize=True); mapas.append(y)
# vista previa de la escena despejada más reciente
Image.open(f"{S}/ql_{base_d}.jpg").save(f"{O}/ultima_escena.jpg", quality=85)
ser = [dict(f=d.strftime("%Y-%m-%d"), t=round(t, 2), a=round(a, 2), b=round(b, 2), t20=round(t20, 2), t40=round(t40, 2), v=round(v, 2))
       for d, t, a, b, t20, t40, v in zip(C.fecha, C.total, C.arriba, C.abajo, C.total_20, C.total_40, C.vf)]
todas = [dict(f=d.strftime("%Y-%m-%d"), v=round(v, 2)) for d, v in zip(E.fecha, E.vf)]
# Landsat 8/9 (30 m): NDVI ≥ 0,40 reproduce el área de Sentinel-2 (NDVI ≥ 0,30) en fechas con ≤3 días de diferencia
lsat = []
LP = f"{R}/datos/satelite/landsat/escenas_landsat.csv"
if os.path.exists(LP):
    L = pd.read_csv(LP, parse_dates=["fecha"]); L["vf"] = L.total_valid_px / L.total_area_px
    L = L[L.vf >= 0.70].sort_values("vf").drop_duplicates("fecha", keep="last").sort_values("fecha")
    for lado in ("total", "arriba", "abajo"):
        L[lado] = L[f"{lado}_ndvi40"] / L[f"{lado}_valid_px"].clip(lower=1) * L[f"{lado}_area_px"] / 100
    lsat = [dict(f=d.strftime("%Y-%m-%d"), t=round(t, 2), a=round(a_, 2), b=round(b, 2), v=round(v, 2), p=p_[-1])
            for d, t, a_, b, v, p_ in zip(L.fecha, L.total, L.arriba, L.abajo, L.vf, L.plat)]
# Sentinel-1 RTC (radar, sin nubes): VH ≥ −14 dB reproduce el área total de Sentinel-2 (90 fechas, ρ = 0,75);
# aguas arriba (tramo de río, agua turbulenta) no concuerda (ρ = 0,43) y no se publica.
s1 = []
SP = f"{R}/datos/satelite/s1/escenas_s1.csv"
if os.path.exists(SP):
    Q = pd.read_csv(SP, parse_dates=["fecha"]).sort_values("fecha").drop_duplicates("fecha", keep="last")
    Q["t"] = Q.total_vh14 / Q.total_valid_px.clip(lower=1) * Q.total_area_px / 100
    Q["b"] = Q.abajo_vh14 / Q.abajo_valid_px.clip(lower=1) * Q.abajo_area_px / 100
    Q["a"] = Q.arriba_vh14 / Q.arriba_valid_px.clip(lower=1) * Q.arriba_area_px / 100
    _v = json.load(open(f"{R}/datos/satelite/s1/validacion_s1ml.json")) if os.path.exists(f"{R}/datos/satelite/s1/validacion_s1ml.json") else None
    _usa_a = bool(_v and _v["arriba"]["rho_umbral"] >= 0.6)
    s1 = [dict(f=d.strftime("%Y-%m-%d"), t=round(t, 2), b=round(b, 2), **({"a": round(a, 2)} if _usa_a else {})) for d, t, b, a in zip(Q.fecha, Q.t, Q.b, Q.a)]
# Margen del cauce (derecha = oriental, donde se extrae el material), Sentinel-2 (NDVI ≥ 0,30) y Landsat (NDVI ≥ 0,40)
marg = []
for f_, t_, s_ in (("escenas_s2.csv", 30, "S2"), ("escenas_landsat.csv", 40, "L")):
    MP = f"{R}/datos/satelite/margenes/{f_}"
    if not os.path.exists(MP): continue
    M = pd.read_csv(MP, parse_dates=["fecha"]); M["vf"] = M.total_valid_px / M.total_area_px
    M = M[M.vf >= 0.70].sort_values("vf").drop_duplicates("fecha", keep="last")
    for z in ("arriba_der", "arriba_izq", "abajo_der", "abajo_izq"):
        M[z] = M[f"{z}_ndvi{t_}"] / M[f"{z}_valid_px"].clip(lower=1) * M[f"{z}_area_px"] / 100
    marg += [dict(f=d.strftime("%Y-%m-%d"), s=s_, ad=round(a1, 2), ai=round(a2, 2), bd=round(b1, 2), bi=round(b2, 2))
             for d, a1, a2, b1, b2 in zip(M.fecha, M.arriba_der, M.arriba_izq, M.abajo_der, M.abajo_izq)]
marg = sorted(marg, key=lambda r: r["f"])
# radar calibrado píxel a píxel (s1ml.py): se usa si en la validación por años supera al umbral fijo
s1val = dict(n=90, rho=0.75, sesgo_ha=3.1, mae_ha=11.3, umbral="VH ≥ −14 dB", rho_abajo=0.78, rho_arriba=0.43)
if os.path.exists(f"{R}/datos/satelite/s1/validacion_s1ml.json"):      # validación con la línea de la barrera (pares ±2 días)
    _v = json.load(open(f"{R}/datos/satelite/s1/validacion_s1ml.json"))
    s1val = dict(n=_v["total"]["n"], rho=_v["total"]["rho_umbral"], mae_ha=_v["total"]["mae_umbral"], umbral="VH ≥ −14 dB", rho_abajo=_v["abajo"]["rho_umbral"], rho_arriba=_v["arriba"]["rho_umbral"],
                 usa_arriba=_v["arriba"]["rho_umbral"] >= 0.6, clasificador=dict(rho=_v["total"]["rho_ml"], mae_ha=_v["total"]["mae_ml"], rho_arriba=_v["arriba"]["rho_ml"]))
MLP = f"{R}/datos/satelite/s1/escenas_s1ml.csv"; MLV = f"{R}/datos/satelite/s1/validacion_s1ml.json"
if os.path.exists(MLP) and os.path.exists(MLV):
    vv_ = json.load(open(MLV))
    if vv_["total"]["rho_ml"] > vv_["total"]["rho_umbral"]:
        Q = pd.read_csv(MLP); usa_a = vv_.get("arriba", {}).get("rho_ml", 0) >= 0.6
        s1 = [dict(f=r.fecha, t=round(r.t, 2), b=round(r.b, 2), **({"a": round(r.a, 2)} if usa_a else {})) for r in Q.itertuples()]
        s1val = dict(n=vv_["total"]["n"], rho=vv_["total"]["rho_ml"], sesgo_ha=vv_["total"]["sesgo_ml"], mae_ha=vv_["total"]["mae_ml"], umbral="clasificador VV/VH + textura (entrenado con Sentinel-2)",
                     rho_abajo=vv_["abajo"]["rho_ml"], rho_arriba=vv_["arriba"]["rho_ml"], rho_umbral=vv_["total"]["rho_umbral"], mae_umbral=vv_["total"]["mae_umbral"], usa_arriba=usa_a)
# visor interactivo: límites geográficos de la grilla, barrera, máscaras de vegetación por fecha y vistas de radar
from pyproj import Transformer
VI = f"{R}/datos/satelite/visor"; os.makedirs(VI, exist_ok=True)
tf = Transformer.from_crs(G["crs"], 4326, always_xy=True); a_, b_, x0, c_, d_, y0 = G["transform"]; H_, W_ = G["shape"]
lo0, la0 = tf.transform(x0, y0 + d_ * H_); lo1, la1 = tf.transform(x0 + a_ * W_, y0)
vis = dict(bounds=[[la0, lo0], [la1, lo1]], punto=list(BARRERA_PUNTO), puerto=list(PUERTO), deposito=list(DEPOSITO), linea=[list(p) for p in BARRERA_LINEA], s2=[], s1=[])
MP = f"{S}/mascaras.npz"
if os.path.exists(MP):
    Mk = np.load(MP); un = lambda q: np.unpackbits(q)[:H_ * W_].reshape(H_, W_).astype(bool)
    Zz = np.load(f"{S}/zona_agua.npy") >= 0.5
    yy_, xx_ = np.mgrid[0:H_, 0:W_]; Zz &= np.hypot((yy_ - r0) * 10, (xx_ - c0) * 10) <= 2500
    ed = Zz & ~np.roll(Zz, 1, 0) | Zz & ~np.roll(Zz, 1, 1) | Zz & ~np.roll(Zz, -1, 0) | Zz & ~np.roll(Zz, -1, 1)
    zon = np.zeros((H_, W_, 4), "uint8"); zon[ed] = [56, 189, 248, 230]; Image.fromarray(zon).save(f"{VI}/zona.png", optimize=True)
    ok = set(C.fecha.dt.strftime("%Y-%m-%d"))
    for f_, v_, g_ in zip(Mk["fechas"], Mk["val"], Mk["veg"]):
        f_ = str(f_)
        if f_ not in ok: continue
        V_, G_ = un(v_), un(g_); im = np.zeros((H_, W_, 4), "uint8")
        im[G_ & Zz] = [16, 185, 129, 210]; im[G_ & ~Zz] = [16, 185, 129, 70]; im[~V_ & Zz] = [255, 255, 255, 90]
        Image.fromarray(im).save(f"{VI}/veg_{f_}.png", optimize=True)
        vis["s2"].append(dict(f=f_, ql=os.path.exists(f"{S}/ql_{f_}.jpg")))
vis["s1"] = sorted(os.path.basename(f)[3:13] for f in glob.glob(f"{VI}/s1_*.jpg"))
json.dump(vis, open(f"{VI}/visor.json", "w"), separators=(",", ":"))
json.dump(dict(margen=marg, s1=s1, s1_validacion=s1val, landsat=lsat, landsat_validacion=dict(n=31, rho=0.82, sesgo_ha=-0.6, mae_ha=9.3, umbral="NDVI ≥ 0,40"), generado=pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M"), barrera=[6.900561, -75.8353999], barrera_linea=[list(p) for p in BARRERA_LINEA], area_ha=area,
               n_escenas=int(len(E)), n_utiles=int(len(C)), ultima_vista=base_d, mapas=mapas, serie=ser, todas=todas,
               metodo=dict(sensor="Sentinel-2 L2A (10 m), Microsoft Planetary Computer", nubes="SCL: válidos 4, 5, 6, 7",
                           agua="MNDWI > 0 en ≥ 50 % de las escenas despejadas, radio 2,5 km", vegetacion="NDVI ≥ 0,30", minimo_despejado=0.70)),
          open(f"{O}/serie.json", "w"), separators=(",", ":"))
print("serie", len(ser), "mapas", mapas, "última", base_d)
