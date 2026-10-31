"""Grilla y zona de agua del análisis Sentinel-2, reutilizadas por Sentinel-1 y Landsat."""
import json, numpy as np
from rasterio.transform import Affine
SER = "../datos/satelite/series"
G = json.load(open(f"{SER}/grilla.json")); SH = tuple(G["shape"]); TR = Affine(*G["transform"]); CRS = G["crs"]
FREQ = np.load(f"{SER}/zona_agua.npy")
r0, c0 = G["barrera_px"]; yy, xx = np.mgrid[0:SH[0], 0:SH[1]]
DENTRO = np.hypot((yy - r0) * 10, (xx - c0) * 10) <= 2500
Z = (FREQ >= 0.5) & DENTRO; SUR = yy > r0
LADOS = (("total", np.ones(SH, bool)), ("arriba", SUR), ("abajo", ~SUR))
