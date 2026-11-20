# Matriz de cumplimiento · Entrega 4

Compara lo que se definió en la **Entrega 2 (Especificación técnica)** con lo que hace la versión liberada del sistema (`v1.0`). Para cada requerimiento dice si se cumplió, qué cambió, cómo y por qué.

Estados: **Cumplido** · **Cumplido con cambio** · **Parcial**.

Las pruebas que respaldan esta tabla están en `tests/` (`python -m pytest -q`: 16 pruebas de la API y 7 de `predecir()`, 23 en total), y los tiempos en `results/tiempos_rnf01.json` (`python scripts/medir_tiempos.py`).

## Requerimientos funcionales

| ID | Qué se definió en la Entrega 2 | Estado | Qué hace la versión final / qué cambió y por qué |
|---|---|---|---|
| RF-01 | Ingreso de datos: dirección de EE. UU. (5 a 200 caracteres) que el geocodificador del Censo convierte en condado, o dos selectores de estado y condado. | Cumplido | Campo de dirección (`GET /api/direccion`) y selector con los 3,141 condados del catálogo del Censo (`GET /api/condados`), con nombres de estado en español. La página manda solo `county_fips`; el servidor completa `anio_base` con el último año de datos (2024), así que el objeto que recibe `predecir()` es el mismo que se definió. |
| RF-02 | Botón «Analizar» que llama a `POST /api/predecir`, muestra los pasos de carga y se desactiva hasta recibir respuesta, sin congelar la página. | Cumplido | La llamada usa `fetch` (asíncrona). Mientras responde, la página muestra los pasos de carga y desactiva los botones de análisis y los ejemplos. |
| RF-03 | Tarjeta con el nivel del año siguiente y su probabilidad, en color, y 4 KPIs: reclamaciones NFIP en 5 años, monto pagado en 5 años (USD), eventos de inundación en 10 años y declaratorias FEMA en 5 años. | Cumplido | Ejemplo real: Harris, TX → «Alto · Para 2025 · 92 % de probabilidad» en rojo, con barras de probabilidad por nivel (Gráfica 1) y los 4 KPIs reales (3,039 reclamaciones; US$ 69.5 millones; 106 eventos; 8 declaratorias). |
| RF-04 | Filtros de periodo (10 o 20 años) y series (reclamaciones, eventos, declaratorias) que actualizan la gráfica 2 y la tabla en 1 s o menos sin llamar al modelo. | Cumplido | Botones 10/20 años y 3 casillas. La gráfica y la tabla «Detalle por año» se redibujan con los datos ya cargados, sin volver a llamar al servidor. Medido en el navegador: 21 a 142 ms por cambio. |
| RF-05 | 3 condados reales de prueba, uno por nivel según el dato real de 2025: Harris, TX (alto); Jefferson, TX (medio); Aransas, TX (bajo). Al pulsarlos se llena el formulario y corre el análisis. | Cumplido con cambio | **Cambió:** Harris, TX (alto), Clark, NV (medio) y Pecos, TX (bajo). **Por qué:** con el modelo final, Jefferson (87 %) y Aransas (67 %) salen «alto», así que la demostración mostraba tres veces el mismo nivel. Se eligieron condados donde el modelo coincide con el dato real de 2025 (Clark: 1 reclamación → medio; Pecos: 0 → bajo). **Cómo:** cada botón llena el selector de estado y condado y ejecuta el análisis completo. Se agregaron 2 ejemplos de casos sin estimación (Hartford, CT y Cancún). |
| RF-06 | Mapa con el contorno del condado (TIGERweb del Censo) y su nombre y estado. | Cumplido | Mapa Leaflet con el contorno oficial en el color del nivel y su nombre. Si se buscó una dirección, también marca el punto encontrado. |
| RF-07 | Lista y gráfica de las 4 variables con mayor importancia, con el valor del condado consultado (Gráfica 3). | Cumplido | «Por qué este resultado»: 4 variables con nombre en español, el valor del condado y una barra con su importancia global en el Random Forest (reclamaciones en 10 años 21 %, en 5 años 17 %, monto pagado en 5 años 11 %, estado 10 %). |
| RF-08 | Orientación sobre seguros según el nivel, enlaces a FloodSmart.gov y a los mapas de FEMA, aviso de que el resultado es automático y orientativo, y formulario para reportar un resultado incorrecto. | Parcial | La orientación, los enlaces y los avisos están completos. El formulario de reporte se abre y confirma, pero **todavía no envía ni guarda el reporte**; la página lo dice así. Guardar los reportes en el servidor queda como trabajo futuro. |
| RF-09 | Si la dirección no se encuentra, está fuera de EE. UU. o el condado no tiene datos, el sistema lo explica y no muestra un nivel de riesgo. | Cumplido con cambio | Mensajes propios para dirección no encontrada, entrada incompleta, condado sin datos y servicio caído, sin mostrar nivel. **Cambió:** «fuera de EE. UU.» y «no encontrada» comparten mensaje, porque el geocodificador del Censo responde igual en los dos casos (sin coincidencias); el texto explica ambos. **Caso nuevo detectado:** en 2022 el Censo cambió los condados de Connecticut por regiones de planeación (ej. 09110); esas direcciones dan «sin datos» y el mensaje indica elegir el condado anterior en la lista. |

