# Auditoría · Material Flotante Ituango

Fecha: 2026-11-01 · Modelo v2.1 · Generado desde la pestaña Auditoría de la aplicación.

## Integridad de los datos

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Estructura del archivo | 2 hojas, 2614 filas cada una, mismas fechas en ambas, ordenadas y sin duplicados. |
| ✅ Correcto | Acumulados vs avances diarios | Las 4 series cuadran en todas las fechas (0 quiebres) . |
| ✅ Correcto | Valores negativos | Ninguno. |
| ✅ Correcto | Conversión kg → m³ (macrófitas manual) | Constante en 160 kg/m³ en todos los registros. |
| ⚠️ Atención | Avances diarios vacíos | 2 celdas vacías (flotante mecanizado 30-ago-2019; flotante manual 8-sep-2020), rellenadas con la diferencia de acumulados. |
| ✅ Correcto | Días sin reporte | 43 días (todos en jul–ago 2019): se cuentan como 0 m³ por criterio del área y permanecen en el análisis. |
| ⚠️ Atención | Valores extremos | 4 días superan 3 veces el percentil 99 de su serie: flotante manual 11-mar-2020 (448 m³); macrófitas manual 20–22-ene-2022 (1.285, 1.209 y 2.292 m³). El de 28-dic-2019 (748 m³) se corrigió: era el acumulado del mes y se repartió en diciembre. |
| ⚠️ Atención | El volumen es una estimación por viajes | Mecanizado: viajes × capacidad nominal de cada volqueta (14,62–20 m³), y el flotante × 0,56. Manual: viajes de parihuela (80 kg), lancha (480–500 kg) o cosechadora, ÷ 160 kg/m³. La división flotante/macrófitas del mecanizado se estima por composición (en volquetas mixtas 60/40). |
| ⚠️ Atención | Otras inconsistencias de la hoja | El total de viajes de macrófitas mecanizado omite volquetas en 47 filas (259 viajes; el volumen sí las incluye). 23 a 27-may-2024: volúmenes digitados que no coinciden con los viajes, dos de ellos en días de descanso (184,8 m³); se conservan. |
| ⚠️ Atención | Flotante mecanizado 3–9 abr-2026 sin volumen | 310 viajes registrados con la celda de m³ vacía: 0 en la hoja y en DatosExtracción. Con la fórmula de la fila anterior serían 2.578 m³. |
| ✅ Correcto | Fechas de DatosExtracción corregidas (31-oct-2026) | Los valores se movieron a la fecha real de su fila en la hoja de viajes, sin cambiar ningún valor ni los totales (1.613.271 m³): 366 días de flotante manual y 564 de macrófitas manual (1 día, desde nov-2024), 126 de flotante mecanizado (1 día, desde may-2026) y 371 de macrófitas mecanizado (1 a 3 días, dic-2022–jun-2023 y ene–oct-2026). Comprobación: las jornadas de elecciones del 31-may y 21-jun-2026 quedan sin extracción, como dicen las observaciones. La copia anterior quedó en el historial del repositorio. |
| ⚠️ Atención | Valores repetidos u omitidos que siguen en DatosExtracción | No se cambiaron valores. Pendientes de decisión: 30-nov-2022 contado dos veces en macrófitas mecanizado (204 m³; la fila duplicada tiene los mismos viajes y observación); 27-oct y 4-nov-2024 en lo manual repiten el día siguiente (flotante 14 y 15 m³, macrófitas 192 y 218) en vez de lo registrado (8, 4, 130 y 172,5); faltan 30-jun-2023 (85 m³) y 9-oct-2026 (20,4 m³) de macrófitas mecanizado y 8-nov-2024 (9 y 120 m³); 20-ene-2024: 67,53 m³ de flotante manual frente a 6,15 en la hoja. |

