# Cauce — riesgo de inundación para tu vivienda

**Proyecto:** Sistema de análisis de datos para el riesgo de inundaciones
**Equipo Cauce:** Ríos Astudillo Daniel Eduardo · Itza Santizo Jarett Osiel · Salinas Beatriz Erick · Navarrete Tzuc Jorge
**Materias:** Fundamentos de Inteligencia Artificial · Formulación de Proyectos de Tecnología (UT Cancún)

Página web que estima el riesgo de inundación de la zona donde está una vivienda en Estados Unidos. El usuario escribe su dirección (o elige su estado y condado), el sistema identifica el condado, reúne el historial de tormentas e inundaciones (NOAA Storm Events) y de reclamaciones al seguro nacional de inundación (OpenFEMA, NFIP), y un modelo **Random Forest** clasifica el riesgo como **bajo, medio o alto**. Con el resultado muestra los factores que más pesaron y sugerencias para revisar un seguro contra inundaciones.

## Versión liberada (Entrega 4)

La versión evaluada es la etiqueta **`v1.0`**. El sistema corre en una sola dirección: el servidor FastAPI carga el Random Forest y sirve la página y la API (ver la guía de ejecución más abajo). Todo lo que muestra la página sale del modelo y de los datos reales del condado.

**Qué hace la página:**

- Consulta por dirección de EE. UU. (geocodificador del Censo) o por estado y condado (3,141 condados).
- Nivel de riesgo para el año siguiente con su probabilidad, mapa del condado, los 4 factores que más pesaron y 4 indicadores del condado.
- Historial de 10 o 20 años con eventos de inundación (NOAA), reclamaciones (NFIP) y declaratorias (FEMA), en gráfica y tabla.
- Diagnóstico del modelo: tiempo de la inferencia, versiones y matriz de confusión.
- Sugerencias para revisar un seguro, avisos de transparencia y mensajes claros cuando no se puede estimar.

**Ejemplos de prueba:** Harris, TX (`48201`, alto), Clark, NV (`32003`, medio) y Pecos, TX (`48371`, bajo). Hartford, CT y Cancún muestran los casos sin estimación.

Con el servidor corriendo, estos enlaces abren cada estado: `/#resultado-alto`, `/#resultado-medio`, `/#resultado-bajo`, `/#proteccion`, `/#error-sin-datos`, `/#error-fuera` y `/#error-no-encontrada`. Agregar `?notas` muestra las notas de diseño y `?tema=claro` u `?tema=oscuro` fuerza el tema.

El botón **Notas de diseño** pone sobre cada elemento qué requisito atiende y para qué sirve.

