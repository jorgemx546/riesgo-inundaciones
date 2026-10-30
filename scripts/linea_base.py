"""Calcula la línea base de la Entrega 2 sobre el conjunto de prueba (años base 2020-2024).
Uso: python linea_base.py county_year_model.csv"""
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

d = pd.read_csv(sys.argv[1], dtype={'county_fips': str})
prueba = d[d.year >= 2020]
y = prueba.risk_class
clase = lambda x: np.select([x == 0, x < 10], ['bajo', 'medio'], 'alto')

reglas = {
    'Clase más frecuente (siempre bajo)': np.full(len(y), 'bajo'),
    'Persistencia (mismo nivel que este año)': clase(prueba.claims_1y),
}
for nombre, pred in reglas.items():
    print(f"{nombre}: exactitud {accuracy_score(y, pred):.3f} | F1 macro {f1_score(y, pred, average='macro'):.3f} "
          f"| recall alto {recall_score(y, pred, labels=['alto'], average=None)[0]:.3f}")
