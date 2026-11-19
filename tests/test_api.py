from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_salud():
    r = client.get("/api/salud")
    assert r.status_code == 200
    assert r.json().get("estado") == "ok"


def test_predecir_niveles():
    r_alto = client.post("/api/predecir", json={"county_fips": "48201"})
    assert r_alto.status_code == 200
    assert "alto" in str(r_alto.json()).lower()

    r_medio = client.post("/api/predecir", json={"county_fips": "32003"})
    assert r_medio.status_code == 200
    assert "medio" in str(r_medio.json()).lower()

    r_bajo = client.post("/api/predecir", json={"county_fips": "48371"})
    assert r_bajo.status_code == 200
    assert "bajo" in str(r_bajo.json()).lower()


def test_predecir_fips_invalido_e_inexistente():
    r_inv = client.post("/api/predecir", json={"county_fips": "abc"})
    assert r_inv.status_code == 422

    r_no_existe = client.post("/api/predecir", json={"county_fips": "09110"})
    assert r_no_existe.status_code == 404


def test_historial_anios():
    r_20 = client.get("/api/historial/48201", params={"anios": 20})
    assert r_20.status_code == 200
    datos = r_20.json()
    lista = datos if isinstance(datos, list) else datos.get("historial", datos.get("anios", datos.get("datos", [])))
    assert len(lista) == 20

    r_15 = client.get("/api/historial/48201", params={"anios": 15})
    assert r_15.status_code == 422


def test_condados():
    r = client.get("/api/condados")
    assert r.status_code == 200
    datos = r.json()
    condados = datos if isinstance(datos, list) else datos.get("condados", [])
    assert len(condados) == 3141