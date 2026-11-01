# Material Flotante Ituango

Plataforma web para analizar y pronosticar la extracción de **material flotante** y **macrófitas** en la cola del embalse del Proyecto Hidroeléctrico Ituango, a partir de los caudales del río Cauca pronosticados por [HydroForecast Ituango](https://jdguarnizor-hydroforecast-ituango.hf.space).

**Aplicación:** https://astrococo.github.io/flotante-ituango/

## Qué hace

| Pestaña | Contenido |
|---|---|
| Pronóstico | Volumen esperado por semana (mediana P50, valor esperado e intervalo P10–P90) para 90 días, con escenarios de caudal bajo, medio y alto. |
| Histórico | Extracción diaria, semanal o mensual por modalidad (manual / mecanizada) frente al caudal de Sitio Presa. |
| Caudal y material | Respuesta de la extracción después de crecientes, correlaciones con rezago y estacionalidad. |
| Operación | Días operados, causas de los días sin extracción (hoja de viajes OT3_001), caudal frente a operación y qué mejora el pronóstico. |
| Calidad del dato | Depuración aplicada, régimen operativo día a día, validación de acumulados y periodos excluidos. |
| Modelo y desempeño | Estructura, parámetros y error por horizonte (backtest 2022–2026); pronóstico real de HydroForecast frente al caudal observado. |
| Satélite | Vegetación flotante con Sentinel-2, Landsat y radar Sentinel-1; visor interactivo por fecha; corredor de 30 km aguas arriba; alertas y material frente al puerto. |
| Auditoría | Revisión de datos, modelo y plataforma con estado de cada punto. Ver también [AUDITORIA.md](AUDITORIA.md). |
| Datos | Cargar un Excel de extracción actualizado y elegir el servidor de HydroForecast. |
| Información requerida | Datos adicionales que mejorarían la precisión. |

## Arquitectura

- **Sitio estático** (GitHub Pages): `index.html` (estructura y estilos), `app.js` (lógica) y datos en `datos/app/base.json` y `datos/app/extra.json`. Chart.js, SheetJS y Leaflet están en `vendor/`. Instalable como aplicación (service worker, red primero).
- **Datos de extracción:** al subir `datos/DatosExtraccion.xlsx`, la tarea `datos` lo convierte en `datos/app/base.json` (`scripts/excel_a_json.py`); la página no descarga el Excel al abrir.
- **Caudal en vivo:** al abrir la página se consultan `GET /api/forecast/quarterly_outlook` y `GET /api/observed/daily?days=90` del backend de HydroForecast en Hugging Face, que permite consultas desde otros dominios (CORS). Si la consulta falla, se usa el pronóstico de respaldo incluido y la cabecera lo indica en rojo.
- **Excel local:** el archivo que se carga en la pestaña *Datos* se procesa en el navegador; no se envía a ningún servidor ni queda guardado.

## Criterios de depuración

- Material flotante = manual + mecanizado; macrófitas = manual + mecanizado; total = ambos (m³).
- Calendario continuo desde el 3-jul-2019. Un día sin reporte significa que no se extrajo: cuenta como 0 m³ y se conserva en el análisis.
- Avances diarios vacíos se rellenan con la diferencia de acumulados; se valida acumulado vs suma de avances en cada fila.
- Rachas de 7 o más días sin extracción ("sin operación") y de 10 o más sin mecanizado ("mecanizado detenido") se excluyen solo como objetivo al ajustar el modelo.
- Sitio Presa faltante se estima como 1,049·Olaya + 30 (r = 0,998).

## Modelo (v2.3)

```
nivel_P = a8(h)·L8 + (1−a8(h))·LT                         (persistencia, 8 semanas)
nivel_E = (1−s)·[a(h)·EW + (1−a(h))·LT] + s·LT            (EW: media exponencial, vida media 6 semanas)
f(h)    = [w·nivel_P + (1−w)·nivel_E] · clip(√exp(b0 + Σ βl·x(h−l)), 0,7, 1,5)
          flotante: w = 0, s = 0,25   ·   macrófitas: w = 0,5, s = 0,5
P50 = f            E = (f+50)·r̄(h) − 50
```

Valor esperado con paros = E × (media de todas las semanas / media de semanas con operación, últimas 104 semanas).

Se comparó contra modelos solo de extracción y modelos con caudal (ver [AUDITORIA.md](AUDITORIA.md)): la base son los registros de extracción y el caudal entra como ajuste acotado; con la raíz y el límite 0,7–1,5 reduce el error en ambos componentes (v2.3). L8 = mediana de las últimas 8 semanas con operación; LT = mediana desde jul-2020; x = exceso semanal de caudal Sitio Presa sobre el umbral; k = peso de persistencia elegido con el error de las últimas 52 semanas. Parámetros en [`modelo/params_v21.json`](modelo/params_v21.json); implementación de referencia en Python en [`modelo/modelo_flotante.py`](modelo/modelo_flotante.py), que incluye un router opcional para FastAPI (`/api/flotante/pronostico`) para integrarlo en el backend de HydroForecast.

## Actualizar

- **Datos de extracción (para todos):** en GitHub, abra la carpeta `datos/`, use *Add file › Upload files* y suba el Excel nuevo con el nombre exacto `DatosExtraccion.xlsx` (reemplaza al anterior). Una tarea automática lo convierte en los datos de la app; en 2–3 minutos queda publicado.
- **Prueba rápida (solo para usted):** en la pestaña *Datos* cargue el Excel; se procesa en el navegador y no se guarda.
- **Caudal:** automático. La página consulta HydroForecast al abrir. El GitHub Action `archivar-hydroforecast` guarda cuatro veces al día el pronóstico y el caudal observado en `datos/hf/`; si la API no responde, la página usa ese archivo.
- **Modelo:** recalibrar cada trimestre con `modelo/modelo_flotante.py`.

## Archivos

```
index.html, app.js              aplicación (estructura y lógica)
datos/app/                      datos que lee la app (base.json, extra.json)
datos/DatosExtraccion.xlsx      Excel de extracción (fechas corregidas el 1-nov-2026)
datos/hf/                       archivo del pronóstico y caudal de HydroForecast
datos/satelite/                 series, visor, corredor y alertas satelitales
datos/produccion/               operación diaria derivada de la hoja de viajes
.github/workflows/              tareas: archivar-hydroforecast, datos, satelite (mensual), corredor (diario), lluvia (semanal)
satelite/                       procesamiento satelital (Planetary Computer)
produccion/                     scripts de la hoja de viajes (el Excel fuente no se publica)
scripts/                        excel_a_json.py y build_v3.py
vendor/                         Chart.js 4.4.1, SheetJS 0.18.5, Leaflet 1.9.4
modelo/modelo_flotante.py       depuración + pronóstico + router FastAPI
modelo/params_v21.json          parámetros, cuantiles y métricas del backtest
datos/extraccion_caudal_depurado.csv   serie diaria depurada con caudales y régimen
AUDITORIA.md                    informe de auditoría
```
