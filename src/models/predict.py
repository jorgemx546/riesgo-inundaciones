"""Función de inferencia del proyecto. Es el contrato entre el motor de IA y el dashboard.

Uso desde Python, en la raíz del repositorio:
    from src.models.predict import predecir
    predecir({"county_fips": "48201", "anio_base": 2024})

Uso desde la terminal:
    python src/models/predict.py --fips 48201 --anio 2024
"""
import argparse
import json
import re
import time
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
ETIQUETAS = {"bajo": "Riesgo bajo", "medio": "Riesgo medio", "alto": "Riesgo alto"}


@lru_cache(maxsize=1)
def cargar_artefactos() -> tuple:
    """Carga modelo, metadatos y tabla una sola vez en memoria."""
    metadatos = json.loads((RAIZ / "models" / "metadata.json").read_text(encoding="utf-8"))
    modelo = joblib.load(RAIZ / "models" / metadatos["modelo"])
    tabla = pd.read_csv(
        RAIZ / "data" / "processed" / "county_year_model.csv",
        dtype={"county_fips": str, "state_fips": str},
    ).set_index(["county_fips", "year"]).sort_index()
    return modelo, metadatos, tabla


def error(codigo: str, mensaje: str) -> dict:
    return {"error": codigo, "mensaje": mensaje}


def valor_simple(valor):
    """Convierte un valor de pandas a un tipo que se pueda escribir en JSON."""
    if isinstance(valor, str):
        return valor
    numero = float(valor)
    return int(numero) if numero.is_integer() else round(numero, 2)


def predecir(datos_entrada: dict) -> dict:
    """Estima el nivel de riesgo de inundación de un condado para el año siguiente.

    Parámetros:
        datos_entrada: {"county_fips": "48201", "anio_base": 2024}

    Retorna:
        El nivel, su confianza, las probabilidades, los factores con más peso y el
        tiempo de inferencia. Si no se puede estimar, retorna {"error", "mensaje"}.
    """
    if not isinstance(datos_entrada, dict):
        return error("entrada_invalida", "La entrada debe ser un objeto con county_fips y anio_base.")
    fips = datos_entrada.get("county_fips")
    anio = datos_entrada.get("anio_base")
    if not isinstance(fips, str) or not re.fullmatch(r"\d{5}", fips):
        return error("entrada_invalida", "county_fips debe ser un texto de 5 dígitos.")
    if isinstance(anio, bool) or not isinstance(anio, int):
        return error("entrada_invalida", "anio_base debe ser un número entero.")

    modelo, metadatos, tabla = cargar_artefactos()
    inicio = time.perf_counter()  # La carga ocurre una sola vez y no cuenta como inferencia.
    if (fips, anio) not in tabla.index:
        return error("condado_sin_datos", "No hay datos suficientes de este condado para estimar el riesgo.")

    fila = tabla.loc[[(fips, anio)], metadatos["variables"]]
    probabilidades = modelo.predict_proba(fila)[0]
    por_clase = dict(zip(modelo.classes_, probabilidades))
    prediccion = max(por_clase, key=por_clase.get)

    factores = [
        {
            "variable": variable,
            "valor": valor_simple(fila.iloc[0][variable]),
            "importancia": round(importancia, 2),
        }
        for variable, importancia in list(metadatos["importancias"].items())[:4]
    ]

    return {
        "prediccion": prediccion,
        "clase_etiqueta": ETIQUETAS[prediccion],
        "confianza_o_score": round(float(por_clase[prediccion]), 2),
        "probabilidades": {clase: round(float(por_clase[clase]), 2) for clase in metadatos["clases"]},
        "anio_pronostico": anio + 1,
        "factores": factores,
        "tiempo_ms": round((time.perf_counter() - inicio) * 1000),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta el riesgo de un condado.")
    parser.add_argument("--fips", required=True, help="código FIPS de 5 dígitos")
    parser.add_argument("--anio", type=int, default=2024, help="año base")
    args = parser.parse_args()
    print(json.dumps(predecir({"county_fips": args.fips, "anio_base": args.anio}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
