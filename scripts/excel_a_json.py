"""Convierte datos/DatosExtraccion.xlsx en los arreglos de datos/app/base.json (lo que lee la app).
Mismas reglas que la depuración: avance diario faltante = diferencia del acumulado; día sin fila = 0 y no reportado."""
import json, hashlib, pandas as pd, numpy as np
F = "datos/DatosExtraccion.xlsx"; B = "datos/app/base.json"
mf = pd.read_excel(F, "Material Flotante", header=None, skiprows=3, names=["fecha", "mf_man", "mf_man_ac", "mf_mec", "mf_mec_ac"])
ma = pd.read_excel(F, "Macrófitas", header=None, skiprows=3, names=["fecha", "kg", "kg_ac", "ma_man", "ma_man_ac", "ma_mec", "ma_mec_ac"])
for d in (mf, ma): d["fecha"] = pd.to_datetime(d["fecha"], errors="coerce"); d.dropna(subset=["fecha"], inplace=True)
for c in ["mf_man", "mf_mec"]: mf.loc[mf[c].isna(), c] = mf[c + "_ac"].diff()[mf[c].isna()].clip(lower=0)
for c in ["ma_man", "ma_mec"]: ma.loc[ma[c].isna(), c] = ma[c + "_ac"].diff()[ma[c].isna()].clip(lower=0)
df = mf.groupby("fecha")[["mf_man", "mf_mec"]].sum().join(ma.groupby("fecha")[["ma_man", "ma_mec"]].sum(), how="outer").fillna(0)
J = json.load(open(B)); D = J["data"]; start = pd.Timestamp(D["start"])
last = max(df.index.max(), start + pd.Timedelta(days=D["n"] - 1)); idx = pd.date_range(start, last)
X = df.reindex(idx)
ext = len(idx) - D["n"]
for k in ["olaya", "pintada", "sitiopresa", "nivel", "olaya_max"]: D[k] = D[k] + [None] * ext
D["n"] = len(idx)
for k in ["mf_man", "mf_mec", "ma_man", "ma_mec"]: D[k] = [None if pd.isna(v) else round(float(v), 2) for v in X[k]]
D["rep"] = [0 if pd.isna(v) else 1 for v in X["mf_man"]]
J["xlsx_sha"] = hashlib.sha256(open(F, "rb").read()).hexdigest()
json.dump(J, open(B, "w"), ensure_ascii=False, separators=(",", ":"))
print("días", len(idx), "reportados", sum(D["rep"]), "último", df.index.max().date(), {k: round(sum(v or 0 for v in D[k]), 1) for k in ["mf_man", "mf_mec", "ma_man", "ma_mec"]})