## Caudales y HydroForecast

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Cobertura de caudal | Olaya, La Pintada y nivel con datos el 100 % de los días del registro. |
| ⚠️ Atención | Sitio Presa incompleto | Falta en 881 días (33 %); se estima como 1,049·Olaya + 30 (r = 0,998, error medio 2,4 %). Error aceptable para un exceso semanal. |
| ✅ Correcto | Caudal en vivo | La API pública de HydroForecast (Hugging Face) responde con CORS abierto: la plataforma toma el pronóstico de 90 días y el caudal observado al abrirse, con respaldo embebido si no hay conexión. |
| ⚠️ Atención | Afluentes y lluvia en HydroForecast | HydroForecast no mide caudal de los ríos San Andrés, Ituango ni Espíritu Santo. Tiene pluviómetros (la API guarda 14 días), Cauca aguas arriba en La Virginia y Bolombolo (30 días) y lluvia pronosticada (WRF, GEFS, AIFS). Los totales anuales DHIME 2005–2025 cubren ~144 días/año y La Pintada y Olaya tienen valores idénticos (posible error de datos). Desde el 30-oct estas series se archivan a diario en el repositorio. |
| ✅ Correcto | Lluvia histórica como variable exógena | Se probaron cuatro series de lluvia diaria 2019–2026 y ninguna mejoró el pronóstico. CHIRPS v2.0 completo (ClimateSERV, 2019–sep 2026), zona de la cola: flotante +23 (1–4 sem) y +22 m³/sem (5–13 sem), ambos significativos; macrófitas +15 y +24. IMERG (ClimateSERV, hasta may-2024): flotante +29 y +26; macrófitas +15 y +13. NASA POWER: flotante +4 a +13; macrófitas +17 a +41. Sumar lluvia al caudal no supera al caudal solo. El caudal de Sitio Presa ya integra la lluvia de la cuenca. |
| ✅ Correcto | Pronóstico real de HydroForecast | Con los 20 pronósticos de 90 días de los últimos 60 días: el pronóstico empata con repetir el caudal actual en las semanas 1–2 y lo supera desde la semana 3 (error 136–175 m³/s frente a 205–393 m³/s), con sesgo de −100 a −170 m³/s en temporada de subida. El pronóstico de extracción no cambió con pronóstico real frente a caudal observado (0 de 84 casos), porque el caudal no superó los umbrales. Panel en vivo en Modelo y desempeño. |

## Modelo y satélite

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
| ✅ Correcto | Cobertura satelital con tres sensores | Sentinel-2 (106 escenas), Landsat 8/9 (103; frente a Sentinel-2 ρ = 0,82, sesgo −0,6 ha) y radar Sentinel-1 corregido por terreno (351; con la línea de la barrera ρ = 0,80 en total y 0,64 aguas arriba). Cubren los 94 meses desde 2019. Ni la serie de Sentinel-2 ni la combinada mejoran el pronóstico de extracción (−2 a +4 m³/sem, no significativo). |
| ✅ Correcto | Corrección sobre Sentinel-1 | Una revisión anterior atribuyó el fallo de Sentinel-1 a la falta de una clave de suscripción. La causa real era la configuración del lector (solo aceptaba archivos .tif); corregida, las escenas se leen sin cuenta. |
| ✅ Correcto | Validación del satélite frente a la extracción | Revisión visual de 15 escenas en color real: las masas verdes aparecen en el lado que reporta cada serie. Aguas arriba de la barrera el área sigue a la extracción de macrófitas (ρ = +0,28 y +0,25 con las 2 semanas previas y siguientes, sin estacionalidad, 192 escenas); aguas abajo, donde crecen en el agua quieta del embalse, la relación es inversa (ρ = −0,22). El total mezcla ambos efectos. Madera y residuos no son visibles. |
| ✅ Correcto | Área por margen del cauce | Con el sitio de extracción confirmado (margen derecha, oriental) se separó la zona por el eje del cauce. Desde 2024 esa margen concentra 57–79 % del material, pero ninguna subzona anticipa la extracción mejor que la extracción reciente (correlación parcial ≤ 0,08). El satélite sigue como indicador de estado. |
| ✅ Correcto | Barrera ubicada en la imagen | El punto informado (6,90056; −75,83540) cae en la orilla occidental. En la frecuencia de vegetación de Sentinel-2 hay un borde recto y persistente a la salida del estrecho (2022–2023): la barrera va de 6,90217; −75,83497 a 6,90199; −75,83279 (unos 240 m, ±20 m), ~180 m al noreste del punto. Aguas arriba y abajo se separan ahora por esa línea. |
| ✅ Correcto | Radar Sentinel-1 con la barrera corregida | 351 escenas hasta el 30-oct-2026. Frente a Sentinel-2 en 70 fechas (±2 días): total ρ 0,80 y error 10 ha; aguas abajo 0,76; aguas arriba 0,64 (antes 0,43 con el punto sobre tierra), por eso ahora se muestra por lado. Un clasificador de VV, VH y textura entrenado con Sentinel-2 fue peor dejando un año fuera (ρ 0,58). |
| ✅ Correcto | Alternativas de pronóstico probadas | Con las fechas corregidas: pronosticar el total directamente o como tasa por día operado × días esperados no mejora (−4 a −22 m³/sem, IC95 incluye 0). Conocer el descanso programado: −15 % (semanas 1–4) y −16 % (5–13). |
| ✅ Correcto | Corredor del río: 30 km aguas arriba | Sentinel-2 a 20 m en 8 tramos, de 30 km aguas arriba a 15 km aguas abajo de la barrera (mosaicos 18NTN, 18NUN y 18NVN; 587 fechas, 310 con algún tramo despejado). Se actualiza a diario con las imágenes nuevas. Ningún tramo mejora el pronóstico al usarlo (+9 a +179 m³/sem); se muestra como seguimiento. |

