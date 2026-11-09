"""Calcula la línea base sobre el conjunto de prueba (años base 2020 a 2024).

Uso:
    python src/models/baseline.py --data data/processed/county_year_model.csv
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score


def clase_de_reclamaciones(reclamaciones) -> np.ndarray:
    """Convierte un número de reclamaciones en nivel de riesgo."""
    return np.select([reclamaciones == 0, reclamaciones < 10], ["bajo", "medio"], "alto")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/processed/county_year_model.csv")
    args = parser.parse_args()

    datos = pd.read_csv(args.data, dtype={"county_fips": str})
    prueba = datos[datos.year >= 2020]
    real = prueba.risk_class

    reglas = {
        "Clase más frecuente (siempre bajo)": np.full(len(real), "bajo"),
        "Persistencia (mismo nivel que este año)": clase_de_reclamaciones(prueba.claims_1y),
    }
    for nombre, pred in reglas.items():
        print(
            f"{nombre}: exactitud {accuracy_score(real, pred):.3f} | "
            f"F1 macro {f1_score(real, pred, average='macro'):.3f} | "
            f"recall alto {recall_score(real, pred, labels=['alto'], average=None)[0]:.3f}"
        )


if __name__ == "__main__":
    main()
