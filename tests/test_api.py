"""Pruebas de la API (src/api/app.py). Uso: python -m pytest -q

Las pruebas de dirección no salen a internet: reemplazan la llamada al
geocodificador del Censo por respuestas fijas.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

import src.api.app as api
from src.api.app import app

client = TestClient(app)


def test_salud():
    r = client.get("/api/salud")
    assert r.status_code == 200
    datos = r.json()
    assert datos["estado"] == "ok"
    assert datos["modelo"] == "modelo_rf.joblib"
    assert datos["anio_base"] == 2024


@pytest.mark.parametrize("fips, nivel", [("48201", "alto"), ("32003", "medio"), ("48371", "bajo")])
def test_predecir_niveles(fips, nivel):
    """Los 3 ejemplos de la página (RF-05) dan el nivel que muestran."""
    r = client.post("/api/predecir", json={"county_fips": fips})
    assert r.status_code == 200
    datos = r.json()
    assert datos["prediccion"] == nivel
    assert datos["anio_pronostico"] == 2025
    assert datos["confianza_o_score"] == datos["probabilidades"][nivel]
    assert abs(sum(datos["probabilidades"].values()) - 1) <= 0.02
    assert len(datos["factores"]) == 4
    assert datos["tiempo_ms"] < 3000  # RNF-01


def test_predecir_fips_invalido_e_inexistente():
    r_inv = client.post("/api/predecir", json={"county_fips": "abc"})
    assert r_inv.status_code == 422
    assert r_inv.json()["error"] == "entrada_invalida"

    r_no_existe = client.post("/api/predecir", json={"county_fips": "09110"})
    assert r_no_existe.status_code == 404
    assert r_no_existe.json()["error"] == "condado_sin_datos"
    assert "prediccion" not in r_no_existe.json()  # RF-09: sin nivel de riesgo


@pytest.mark.parametrize("anios", [10, 20])
def test_historial_anios(anios):
    r = client.get("/api/historial/48201", params={"anios": anios})
    assert r.status_code == 200
    datos = r.json()
    assert datos["condado"] == "Harris County"
    assert datos["anios"][-1] == 2024
    for serie in ("anios", "reclamaciones", "eventos_inundacion", "declaratorias"):
        assert len(datos[serie]) == anios
    assert set(datos["kpis"]) == {"reclamaciones_5y", "monto_pagado_5y_usd", "eventos_inundacion_10y", "declaratorias_5y"}


def test_historial_errores():
    assert client.get("/api/historial/48201", params={"anios": 15}).status_code == 422
    assert client.get("/api/historial/99999").status_code == 404


def test_condados():
    r = client.get("/api/condados")
    assert r.status_code == 200
    condados = r.json()
    assert len(condados) == 3141
    assert all(len(c["county_fips"]) == 5 for c in condados)
    assert {"county_fips": "48201", "condado": "Harris County", "estado": "TX"} in condados


class RespuestaCenso:
    """Imita la respuesta del geocodificador del Censo."""

    def __init__(self, coincidencias):
        self.coincidencias = coincidencias

    def raise_for_status(self):
        pass

    def json(self):
        return {"result": {"addressMatches": self.coincidencias}}


HOUSTON = {
    "matchedAddress": "1001 PRESTON ST, HOUSTON, TX, 77002",
    "coordinates": {"x": -95.3612, "y": 29.7615},
    "geographies": {"Counties": [{"GEOID": "48201", "NAME": "Harris County"}]},
}


def test_direccion_encontrada(monkeypatch):
    monkeypatch.setattr(api.httpx, "get", lambda *a, **k: RespuestaCenso([HOUSTON]))
    r = client.get("/api/direccion", params={"q": "1001 Preston St, Houston, TX 77002"})
    assert r.status_code == 200
    assert r.json()["county_fips"] == "48201"
    assert r.json()["coordenadas"] == {"lat": 29.7615, "lon": -95.3612}


def test_direccion_no_encontrada(monkeypatch):
    monkeypatch.setattr(api.httpx, "get", lambda *a, **k: RespuestaCenso([]))
    r = client.get("/api/direccion", params={"q": "Av. Tulum 100, Cancún, México"})
    assert r.status_code == 404
    assert r.json()["error"] == "direccion_no_encontrada"


def test_direccion_servicio_caido(monkeypatch):
    def falla(*a, **k):
        raise httpx.ConnectTimeout("sin respuesta")

    monkeypatch.setattr(api.httpx, "get", falla)
    r = client.get("/api/direccion", params={"q": "1001 Preston St, Houston, TX"})
    assert r.status_code == 503
    assert r.json()["error"] == "servicio_no_disponible"


@pytest.mark.parametrize("texto", ["", "abc", "x" * 201])
def test_direccion_invalida(texto):
    r = client.get("/api/direccion", params={"q": texto})
    assert r.status_code == 422
    assert r.json()["error"] == "entrada_invalida"


def test_pagina_y_datos_privados():
    r = client.get("/")
    assert r.status_code == 200
    assert "Cauce" in r.text
    assert client.get("/js/app.js").status_code == 200
    assert client.get("/data/processed/condados.csv").status_code == 404
    assert client.get("/models/modelo_rf.joblib").status_code == 404
