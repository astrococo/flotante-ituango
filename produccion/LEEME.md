# Producción diaria → datos de la plataforma

Fuente: `OT3_001_Producción_Diaria_<fecha>.xlsx` (no se publica: contiene datos internos). Hojas usadas:
`Viajes-Macrofitas_Mecanizado`, `Viajes-MF-Mecanizado-EPM`, `Viajes-diario-macrofitas_Manual`, `Viajes-diario-MF_Manual`.

Orden: `tidy.py` (lee celdas, fórmulas y comentarios) → `mec.py` (viajes por volqueta, auditoría de fórmulas) →
`build.py` (correcciones por fecha, serie diaria) → `semanal.py` (causas y semanas) → `exp_*.py` (backtests).

Salidas publicadas: `datos/DatosExtraccion.xlsx` (mismo formato de siempre, con hoja «Depuración») y
`datos/produccion/esfuerzo_diario.csv` (operación por día, sin textos de observaciones).
La versión anterior del Excel quedó en `datos/DatosExtraccion_original_2026-10-30.xlsx`.
