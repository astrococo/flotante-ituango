# Hoja de viajes (OT3_001) ↔ DatosExtracción

**Referencia: `datos/DatosExtraccion.xlsx` (sin cambios).** La hoja de viajes se ajusta a ella; el Excel fuente no se publica (contiene datos internos).

1. `tidy.py`, `mec.py`: leen celdas, fórmulas y comentarios de las hojas `Viajes-Macrofitas_Mecanizado`, `Viajes-MF-Mecanizado-EPM`, `Viajes-diario-macrofitas_Manual`, `Viajes-diario-MF_Manual`.
2. `alinear.py`: para cada fila de viajes, la fecha con que la usa `Info_día_PHI-integrado` (origen de DatosExtracción).
3. `plan.py`, `aplicar.py`: re-fechan filas y ajustan los pocos valores repetidos u omitidos por el informe; editan el XML del libro (no se toca ninguna otra hoja) y quitan la cadena de cálculo con recálculo al abrir. Registro de cambios en `Ajustes_archivo_viajes.xlsx`.
4. `build_aj.py`, `semanal_aj.py`, `esf.py`: operación diaria y semanal con esas fechas → `datos/produccion/esfuerzo_diario.csv` y la pestaña Operación.
5. `exp_*_aj.py`: backtests (descanso programado, calendario, caudal).
