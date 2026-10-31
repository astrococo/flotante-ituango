"""Subzonas por margen sobre la zona de agua de Sentinel-2.
Margen derecha (oriental) e izquierda (occidental) respecto al eje del cauce en cada fila; el Cauca fluye de sur a norte,
así que la margen derecha hidrográfica es la oriental. Orilla = franja de agua a ≤ 100 m de tierra."""
import numpy as np
from scipy import ndimage
from comun_grilla import SH, Z, SUR, yy, xx, r0, c0
eje = np.full(SH[0], np.nan)
for r in range(SH[0]):
    c = np.where(Z[r])[0]
    if c.size: eje[r] = (c.min() + c.max()) / 2           # eje = punto medio entre orillas de la fila
ok = ~np.isnan(eje); eje = np.interp(np.arange(SH[0]), np.where(ok)[0], eje[ok])
ESTE = xx > eje[:, None]
dist = ndimage.distance_transform_edt(Z) * 10             # m a la tierra más cercana
ORILLA = Z & (dist <= 100)
CERCA = np.hypot((yy - r0) * 10, (xx - c0) * 10) <= 600   # 600 m alrededor de la barrera
SUBZ = {
    "arriba_der": Z & SUR & ESTE, "arriba_izq": Z & SUR & ~ESTE,
    "abajo_der": Z & ~SUR & ESTE, "abajo_izq": Z & ~SUR & ~ESTE,
    "orilla_der_arriba": ORILLA & SUR & ESTE, "orilla_der_abajo": ORILLA & ~SUR & ESTE,
    "barrera_arriba": Z & SUR & CERCA, "barrera_abajo": Z & ~SUR & CERCA,
    "barrera_arriba_der": Z & SUR & CERCA & ESTE,
}
