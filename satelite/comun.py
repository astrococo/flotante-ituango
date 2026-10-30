"""Utilidades comunes para el análisis satelital de la cola del embalse Ituango.
Datos: Sentinel-2 L2A (Microsoft Planetary Computer, colección sentinel-2-l2a)."""
import numpy as np, rasterio, planetary_computer, pystac_client
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
BARRERA = (6.900561, -75.8353999)            # lat, lon (dato del área)
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
# SCL válidos: 4 vegetación, 5 suelo, 6 agua, 7 sin clasificar (baja prob. de nube), 2 sombra oscura de terreno, 11 nieve (no aplica)
SCL_OK = {2, 4, 5, 6, 7}
def catalogo():
    return pystac_client.Client.open(STAC)
def firmar(item):
    """Firma justo antes de leer (los tokens SAS vencen; planetary_computer los renueva)."""
    return planetary_computer.sign(item)
def bbox_grados(lat, lon, half_km):
    dlat = half_km / 111.32; dlon = half_km / (111.32 * np.cos(np.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
def leer(href, bbox4326, out_shape=None, resampling=rasterio.enums.Resampling.nearest):
    with rasterio.open(href) as src:
        b = transform_bounds("EPSG:4326", src.crs, *bbox4326, densify_pts=21)
        w = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=w, out_shape=out_shape, resampling=resampling, boundless=True, fill_value=0)
        tr = src.window_transform(w)
        if out_shape is not None:
            tr = tr * tr.scale(w.width / out_shape[1], w.height / out_shape[0])
        return arr, tr, src.crs
def reflectancia(item, banda, bbox, shape):
    """Reflectancia de superficie (0–1) remuestreada a `shape` (grilla de 10 m).
    Desde el baseline 04.00 (ene-2022) L2A trae un offset de −1000 (BOA_ADD_OFFSET)."""
    arr, _, _ = leer(item.assets[banda].href, bbox, out_shape=shape, resampling=rasterio.enums.Resampling.bilinear)
    arr = arr.astype("float32")
    base = item.properties.get("s2:processing_baseline", "00.00")
    off = -1000.0 if float(base) >= 4.0 else 0.0
    r = (arr + off) / 10000.0
    r[arr == 0] = np.nan
    return r