**GitHub Pages** (https://jorgemx546.github.io/riesgo-inundaciones/) solo publica los archivos de la página, sin el servidor del modelo: ahí se ve la interfaz, pero no puede analizar.

## Requisitos funcionales (Entrega 2)

| RF | Requisito |
|---|---|
| RF-01 | Ingreso de datos: dirección de EE. UU. o estado y condado |
| RF-02 | Botón que pide la estimación al modelo sin congelar la página |
| RF-03 | Resultado con su nivel, probabilidad y 4 indicadores del condado |
| RF-04 | Filtros de periodo y series que actualizan la gráfica y la tabla |
| RF-05 | Ejemplos de prueba con condados reales |
| RF-06 | Mapa del condado identificado |
| RF-07 | Factores que más pesaron, con el valor del condado |
| RF-08 | Orientación sobre seguros, avisos de transparencia y reporte de errores |
| RF-09 | Casos sin estimación: dirección no encontrada, fuera de EE. UU. o condado sin datos |

Qué se cumplió y qué cambió respecto a la Entrega 2: [`docs/matriz_cumplimiento.md`](docs/matriz_cumplimiento.md).

## Estructura

```
index.html        pantallas: inicio, estados, resultado, protección, cómo funciona, avisos
css/estilos.css   guía visual: colores, tipografía y componentes (tema claro y oscuro)
js/app.js         llamadas a la API, navegación, resultado, mapa, gráfica, tabla y diálogos
data/raw/         datos originales del docente, sin modificar
data/processed/   tabla lista para el modelo y catálogo de condados (condados.csv)
src/api/          servidor FastAPI: conecta la página con el modelo
src/data/         preparación de los datos, catálogo de condados e historial por condado
src/models/       línea base, entrenamiento e inferencia
tests/            pruebas de la API y de la función predecir()
scripts/          medición de tiempos de respuesta (RNF-01)
docs/             matriz de cumplimiento de la Entrega 4
models/           modelos entrenados y sus metadatos
results/          registro, métricas, gráficas del entrenamiento y tiempos medidos
Dockerfile        imagen para correr el sistema completo con Docker
```

Bibliotecas de la página: [Leaflet](https://leafletjs.com/) para el mapa (teselas de OpenStreetMap) y [Chart.js](https://www.chartjs.org/) para la gráfica, cargadas desde cdnjs.

## Guía rápida de ejecución (Entrega 4)

### Versiones

- **Python 3.13.15**
- Librerías con versión exacta en [`requirements.txt`](requirements.txt): scikit-learn 1.9.1, pandas 3.1.1, numpy 2.5.4, joblib 1.6.0, matplotlib 3.11.2, FastAPI 0.162.7, Uvicorn 0.54.0 y httpx 0.28.1; pytest 9.2.0 para las pruebas.
- El servidor necesita unos 450 MB de memoria, porque carga el Random Forest al arrancar.

### Correrlo con Python

Desde la carpeta del repositorio:

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

(en Linux o macOS: `source venv/bin/activate`)

```bash
pip install -r requirements.txt
```

```bash
uvicorn src.api.app:app --reload
```

Abrir http://127.0.0.1:8000. La página y la API salen de la misma dirección.

### Correrlo con Docker

```bash
docker build -t cauce .
```

```bash
docker run -p 7860:7860 cauce
```

Abrir http://127.0.0.1:7860.

### Variables de entorno

No hacen falta para correrlo. [`.env.example`](.env.example) documenta la única variable opcional, `CORS_ORIGENES`: los dominios que pueden llamar a la API desde otra dirección. Si se usa, se define antes de arrancar (`set CORS_ORIGENES=...` en Windows, `export CORS_ORIGENES=...` en Linux o macOS) o con `docker run -e CORS_ORIGENES=... -p 7860:7860 cauce`.

### Credenciales

El sistema no tiene login ni cuentas: no hay credenciales de prueba.

### Pruebas y tiempos

```bash
python -m pytest -q
```

Corre 23 pruebas: 16 de la API y 7 de `predecir()`. Las de dirección no salen a internet.

```bash
python scripts/medir_tiempos.py
```

Mide 20 consultas y 5 búsquedas por dirección y guarda el resultado en `results/tiempos_rnf01.json`. Medición del 19/11/2026: el modelo responde en 56 a 98 ms y la predicción con el historial en 541 ms como máximo; el geocodificador del Censo, que es un servicio externo, tarda de 1.8 a 3.0 s.

### Rutas de la API

| Ruta | Qué devuelve |
|---|---|
| `GET /api/salud` | Estado del servidor, modelo cargado y versiones |
| `POST /api/predecir` | Nivel de riesgo del año siguiente. Cuerpo: `{"county_fips": "48201", "anio_base": 2024}` (el año es opcional) |
| `GET /api/direccion?q=...` | Condado de una dirección de EE. UU., con el geocodificador del Censo (necesita internet) |
| `GET /api/condados` | Lista de condados para el selector de estado y condado |
| `GET /api/historial/{fips}?anios=10` | Reclamaciones, eventos de inundación y declaratorias por año (10 o 20 años) y los 4 KPIs |

Ejemplos para probar: Harris, TX (`48201`, alto), Clark, NV (`32003`, medio) y Pecos, TX (`48371`, bajo).

El catálogo `data/processed/condados.csv` sale del Gazetteer de condados del Censo de EE. UU. Para volver a generarlo:

```bash
python src/data/generar_condados.py
```

Los 8 condados de Connecticut que el Censo reemplazó por regiones en 2022 se agregan en `src/data/historial.py`, porque los datos del proyecto los traen con sus códigos anteriores. Por la misma razón, una dirección de Connecticut que el Censo ubica en una región nueva no tiene datos para estimar.

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

El resultado es por condado y solo orientativo. No estima el riesgo de una vivienda.

