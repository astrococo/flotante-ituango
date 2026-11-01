"""
Pronóstico de extracción de material flotante y macrófitas · Cola del embalse Ituango
-------------------------------------------------------------------------------------
Mismo modelo que la plataforma web. Pensado para integrarse al backend de HydroForecast
(FastAPI en localhost:8001) y consumir su pronóstico de caudal Sitio Presa.

Uso rápido:
    import pandas as pd, json
    from modelo_flotante import cargar_extraccion, pronosticar
    ext = cargar_extraccion("DatosExtracción.xlsx")
    q   = serie_diaria_sitiopresa   # pd.Series indexada por fecha (observado + pronóstico)
    fc  = pronosticar(ext, q, json.load(open("params_v21.json")))

Router opcional para HydroForecast (ver al final): GET /api/flotante/pronostico
"""
import numpy as np
import pandas as pd

# ------------------------------------------------------------------ depuración
def cargar_extraccion(xlsx_path: str) -> pd.DataFrame:
    """Lee el Excel de extracción, rellena avances diarios vacíos con la diferencia de
    acumulados, construye calendario continuo y marca regímenes operativos."""
    mf = pd.read_excel(xlsx_path, "Material Flotante", header=None, skiprows=3,
                       names=["fecha", "mf_man", "mf_man_ac", "mf_mec", "mf_mec_ac"])
    ma = pd.read_excel(xlsx_path, "Macrófitas", header=None, skiprows=3,
                       names=["fecha", "kg", "kg_ac", "ma_man", "ma_man_ac", "ma_mec", "ma_mec_ac"])
    for d, cols in ((mf, [("mf_man", "mf_man_ac"), ("mf_mec", "mf_mec_ac")]),
                    (ma, [("ma_man", "ma_man_ac"), ("ma_mec", "ma_mec_ac")])):
        d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce")
        d.dropna(subset=["fecha"], inplace=True)
        for dc, ac in cols:
            fill = d[ac].diff().clip(lower=0)
            d[dc] = d[dc].fillna(fill).fillna(0)
    df = mf.merge(ma, on="fecha").set_index("fecha").sort_index()
    df = df[["mf_man", "mf_mec", "ma_man", "ma_mec"]]
    df["reportado"] = 1
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="D"))
    df["reportado"] = df["reportado"].fillna(0).astype(int)
    df[["mf_man", "mf_mec", "ma_man", "ma_mec"]] = df[["mf_man", "mf_mec", "ma_man", "ma_mec"]].fillna(0)  # sin reporte = no se extrajo
    df["mf_tot"] = df.mf_man + df.mf_mec
    df["ma_tot"] = df.ma_man + df.ma_mec
    df["tot"] = df.mf_tot + df.ma_tot
    df["sin_operacion"] = _rachas(df.tot.fillna(0).eq(0), 7)
    df["mecanizado_detenido"] = _rachas((df.mf_mec.fillna(0) + df.ma_mec.fillna(0)).eq(0), 10)
    df["op"] = ((df.sin_operacion == 0) & (df.mecanizado_detenido == 0)).astype(int)
    return df


def _rachas(z: pd.Series, min_len: int) -> pd.Series:
    g = (z != z.shift()).cumsum()
    return (z & (z.groupby(g).transform("size") >= min_len)).astype(int)