## Plataforma

| Estado | Punto | Detalle |
|---|---|---|
| ✅ Correcto | Equivalencia Python ↔ navegador | Las 16 semanas pronosticadas coinciden entre el módulo de Python y la página: diferencia máxima 0,05 % (redondeo). |
| ✅ Correcto | Pruebas de interfaz | 8 pestañas sin errores en tema oscuro y claro, carga del Excel verificada y sin desplazamiento horizontal en móvil (390 px). |
| ✅ Correcto | Validación de la API | Se descartan filas sin fecha o sin caudal numérico; con menos de 7 días válidos se usa el respaldo. |
| ✅ Correcto | Actualización sin código | La página lee datos/DatosExtraccion.xlsx del repositorio al abrir; un GitHub Action archiva cada día el pronóstico y el caudal observado de HydroForecast. |
| ✅ Correcto | Instalable y con respaldo sin conexión | Se puede instalar como aplicación en celular o PC. Sin red muestra la última versión consultada; con red siempre trae los datos actuales. |
| ✅ Correcto | Carga del Excel | Si el Excel del repositorio es el mismo que trae la página (comparación SHA-256), no se vuelve a procesar: se evita descargar el lector de Excel (311 kB) y se ahorra entre 0,3 y 0,9 s de procesamiento al abrir. |
| ✅ Correcto | Exportar e imprimir | El pronóstico semanal se descarga en CSV (separador «;», abre directo en Excel) y la página tiene formato de impresión para guardar como PDF. |

## Vigencia

| Estado | Punto | Detalle |
|---|---|---|
| ⚠️ Atención | Vigencia de los datos | La pestaña Pronóstico muestra a diario cuántos días tiene el último reporte; conviene subir el Excel cada semana. |

## Experimento: qué variables mejoran el pronóstico (MAE m³/semana, origen móvil 2022–2026)

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
| Modelo actual + caudal futuro real | 780 | 822 | 903 | 975 |
| Modelo actual + lluvia (NASA POWER, climatología futura) | 797 | 837 | 960 | 1.009 |
| Modelo actual + lluvia (CHIRPS completo, cola) | 808 | 856 | 956 | 1.016 |
| Modelo actual + lluvia (IMERG, cola, hasta 2024) | 815 | 859 | 956 | 1.005 |
| Modelo actual + caudal + cobertura satelital | 780 | 822 | 910 | 981 |

Error medio absoluto (m³/semana) en 4.908 pronósticos con origen móvil 2022–2026, semanas con operación normal. "Caudal futuro real" es el caudal que efectivamente ocurrió (cota superior); "ingenuo" repite el de la semana de origen. El pronóstico real de HydroForecast queda entre ambos. Las filas de lluvia y satélite se recalibraron cada 13 semanas solo con datos anteriores a cada origen.

## Recomendaciones

- Reemplazar datos/DatosExtraccion.xlsx en el repositorio cada semana (ideal: cada día); la página lo toma al abrir.
- Registrar el esfuerzo diario (equipos, horas, cuadrillas) y la causa de los días sin extracción: es la mayor fuente de error.
- Confirmar el valor de 448 m³ del 11-mar-2020 (flotante manual) y los de 20–22-ene-2022 (macrófitas manual): podrían ser acumulados de varios días, como el de dic-2019.
- Recalibrar el modelo cada trimestre con el script de Python del repositorio.
- En 3 meses, evaluar con el archivo diario el aporte del pronóstico de caudal (5–13 semanas), de la lluvia de los pluviómetros y del Cauca aguas arriba.
- Para medir madera y residuos (no visibles con Sentinel-2, Landsat ni radar en agua turbia), considerar imágenes de mayor resolución (PlanetScope 3 m) o vuelos con dron sobre la barrera.
- Registrar la causa de cada día sin extracción con una lista fija (descanso, labores operativas, sin material en el puerto, caudal, externa) y compartir el plan semanal de descansos de EPM: con él el error del pronóstico total baja 15–16 %.
- Medir el volumen real de algunas cargas y separar la composición por viaje: hoy el volumen y la división flotante/macrófitas son estimaciones.
- Armar el informe integrado por fecha (BUSCARV/XLOOKUP sobre la fecha) y no por posición de fila: así se originaron los desfases de 1 a 3 días.
