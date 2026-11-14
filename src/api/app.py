"""Servidor del sistema: conecta la página con el modelo.

Arranque en local, desde la raíz del repositorio:
    uvicorn src.api.app:app --reload

Rutas:
    GET  /                       la página (index.html, css/ y js/)
    GET  /api/salud              estado del servidor y del modelo
    POST /api/predecir           {"county_fips": "48201", "anio_base": 2024} -> resultado de predecir()
    GET  /api/direccion?q=...    dirección de EE. UU. -> condado (geocodificador del Censo)
    GET  /api/condados           lista de condados para el selector de estado y condado
    GET  /api/historial/{fips}   historial por año y KPIs del condado (?anios=10 o 20)
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.models.predict import cargar_artefactos, predecir

RAIZ = Path(__file__).resolve().parents[2]
GEOCODIFICADOR = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
ESPERA_GEOCODIFICADOR = 10  # segundos; con texto sin sentido el servicio del Censo puede tardar mucho
ESTADOS_HTTP = {"entrada_invalida": 422, "condado_sin_datos": 404, "direccion_no_encontrada": 404,
                "servicio_no_disponible": 503, "pendiente": 501}


def ultimo_anio() -> int:
    """Último año base con datos completos en la tabla procesada."""
    _, _, tabla = cargar_artefactos()
    return int(tabla.index.get_level_values("year").max())


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    cargar_artefactos()  # el modelo se carga al arrancar, no en la primera consulta
    yield


app = FastAPI(title="Cauce", summary="Riesgo de inundación por condado en EE. UU.", lifespan=ciclo_de_vida)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGENES", "http://localhost:8000,http://127.0.0.1:8000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def respuesta(resultado: dict) -> JSONResponse:
    """Devuelve el resultado con el código HTTP que corresponde a su error, si trae uno."""
    return JSONResponse(resultado, status_code=ESTADOS_HTTP.get(resultado.get("error"), 200))


def error(codigo: str, mensaje: str) -> JSONResponse:
    return respuesta({"error": codigo, "mensaje": mensaje})


@app.get("/api/salud")
def salud() -> dict:
    _, metadatos, _ = cargar_artefactos()
    return {"estado": "ok", "modelo": metadatos["modelo"], "anio_base": ultimo_anio(), "versiones": metadatos["versiones"]}


@app.post("/api/predecir")
def api_predecir(datos: dict = Body(...)) -> JSONResponse:
    entrada = {"county_fips": datos.get("county_fips"), "anio_base": datos.get("anio_base", ultimo_anio())}
    return respuesta(predecir(entrada))


@app.get("/api/direccion")
def api_direccion(q: str = Query("", description="dirección de EE. UU.")) -> JSONResponse:
    direccion = q.strip()
    if not 5 <= len(direccion) <= 200:
        return error("entrada_invalida", "Escribe una dirección de 5 a 200 caracteres.")
    try:
        r = httpx.get(GEOCODIFICADOR, timeout=ESPERA_GEOCODIFICADOR, params={
            "address": direccion, "benchmark": "Public_AR_Current", "vintage": "Current_Current",
            "layers": "Counties", "format": "json"})
        r.raise_for_status()
        coincidencias = r.json()["result"]["addressMatches"]
    except (httpx.HTTPError, KeyError, ValueError):
        return error("servicio_no_disponible",
                     "El servicio de direcciones del Censo no respondió. Prueba de nuevo o elige estado y condado.")
    if not coincidencias:
        return error("direccion_no_encontrada",
                     "No encontramos esa dirección en EE. UU. Revisa que tenga calle, ciudad y estado.")
    mejor = coincidencias[0]
    condado = mejor["geographies"]["Counties"][0]
    return respuesta({
        "county_fips": condado["GEOID"],
        "condado": condado["NAME"],
        "direccion_encontrada": mejor["matchedAddress"],
        "coordenadas": {"lat": mejor["coordinates"]["y"], "lon": mejor["coordinates"]["x"]},
    })


@app.get("/api/condados")
def api_condados() -> JSONResponse:
    try:
        from src.data.historial import listar_condados
    except ImportError:
        return error("pendiente", "La lista de condados todavía no está lista.")
    return JSONResponse(listar_condados())


@app.get("/api/historial/{fips}")
def api_historial(fips: str, anios: int = Query(10)) -> JSONResponse:
    if anios not in (10, 20):
        return error("entrada_invalida", "anios debe ser 10 o 20.")
    try:
        from src.data.historial import historial_condado
    except ImportError:
        return error("pendiente", "El historial por condado todavía no está listo.")
    historial = historial_condado(fips, anios)
    if historial is None:
        return error("condado_sin_datos", "No hay historial de este condado.")
    return JSONResponse(historial)


# La página se sirve desde la misma URL que la API.
app.mount("/css", StaticFiles(directory=RAIZ / "css"), name="css")
app.mount("/js", StaticFiles(directory=RAIZ / "js"), name="js")


@app.get("/", include_in_schema=False)
def pagina() -> FileResponse:
    return FileResponse(RAIZ / "index.html")
