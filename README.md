# Cauce — riesgo de inundación para tu vivienda

**Proyecto:** Sistema de análisis de datos para el riesgo de inundaciones
**Equipo Cauce:** Ríos Astudillo Daniel Eduardo · Itza Santizo Jarett Osiel · Salinas Beatriz Erick · Navarrete Tzuc Jorge
**Materias:** Fundamentos de Inteligencia Artificial · Formulación de Proyectos de Tecnología (UT Cancún)

Página web que estima el riesgo de inundación de la zona donde está una vivienda en Estados Unidos. El usuario escribe su dirección (o comparte su ubicación con permiso), el sistema identifica el condado, reúne el historial de tormentas e inundaciones (NOAA Storm Events) y de reclamaciones al seguro nacional de inundación (OpenFEMA, NFIP), y un modelo **Random Forest** clasifica el riesgo como **bajo, medio o alto**. Con el resultado muestra los factores que más pesaron y sugerencias para revisar un seguro contra inundaciones.

## Prototipo (Entrega 1)

**Ver en línea:** https://jorgemx546.github.io/riesgo-inundaciones/

> Los resultados del prototipo son **simulados**. El modelo ya está entrenado (Entrega 3), pero todavía no está conectado a la página. Lo único real en los ejemplos son los condados, sus códigos FIPS, sus coordenadas y el contorno del mapa (servicio TIGERweb del Censo de EE. UU.).

Enlaces directos a cada pantalla y estado:

