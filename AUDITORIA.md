# Auditoría · Material Flotante Ituango

Fecha: 30 de octubre de 2026 · Modelo v2.1 (30-oct-2026)

Revisión de la integridad del archivo de extracción, la calidad de los caudales, la validez estadística del modelo y el funcionamiento de la plataforma. En la aplicación, la integridad se recalcula con el Excel que se cargue.

## Integridad del archivo de extracción

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Estructura del archivo | 2 hojas, 2614 filas cada una, mismas fechas en ambas, ordenadas y sin duplicados. |
| ✅ Correcto | Acumulados vs avances diarios | Las 4 series cuadran en todas las fechas (0 quiebres) . |
| ✅ Correcto | Valores negativos | Ninguno. |
| ✅ Correcto | Conversión kg → m³ (macrófitas manual) | Constante en 160 kg/m³ en todos los registros. |
| ⚠️ Atención | Avances diarios vacíos | 2 celdas vacías (flotante mecanizado 30-ago-2019; flotante manual 8-sep-2020), rellenadas con la diferencia de acumulados. |
| ✅ Correcto | Días sin reporte | 43 días (todos en jul–ago 2019): se cuentan como 0 m³ por criterio del área y permanecen en el análisis. |
| ⚠️ Atención | Valores extremos | 4 días superan 3 veces el percentil 99 de su serie: flotante manual 11-mar-2020 (448 m³); macrófitas manual 20–22-ene-2022 (1.285, 1.209 y 2.292 m³). El de 28-dic-2019 (748 m³) se corrigió: era el acumulado del mes y se repartió en diciembre. |

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
| ✅ Correcto | Validación de la API | Se descartan filas sin fecha o sin caudal numérico; con menos de 7 días válidos se usa el respaldo. |
| ✅ Correcto | Actualización sin código | La página lee datos/DatosExtraccion.xlsx del repositorio al abrir; un GitHub Action archiva cada día el pronóstico y el caudal observado de HydroForecast. |

## Modelo

| Estado | Punto | Detalle |
|---|---|---|
| ⚠️ Atención | Pérdida de desempeño del material flotante en 2024–2026 (v1) | Frente a la mediana histórica, la v1 fue 12 % mejor en 2022 y 7 % en 2023, pero 2 % peor en 2024, 7 % en 2025 y 12 % en 2026: las últimas 8 semanas pesaban demasiado cuando hay paros frecuentes. Corregida en buena parte con el peso adaptativo; 2026 sigue por debajo de la mediana histórica. |
| ✅ Correcto | Peso adaptativo de la persistencia | El peso de las semanas recientes se elige cada semana entre 0; 0,5 y 1 según el error de las últimas 52 semanas con resultado conocido. Error medio absoluto del material flotante: 835 → 809 m³/sem. |
| ✅ Correcto | La base del modelo son los registros de extracción | En 4.908 pronósticos (2022–2026), combinar persistencia y nivel de largo plazo reduce el error frente a la mediana histórica en 60–90 m³/sem a 1–4 semanas (significativo). Suavizamiento exponencial, estacionalidad y aprendizaje automático no la superan. |
| ✅ Correcto | Caudal en macrófitas | Reduce el error a 1–4 semanas en 38 m³/sem (−4 %, IC95 −74 a −5) incluso con caudal futuro desconocido: la ganancia viene del caudal pasado (lavado tras crecientes). |
| ⚠️ Atención | Caudal en material flotante | Sin ganancia significativa (IC95 incluye 0). Se mantiene porque quitarlo sube el RMSE 1,5 % y hay respaldo físico (11 crecientes con 1,3–1,5× más extracción); se agrega un aviso de creciente como escenario. |
| ⚠️ Atención | Aprendizaje automático con caudal | Un modelo flexible (gradient boosting) con caudal pasado o futuro fue 4–24 % peor que la mediana histórica: con ~300 semanas no hay datos suficientes para relaciones complejas. |
| ⚠️ Atención | Valor del pronóstico de caudal a 5–13 semanas | La ganancia del caudal más allá de 4 semanas solo aparece con el caudal futuro real. Su valor práctico depende de la calidad del pronóstico de HydroForecast, que se medirá con el archivo diario que ahora guarda el repositorio. |
| ✅ Correcto | Intervalos P10–P90 fuera de muestra | Calibrados con 2022–2023 y evaluados en 2024–2026: cubren 76 % (flotante) y 78 % (macrófitas), frente al 80 % nominal. |
| ✅ Correcto | Paros en el valor esperado | El pronóstico se calibra con semanas de operación normal. El valor esperado con paros (factor de las últimas 104 semanas: 0,78 flotante, 0,84 macrófitas) reduce el sesgo de 8 semanas de +3.200 m³ a +350–600 m³. |
| ⚠️ Atención | Fuga de información menor | Umbrales de caudal, factores de día de la semana y forma de a(h) se eligieron con todo el periodo; las métricas son levemente optimistas. |

## ¿Solo extracción o caudal como variable exógena?

| Modelo | Flotante 1–4 sem | Flotante 5–13 | Macrófitas 1–4 | Macrófitas 5–13 |
|---|---|---|---|---|
| Mediana histórica | 861 | 870 | 1.002 | 1.007 |
| Repetir las últimas 8 semanas | 841 | 961 | 969 | 1.082 |
| Suavizamiento exponencial | 844 | 957 | 935 | 1.123 |
| Estacional (misma época) | 895 | 918 | 1.126 | 1.164 |
| Aprendizaje automático, solo extracción | 976 | 1.005 | 1.005 | 1.055 |
| Aprendizaje automático + caudal pasado | 899 | 951 | 1.012 | 1.027 |
| Aprendizaje automático + caudal futuro real | 1.062 | 1.110 | 1.046 | 1.103 |
| Modelo actual sin caudal | 786 | 834 | 942 | 992 |
| Modelo actual + caudal futuro ingenuo | 785 | 842 | 904 | 992 |
| **Modelo actual + caudal futuro real** | 780 | 822 | 903 | 975 |

Error medio absoluto (m³/semana) en 4.908 pronósticos con origen móvil 2022–2026, semanas con operación normal. "Caudal futuro real" es el caudal que efectivamente ocurrió (cota superior); "ingenuo" repite el de la semana de origen. El pronóstico real de HydroForecast queda entre ambos.

## Recomendaciones

1. Reemplazar datos/DatosExtraccion.xlsx en el repositorio cada semana (ideal: cada día); la página lo toma al abrir.
2. Registrar el esfuerzo diario (equipos, horas, cuadrillas) y la causa de los días sin extracción: es la mayor fuente de error.
3. Confirmar el valor de 448 m³ del 11-mar-2020 (flotante manual) y los de 20–22-ene-2022 (macrófitas manual): podrían ser acumulados de varios días, como el de dic-2019.
4. En 3 meses, evaluar el aporte del pronóstico de caudal a 5–13 semanas con el archivo diario de HydroForecast.
5. Recalibrar el modelo cada trimestre con el script de Python del repositorio.