# ------------------------------------------------------------------ pronóstico (modelo v2)
def pronosticar(ext: pd.DataFrame, q_sitiopresa: pd.Series, params: dict) -> pd.DataFrame:
    """Pronóstico diario desde el día siguiente al último reporte hasta el final de q_sitiopresa.

    Por semana h y componente:
        f(h)  = [k·a(h)·L8 + (1 − k·a(h))·LT] · m(h),   a(h) = a1·exp(−(h−1)/τ)
        m(h)  = clip(√exp(b0 + Σ β_l·x_{h−l}), 0,7, 1,5),  x = exceso semanal de Sitio Presa sobre qc
        P50   = (f + 50)·q50(h) − 50   (mediana calibrada en el backtest)
        E     = (f + 50)·r̄(h) − 50     (valor esperado; usar para volúmenes acumulados)
    L8 = mediana de las últimas 8 semanas con operación; LT = mediana de semanas con operación desde 2020-07-01;
    k = peso de persistencia (adaptativo, recalibrado con el backtest).
    v2.3 (si params trae ewma_hl): EW = media exponencial de semanas con operación (vida media ewma_hl),
        f(h) = {w·[a8_h·L8 + (1−a8_h)·LT] + (1−w)·[(1 − s)·(a_h·EW + (1 − a_h)·LT) + s·LT]}·m(h)."""
    last = ext.index[ext.reportado == 1].max()
    q = q_sitiopresa.sort_index()
    end = q.index.max()
    out = {}
    for y in ("mf_tot", "ma_tot"):
        p = params[y]
        W = pd.DataFrame({"y": ext.loc[:last, y].fillna(0).resample("W-SUN").sum(),
                          "op": ext.loc[:last, "op"].resample("W-SUN").min(),
                          "n": ext.loc[:last, "op"].resample("W-SUN").size()})
        W = W[(W.n == 7) & (W.index <= last)]
        Wo = W[W.op == 1]
        L8 = Wo.y.tail(8).median()
        LT = Wo[Wo.index >= p.get("lt_desde", "2020-07-01")].y.median()
        k = p.get("k", 1.0)
        EW = Wo.y.ewm(halflife=p["ewma_hl"]).mean().iloc[-1] if p.get("ewma_hl") else None
        xq = ((q - p["qc"]).clip(lower=0) / 1000).resample("W-SUN").sum()
        rows = []
        for t in pd.date_range(last + pd.Timedelta(days=1), end):
            h = int(np.ceil((t - last).days / 7)); hh = min(h, 13) - 1
            we = t + pd.Timedelta(days=6 - t.dayofweek)
            xs = [xq.get(we - pd.Timedelta(weeks=l), 0.0) for l in range(7)]
            mult = 1.0 if p.get("usa_caudal") is False else float(np.clip(np.sqrt(np.exp(p["b0"] + np.dot(p["beta"], xs))), 0.7, 1.5))
            if EW is not None and p.get("a_h"):
                a, s_ = p["a_h"][hh], p.get("shrink", 0.0)
                w1 = (p.get("mezcla") or {}).get("w1", 0.0); a8 = p["a8_h"][hh] if p.get("a8_h") else 0.0
                fw = (w1 * (a8 * L8 + (1 - a8) * LT) + (1 - w1) * ((1 - s_) * (a * EW + (1 - a) * LT) + s_ * LT)) * mult
            else:
                ah = k * p["a1"] * np.exp(-(h - 1) / p["tau"])
                fw = (ah * L8 + (1 - ah) * LT) * mult
            cal = lambda r: max(0.0, (fw + 50) * r - 50) / 7 * p["dow"][t.dayofweek]
            rows.append(dict(fecha=t, h=h, mult=mult, p10=cal(p["q"]["0.1"][hh]), p50=cal(p["q"]["0.5"][hh]),
                             p90=cal(p["q"]["0.9"][hh]), esperado=cal(p["rmean"][hh])))
        out[y] = pd.DataFrame(rows).set_index("fecha")
    a, b = out["mf_tot"], out["ma_tot"]
    fc = pd.DataFrame({"horizonte_sem": a.h,
        "mf_p50": a.p50, "mf_p10": a.p10, "mf_p90": a.p90, "mf_esperado": a.esperado,
        "ma_p50": b.p50, "ma_p10": b.p10, "ma_p90": b.p90, "ma_esperado": b.esperado,
        "mult_mf": a.mult, "mult_ma": b.mult, "q_sitiopresa": q.reindex(a.index)})
    fc["total_p50"] = fc.mf_p50 + fc.ma_p50
    fc["total_esperado"] = fc.mf_esperado + fc.ma_esperado
    return fc


def factor_paros(ext: pd.DataFrame, col: str, semanas: int = 104) -> float:
    """Razón entre el volumen medio de todas las semanas y el de las semanas con operación
    normal, en las últimas `semanas` semanas completas. Multiplica el valor esperado para
    incluir la frecuencia histórica de paros (el pronóstico se calibra con operación normal)."""
    last = ext.index[ext.reportado == 1].max()
    W = pd.DataFrame({"y": ext.loc[:last, col].fillna(0).resample("W-SUN").sum(),
                      "op": ext.loc[:last, "op"].resample("W-SUN").min(),
                      "n": ext.loc[:last, "op"].resample("W-SUN").size()})
    W = W[(W.n == 7) & (W.index <= last)].tail(semanas)
    act = W[W.op == 1].y.mean()
    return float(min(1.0, W.y.mean() / act)) if act > 0 else 1.0


# ------------------------------------------------------------------ router FastAPI opcional
def crear_router(xlsx_path: str, params_path: str, obtener_q):
    """obtener_q(): función del backend que devuelve pd.Series diaria de Sitio Presa
    (observado reciente + /api/forecast/quarterly_outlook)."""
    import json
    from fastapi import APIRouter
    router = APIRouter(prefix="/api/flotante")
    params = json.load(open(params_path))

    @router.get("/pronostico")
    def pronostico():
        ext = cargar_extraccion(xlsx_path)
        fc = pronosticar(ext, obtener_q(), params)
        fc.index = fc.index.strftime("%Y-%m-%d")
        return {"ultimo_dato": str(ext.index[ext.reportado == 1].max().date()),
                "data": fc.round(1).reset_index(names="fecha").to_dict(orient="records")}
    return router