| Pantalla o estado | Enlace |
|---|---|
| Inicio | [index.html](https://jorgemx546.github.io/riesgo-inundaciones/) |
| Resultado: riesgo alto (Houston, TX) | [#resultado-alto](https://jorgemx546.github.io/riesgo-inundaciones/#resultado-alto) |
| Resultado: riesgo medio (Davenport, IA) | [#resultado-medio](https://jorgemx546.github.io/riesgo-inundaciones/#resultado-medio) |
| Resultado: riesgo bajo (Phoenix, AZ) | [#resultado-bajo](https://jorgemx546.github.io/riesgo-inundaciones/#resultado-bajo) |
| Sugerencias de protección | [#proteccion](https://jorgemx546.github.io/riesgo-inundaciones/#proteccion) |
| Estado de carga | [#cargando](https://jorgemx546.github.io/riesgo-inundaciones/#cargando) |
| Error: pocos datos para estimar | [#error-sin-datos](https://jorgemx546.github.io/riesgo-inundaciones/#error-sin-datos) |
| Error: fuera de EE. UU. | [#error-fuera](https://jorgemx546.github.io/riesgo-inundaciones/#error-fuera) |
| Error: dirección no encontrada | [#error-no-encontrada](https://jorgemx546.github.io/riesgo-inundaciones/#error-no-encontrada) |
| Con notas de diseño (requisito de cada elemento) | [?notas](https://jorgemx546.github.io/riesgo-inundaciones/?notas#resultado-alto) |

Agregar `?tema=claro` u `?tema=oscuro` fuerza el tema de color.

## Requisitos funcionales que cubre

| RF | Requisito |
|---|---|
| RF-01 | Escribir la dirección de la vivienda |
| RF-02 | Usar la ubicación del dispositivo, con permiso |
| RF-03 | Identificar y mostrar el condado analizado |
| RF-04 | Mostrar el nivel de riesgo estimado y la confianza del modelo |
| RF-05 | Explicar qué factores pesaron en el resultado |
| RF-06 | Mostrar el historial de eventos y reclamaciones de la zona |
| RF-07 | Dar sugerencias para revisar un seguro según el nivel |
| RF-08 | Avisar que el sistema es automático, cómo se usa la ubicación y cómo reportar errores |
| RF-09 | Avisar cuando no se puede analizar: dirección no encontrada, fuera de EE. UU. o pocos datos |

El botón **Notas de diseño** muestra sobre cada elemento qué requisito atiende y para qué sirve.

## Estructura

```
index.html        pantallas: inicio, estados, resultado, protección, cómo funciona, avisos
css/estilos.css   guía visual: colores, tipografía y componentes (tema claro y oscuro)
js/datos.js       datos simulados de las zonas de ejemplo
js/app.js         navegación, estados de carga y error, mapa, gráfica y diálogos
data/raw/         datos originales del docente, sin modificar
data/processed/   tabla lista para el modelo
src/data/         preparación de los datos
src/models/       línea base, entrenamiento e inferencia
tests/            pruebas de la función predecir()
models/           modelos entrenados y sus metadatos
results/          registro, métricas y gráficas del entrenamiento
```

Bibliotecas: [Leaflet](https://leafletjs.com/) para el mapa (teselas de OpenStreetMap) y [Chart.js](https://www.chartjs.org/) para la gráfica, cargadas desde cdnjs.

## Verlo en tu computadora

Abrir `index.html` en el navegador funciona, pero el mapa necesita un servidor local:

```bash
python -m http.server 8000
```

y entrar a http://localhost:8000.

## Datos (Entrega 2)

`data/raw/` tiene el dataset que entregó el docente, **US Climate Disaster & Flood Insurance Risk** (versión del 21/08/2026), tal como venía. Junta por condado y año las reclamaciones del NFIP (OpenFEMA), los eventos de NOAA Storm Events y las declaratorias de desastre de FEMA, de 2000 a 2026. La tabla principal es `county_year_climate_flood_risk.csv`: 83,804 filas y 26 columnas. Las fuentes, sus fechas y sus hashes están en `source_manifest.json`.

`data/processed/county_year_model.csv` es la tabla para el modelo: 81,775 filas y 17 columnas, una por condado y año base (2000 a 2024), con variables de 1, 5 y 10 años y el nivel de riesgo del año siguiente:

| Nivel | Reclamaciones al NFIP el año siguiente |
|---|---|
| bajo | 0 |
| medio | de 1 a 9 |
| alto | 10 o más |

Al prepararla se quitan los códigos de nivel estado y de territorios, se deja fuera 2026 (incompleto), el estado se toma del FIPS (la columna `state` mezcla abreviaturas y nombres) y los años sin registro se rellenan con 0.

Para volver a generarla y calcular la línea base (Python con pandas y scikit-learn):

```bash
python src/data/preprocess.py --raw data/raw --output data/processed/county_year_model.csv
```

```bash
python src/models/baseline.py --data data/processed/county_year_model.csv
```

Línea base en el conjunto de prueba (años base 2020 a 2024): siempre «bajo» da F1 macro 0.268; la regla de persistencia (el año siguiente queda en el mismo nivel) da F1 macro 0.552. El modelo tiene que superar 0.552.

## Modelo (Entrega 3)

Instalar las dependencias y repetir el entrenamiento completo (unos 8 minutos en una computadora de 4 núcleos):

```bash
pip install -r requirements.txt
```

```bash
python src/models/train.py --data data/processed/county_year_model.csv --output models/
```

Los modelos entrenan con los años base 2000 a 2019 y se prueban con 2020 a 2024. Los hiperparámetros se eligen con validación por bloques de años dentro del entrenamiento.

| Modelo | F1 macro (validación) | F1 macro (prueba) | Recall de «alto» (prueba) | Exactitud (prueba) |
|---|---|---|---|---|
| Persistencia (línea base) | | 0.552 | 0.437 | 0.680 |
| Regresión logística ajustada | 0.532 | 0.566 | 0.670 | 0.638 |
| Árbol de decisión ajustado | 0.545 | 0.532 | 0.693 | 0.586 |
| **Random Forest ajustado** | **0.584** | **0.596** | 0.474 | 0.675 |

Ganó el Random Forest. Supera a la línea base, pero sigue sobreajustado: su F1 macro es 0.853 en entrenamiento y 0.596 en prueba. Los experimentos completos están en [`results/experimentos.csv`](results/experimentos.csv) y el registro de la corrida en [`results/entrenamiento.log`](results/entrenamiento.log).

Para consultar un condado:

```bash
python src/models/predict.py --fips 48201 --anio 2024
```

Desde Python, en la raíz del repositorio:

```python
from src.models.predict import predecir

predecir({"county_fips": "48201", "anio_base": 2024})
```

Para correr las pruebas:

```bash
python -m unittest discover -s tests -v
```

El resultado es por condado y solo orientativo. No estima el riesgo de una vivienda.
