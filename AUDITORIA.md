# Auditoría · Material Flotante Ituango

Fecha: 30 de octubre de 2026 · Modelo v2.0 (30-oct-2026)

Revisión de la integridad del archivo de extracción, la calidad de los caudales, la validez estadística del modelo y el funcionamiento de la plataforma.

## Integridad del archivo de extracción

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Estructura del archivo | 2 hojas, 2614 filas cada una, mismas fechas en ambas, ordenadas y sin duplicados. |
| ✅ Correcto | Acumulados vs avances diarios | Las 4 series cuadran en todas las fechas (0 quiebres) tras la corrección del 30-oct. |
| ✅ Correcto | Valores negativos | Ninguno. |
| ✅ Correcto | Conversión kg → m³ (macrófitas manual) | Constante en 160 kg/m³ en todos los registros. |
| ⚠️ Atención | Avances diarios vacíos | 2 celdas vacías (flotante mecanizado 30-ago-2019; flotante manual 8-sep-2020), rellenadas con la diferencia de acumulados. |
| ✅ Correcto | Días sin reporte | 43 días (todos en jul–ago 2019): se cuentan como 0 m³ por criterio del área y permanecen en el análisis. |
| ⚠️ Atención | Valores extremos | 5 días superan 3 veces el percentil 99 de su serie: flotante manual 28-dic-2019 (748 m³) y 11-mar-2020 (448 m³); macrófitas manual 20–22-ene-2022 (1.285, 1.209 y 2.292 m³). Son plausibles (jornadas de limpieza masiva) pero conviene confirmarlos; no se excluyen. |

## Caudales e integración con HydroForecast

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Cobertura de caudal | Olaya, La Pintada y nivel con datos el 100 % de los días del registro. |
| ⚠️ Atención | Sitio Presa incompleto | Falta en 881 días (33 %); se estima como 1,049·Olaya + 30 (r = 0,998, error medio 2,4 %). Error aceptable para un exceso semanal. |
| ✅ Correcto | Caudal en vivo | La API pública de HydroForecast (Hugging Face) responde con CORS abierto: la plataforma toma el pronóstico de 90 días y el caudal observado al abrirse, con respaldo embebido si no hay conexión. |

## Plataforma

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Equivalencia Python ↔ navegador | Las 16 semanas pronosticadas coinciden entre el módulo de Python y la página: diferencia máxima 0,05 % (redondeo). |
| ✅ Correcto | Pruebas de interfaz | 8 pestañas sin errores en tema oscuro y claro, carga del Excel verificada y sin desplazamiento horizontal en móvil (390 px). |

## Modelo

| Estado | Punto | Detalle |
|---|---|---|
| ⚠️ Atención | Pérdida de desempeño del material flotante en 2024–2026 (v1) | Frente a la mediana histórica, el modelo v1 fue 12 % mejor en 2022 y 7 % en 2023, pero 2 % peor en 2024, 7 % en 2025 y 12 % en 2026: las últimas 8 semanas pesaban demasiado cuando hay paros frecuentes. Corregida en buena parte con la v2; 2026 sigue por debajo de la mediana histórica. |
| ✅ Correcto | Corrección v2: peso adaptativo | El peso de las semanas recientes se elige cada semana entre 0; 0,5 y 1 según el error de las últimas 52 semanas con resultado conocido (sin mirar el futuro). Error medio absoluto: material flotante 835 → 809 m³/sem; 2026 pasa de −12 % a −8 % frente a la mediana histórica (−2 % antes de calibrar la mediana). |
| ⚠️ Atención | Aporte del caudal al material flotante | Débil y decreciente: la suma de coeficientes del exceso de caudal bajó de 0,24 (2020–2023) a 0,10 (2023–2026), y entre 2024 y 2026 hubo una sola creciente > 2.100 m³/s. Se mantiene porque los 11 eventos históricos muestran 1,3–1,5× más extracción después de crecientes. |
| ✅ Correcto | Aporte del caudal a macrófitas | Consistente: reduce el error de 1.303 a 1.276 m³/sem en el periodo completo y el efecto es estable (lavado tras crecientes). |
| ✅ Correcto | Mejora significativa (semanas 1–4) | Bootstrap por bloques: probabilidad de no mejorar frente a la mediana histórica = 0,03 (flotante) y 0,02 (macrófitas). |
| ⚠️ Atención | Sesgo del valor puntual | El valor puntual v1 subestimaba 235 m³/sem en flotante porque los volúmenes semanales tienen cola larga. v2 muestra la mediana calibrada (P50) y el valor esperado; el valor esperado reproduce el 98–99 % del volumen observado. |
| ✅ Correcto | Intervalos P10–P90 fuera de muestra | Calibrados con 2022–2023 y evaluados en 2024–2026: cubren 76 % (flotante) y 78 % (macrófitas), frente al 80 % nominal. |
| ⚠️ Atención | Fuga de información menor | Umbrales de caudal, factores de día de la semana y forma de a(h) se eligieron con todo el periodo. El efecto es pequeño (la cobertura fuera de muestra es 76–78 %), pero las métricas publicadas son levemente optimistas. |

## Vigencia

| Estado | Punto | Detalle |
|---|---|---|
| ⛔ Crítico | Datos de extracción desactualizados | Último reporte: 2026-10-10 (hace 20 días). Las primeras semanas del pronóstico ya transcurrieron sin datos observados. Cargar el Excel cada semana. |

## Modelo v1 vs v2 (RMSE semanal, backtest 2022–2026, m³)

| Componente | Mediana histórica | Persistencia | v1 | v2 |
|---|---|---|---|---|
| Material flotante | 1.125 | 1.174 | 1.076 | 1.034 |
| Macrófitas | 1.333 | 1.366 | 1.254 | 1.276 |

Mejora frente a la mediana histórica por año (positivo = mejor):

| Año | Flotante v1 | Flotante v2 | Macrófitas v1 | Macrófitas v2 |
|---|---|---|---|---|
| 2022 | +12,2 % | +16,4 % | +5,5 % | +1,1 % |
| 2023 | +7,0 % | +11,2 % | +8,2 % | +5,6 % |
| 2024 | -2,0 % | -1,2 % | +6,1 % | +7,1 % |
| 2025 | -7,4 % | -1,6 % | +6,1 % | +4,8 % |
| 2026 | -11,9 % | -8,3 % | +2,9 % | +3,9 % |

## Recomendaciones

1. Actualizar el Excel de extracción cada semana (ideal: cada día) para que el pronóstico parta de datos recientes.
2. Registrar el esfuerzo diario (equipos, horas, cuadrillas) y la causa de los días sin extracción: es la mayor fuente de error.
3. Confirmar los 5 valores extremos (dic-2019, mar-2020, ene-2022).
4. Recalibrar el modelo cada trimestre con el script de Python del repositorio (recalcula k, intervalos y métricas).
5. Incorporar inventario observado en la cola (dron o satélite) para pasar de pronosticar extracción a pronosticar llegada de material.
