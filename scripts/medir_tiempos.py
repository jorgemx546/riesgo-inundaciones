"""Mide los tiempos de respuesta del sistema (RNF-01: 3 segundos o menos).

Uso, desde la raíz del repositorio:
    python scripts/medir_tiempos.py

Hace 20 consultas de predicción y de historial a la API (los 3 ejemplos de la
página y 17 condados elegidos al azar con semilla 42) y 5 búsquedas por dirección
con el geocodificador del Censo, que sí sale a internet. Guarda el resultado en
results/tiempos_rnf01.json.
"""
import json
import random
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from fastapi.testclient import TestClient  # noqa: E402

from src.api.app import app  # noqa: E402
from src.data.historial import listar_condados  # noqa: E402

EJEMPLOS = ["48201", "32003", "48371"]
DIRECCIONES = [
    "1001 Preston St, Houston, TX 77002",
    "200 S Spring St, Los Angeles, CA 90012",
    "400 S Las Vegas Blvd, Las Vegas, NV 89101",
    "100 N Holliday St, Baltimore, MD 21202",
    "550 Main St, Hartford, CT 06103",
]


def resumen(valores: list[float]) -> dict:
    return {"mediana": round(statistics.median(valores)), "maximo": round(max(valores)), "minimo": round(min(valores))}


def cronometrar(funcion) -> tuple[float, object]:
    inicio = time.perf_counter()
    r = funcion()
    return (time.perf_counter() - inicio) * 1000, r


def main() -> None:
    client = TestClient(app)
    client.get("/api/salud")  # carga el modelo antes de medir, como al arrancar el servidor

    otros = sorted(c["county_fips"] for c in listar_condados() if c["county_fips"] not in EJEMPLOS)
    random.Random(42).shuffle(otros)
    condados, consultas = list(EJEMPLOS), []
    for fips in otros:
        if len(condados) == 20:
            break
        if client.post("/api/predecir", json={"county_fips": fips}).status_code == 200:
            condados.append(fips)

    for fips in condados:
        t_pred, pred = cronometrar(lambda: client.post("/api/predecir", json={"county_fips": fips}))
        t_hist, _ = cronometrar(lambda: client.get(f"/api/historial/{fips}", params={"anios": 20}))
        datos = pred.json()
        consultas.append({"county_fips": fips, "prediccion": datos["prediccion"], "tiempo_ms_modelo": datos["tiempo_ms"],
                          "ms_predecir": round(t_pred), "ms_historial": round(t_hist), "ms_total": round(t_pred + t_hist)})

    direcciones = []
    for texto in DIRECCIONES:
        t, r = cronometrar(lambda: client.get("/api/direccion", params={"q": texto}))
        direcciones.append({"direccion": texto, "respuesta": r.json().get("county_fips", r.json().get("error")),
                            "ms_geocodificador": round(t)})

    total = [c["ms_total"] for c in consultas]
    resultado = {
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "meta_ms": 3000,
        "consultas": consultas,
        "resumen_modelo_ms": resumen([c["tiempo_ms_modelo"] for c in consultas]),
        "resumen_predecir_mas_historial_ms": resumen(total),
        "cumple_20_de_20": sum(t <= 3000 for t in total),
        "direcciones": direcciones,
        "resumen_geocodificador_ms": resumen([d["ms_geocodificador"] for d in direcciones]),
    }
    destino = RAIZ / "results" / "tiempos_rnf01.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'FIPS':<7}{'nivel':<7}{'modelo':>8}{'predecir':>10}{'historial':>11}{'total':>8}  (ms)")
    for c in consultas:
        print(f"{c['county_fips']:<7}{c['prediccion']:<7}{c['tiempo_ms_modelo']:>8}{c['ms_predecir']:>10}"
              f"{c['ms_historial']:>11}{c['ms_total']:>8}")
    print("Modelo:", resultado["resumen_modelo_ms"])
    print("Predecir + historial:", resultado["resumen_predecir_mas_historial_ms"],
          f"· {resultado['cumple_20_de_20']} de 20 en 3 s o menos")
    for d in direcciones:
        print(f"{d['ms_geocodificador']:>6} ms  {d['direccion']} -> {d['respuesta']}")
    print("Geocodificador:", resultado["resumen_geocodificador_ms"])
    print("Guardado en", destino.relative_to(RAIZ))


if __name__ == "__main__":
    main()