## Requerimientos no funcionales

| ID | Meta de la Entrega 2 | Estado | Resultado medido |
|---|---|---|---|
| RNF-01 | Inferencia y actualización visual en 3 s o menos en máquina local (20 consultas, `tiempo_ms`). Filtros en 1 s o menos. | Cumplido (por condado) | 20 consultas de 20 dentro de la meta. Modelo (`tiempo_ms`): mediana 73 ms, máximo 98 ms. Predicción + historial: mediana 130 ms, máximo 541 ms (la primera consulta carga el historial). En el navegador, de clic a resultado: 651 ms. Filtros: 142 ms como máximo. **Aclaración:** la búsqueda por dirección suma el geocodificador del Censo, un servicio externo que tardó de 1.8 a 3.0 s en 5 pruebas; con dirección, el total puede pasar de 3 s. El selector de estado y condado evita ese paso. |
| RNF-02 | Campo vacío, dirección corta, fuera de EE. UU., FIPS inexistente o servidor sin respuesta: advertencia clara sin que la interfaz se rompa ni haya errores en la consola. | Cumplido | Los 5 casos muestran un mensaje y la página sigue funcionando (probado en el navegador y en `tests/test_api.py`, incluido el servicio caído con una respuesta simulada). No hay errores de JavaScript. La consola sí muestra la línea del navegador «Failed to load resource: 404» en los casos sin estimación: es la respuesta esperada de la API, no un fallo. |
| RNF-03 | Lógica del dashboard separada del modelo. | Cumplido | Modelo en `src/models/predict.py`, servidor en `src/api/app.py`, datos del historial en `src/data/historial.py` y página en `index.html` + `js/app.js`. La página solo manda y recibe JSON. |

## Métricas del modelo (Entrega 2, sección 6)

| Métrica | Objetivo mínimo | Resultado en prueba (2020 a 2024) | Estado |
|---|---|---|---|
| F1 macro | mayor que 0.552 (persistencia) | 0.596 | Cumplido |
| Recall de «alto» | mayor que 0.437 | 0.474 | Cumplido |
| Exactitud (secundaria) | se reporta | 0.675 | — |

## Navegación y gráficas

| Elemento de la Entrega 2 | Estado | Detalle |
|---|---|---|
| Gráfica 1: probabilidad por nivel | Cumplido | Barras horizontales por nivel en la tarjeta de resultado. |
| Gráfica 2: historial anual | Cumplido | Barras de eventos NOAA y declaratorias FEMA, línea de reclamaciones NFIP en eje derecho. |
| Gráfica 3: factores | Cumplido | Barras de importancia con el valor del condado. |
| Gráfica 4: matriz de confusión (diagnóstico) | Cumplido | Tarjeta «Diagnóstico del modelo» con la matriz 3 × 3 del conjunto de prueba. |
| Sección de diagnóstico: registro de la inferencia | Cumplido | Tiempo de inferencia, año base, modelo y versiones de Python y scikit-learn. |
| Sección de diagnóstico: tabla de los datos del condado usados por el modelo | Parcial | Se muestran las 4 variables con más peso y el historial por año; no se muestran las 13 variables del modelo en una sola tabla. |

## Alcance y exclusiones (Entrega 2, sección 7)

| Exclusión | Qué pasó |
|---|---|
| 1. Ubicación del dispositivo | Se mantuvo fuera. Se quitó el botón «Usar mi ubicación» del prototipo. Un intento de volver a agregarlo el 19/11 se revirtió: mandaba las coordenadas al buscador de direcciones y siempre respondía «no encontrada». |
| 2. Ajuste por pólizas, vecinos y exportar a PDF | Se mantuvo fuera. |
| 3. Publicar el servidor en internet | La demostración es en máquina local, como se definió. Además quedó lista una imagen Docker (`Dockerfile`, probada: usa 447.6 MiB) para publicarla en Hugging Face Spaces; no se publicó porque Hugging Face bloqueó el registro de la cuenta. |
| 4. Riesgo de una vivienda individual o cotización | Se mantuvo fuera: la página aclara que el resultado es del condado y orientativo. |
