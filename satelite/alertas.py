"""Alertas satelitales para la operación. Lee datos/satelite/corredor/serie.json (diario, Sentinel-2 20 m) y
datos/satelite/app/serie.json (núcleo: Sentinel-2, Landsat y radar) y escribe datos/satelite/alertas.json.
Reglas (percentiles de la historia de cada zona, solo escenas de los últimos 10 días):
  · llegada aguas arriba: un tramo de 2,5–30 km aguas arriba por encima de su percentil 90;
  · acumulación frente al puerto: agua entre el puerto y la barrera por encima de su percentil 90;
  · poco material en el puerto: ≤ 500 m del punto de extracción por debajo del percentil 10 en las dos últimas escenas;
  · posible paso por la barrera: entre dos escenas a ≤ 12 días, aguas arriba cae ≥ 50 % (≥ 5 ha) y aguas abajo sube ≥ 50 % (≥ 5 ha)."""
import os, json, datetime as dt, numpy as np, pandas as pd
R = os.path.dirname(os.path.abspath(__file__)) + "/../datos/satelite"
hoy = pd.Timestamp(dt.date.today()); act = []; hist_fallas = []
fmt = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
def nombre(t):
    a, b = [float(x) for x in t.split("..")]
    return f"{fmt(abs(b))}–{fmt(abs(a))} km aguas arriba" if b <= 0 else f"{fmt(a)}–{fmt(b)} km aguas abajo"
C = json.load(open(f"{R}/corredor/serie.json")) if os.path.exists(f"{R}/corredor/serie.json") else None
if C:
    S = pd.DataFrame(C["serie"]); S["f"] = pd.to_datetime(S.f)
    recientes = S[S.f >= hoy - pd.Timedelta(days=10)]
    for t in [t for t in C["tramos"] if float(t.split("..")[1]) <= -2.5] + ["bp"]:
        if t not in S: continue
        h = S[t].dropna(); r = recientes[t].dropna()
        if len(h) < 30 or not len(r): continue
        p90 = float(h.quantile(0.9)); v = float(r.iloc[-1]); f = recientes.loc[r.index[-1], "f"]
        if v > p90:
            txt = (f"Material acumulado entre el puerto y la barrera: {fmt(v)} ha" if t == "bp" else f"Llega material desde {nombre(t)}: {fmt(v)} ha") + f" (percentil 90 histórico: {fmt(p90)} ha), imagen del {f.date()}."
            act.append(dict(id=f"{t}-{f.date()}", tipo="acumulacion" if t == "bp" else "llegada", nivel="alta" if v > h.quantile(0.97) else "media", fecha=str(f.date()), texto=txt))
    if "p500" in S:
        h = S.p500.dropna(); r = recientes.p500.dropna()
        if len(h) >= 30 and len(r) >= 2 and (r.iloc[-2:] < h.quantile(0.1)).all() and h.quantile(0.1) > 0:
            f = recientes.loc[r.index[-1], "f"]
            act.append(dict(id=f"p500-{f.date()}", tipo="puerto", nivel="media", fecha=str(f.date()), texto=f"Poco material frente al punto de extracción en las dos últimas imágenes ({fmt(r.iloc[-1])} ha a ≤ 500 m; percentil 10: {fmt(h.quantile(0.1))} ha)."))
N = json.load(open(f"{R}/app/serie.json")) if os.path.exists(f"{R}/app/serie.json") else None
if N:
    rows = [dict(f=r["f"], a=r.get("a"), b=r.get("b"), s="S2") for r in N["serie"]] + [dict(f=r["f"], a=r.get("a"), b=r.get("b"), s="Landsat") for r in N.get("landsat", [])] + \
           [dict(f=r["f"], a=r.get("a"), b=r.get("b"), s="radar") for r in N.get("s1", []) if r.get("a") is not None]
    Q = pd.DataFrame(rows).dropna(subset=["a", "b"]); Q["f"] = pd.to_datetime(Q.f); Q = Q.sort_values("f").drop_duplicates("f", keep="last").reset_index(drop=True)
    for i in range(1, len(Q)):
        p, q = Q.iloc[i - 1], Q.iloc[i]
        if (q.f - p.f).days > 12: continue
        if p.a - q.a >= max(5, 0.5 * p.a) and q.b - p.b >= max(5, 0.5 * p.b):
            e = dict(desde=str(p.f.date()), hasta=str(q.f.date()), arriba=[round(p.a, 1), round(q.a, 1)], abajo=[round(p.b, 1), round(q.b, 1)], sensores=f"{p.s} → {q.s}")
            hist_fallas.append(e)
            if q.f >= hoy - pd.Timedelta(days=10):
                act.append(dict(id=f"barrera-{q.f.date()}", tipo="barrera", nivel="alta" if p.s == q.s else "media", fecha=str(q.f.date()),
                                texto=f"Posible paso de material por la barrera: aguas arriba bajó de {fmt(p.a)} a {fmt(q.a)} ha y aguas abajo subió de {fmt(p.b)} a {fmt(q.b)} ha entre el {p.f.date()} y el {q.f.date()}. Revisar en el visor" + ("." if p.s == q.s else f" (sensores distintos: {p.s} → {q.s}; confirmar).")))
json.dump(dict(generado=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), activas=act, posibles_pasos_barrera=hist_fallas), open(f"{R}/alertas.json", "w"), ensure_ascii=False, indent=1)
print("alertas activas:", len(act), "| posibles pasos por la barrera en la historia:", len(hist_fallas))
for a in act: print(" ·", a["texto"])
