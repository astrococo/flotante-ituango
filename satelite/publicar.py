"""Resume la serie satelital para la app: datos/satelite/app/serie.json y mapas PNG de frecuencia anual de vegetación flotante.
Criterios: núcleo de la zona de agua (agua en ≥50 % de las escenas despejadas, 2,5 km alrededor de la barrera), NDVI ≥ 0,30,
escenas con ≥70 % del núcleo despejado, una escena por fecha."""
import os, glob, json, numpy as np, pandas as pd
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
    s1 = [dict(f=d.strftime("%Y-%m-%d"), t=round(t, 2), b=round(b, 2)) for d, t, b in zip(Q.fecha, Q.t, Q.b)]
json.dump(dict(s1=s1, s1_validacion=dict(n=90, rho=0.75, sesgo_ha=3.1, mae_ha=11.3, umbral="VH ≥ −14 dB", rho_abajo=0.78, rho_arriba=0.43), landsat=lsat, landsat_validacion=dict(n=31, rho=0.82, sesgo_ha=-0.6, mae_ha=9.3, umbral="NDVI ≥ 0,40"), generado=pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M"), barrera=[6.900561, -75.8353999], area_ha=area,
               n_escenas=int(len(E)), n_utiles=int(len(C)), ultima_vista=base_d, mapas=mapas, serie=ser, todas=todas,
               metodo=dict(sensor="Sentinel-2 L2A (10 m), Microsoft Planetary Computer", nubes="SCL: válidos 4, 5, 6, 7",
                           agua="MNDWI > 0 en ≥ 50 % de las escenas despejadas, radio 2,5 km", vegetacion="NDVI ≥ 0,30", minimo_despejado=0.70)),
          open(f"{O}/serie.json", "w"), separators=(",", ":"))
print("serie", len(ser), "mapas", mapas, "última", base_d)
