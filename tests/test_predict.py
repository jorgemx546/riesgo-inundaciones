"""Pruebas de la función predecir(). Uso: python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.predict import cargar_artefactos, predecir

CLAVES = {
    "prediccion", "clase_etiqueta", "confianza_o_score", "probabilidades",
    "anio_pronostico", "factores", "tiempo_ms",
}


class PruebasPredecir(unittest.TestCase):
    def test_condado_valido_cumple_el_contrato(self):
        salida = predecir({"county_fips": "48201", "anio_base": 2024})
        self.assertEqual(set(salida), CLAVES)
        self.assertIn(salida["prediccion"], {"bajo", "medio", "alto"})
        self.assertEqual(salida["anio_pronostico"], 2025)
        self.assertEqual(set(salida["probabilidades"]), {"bajo", "medio", "alto"})
        self.assertEqual(len(salida["factores"]), 4)

    def test_probabilidades_suman_uno(self):
        salida = predecir({"county_fips": "48245", "anio_base": 2024})
        self.assertAlmostEqual(sum(salida["probabilidades"].values()), 1.0, delta=0.02)

    def test_confianza_es_la_probabilidad_de_la_prediccion(self):
        salida = predecir({"county_fips": "48007", "anio_base": 2024})
        self.assertEqual(salida["confianza_o_score"], salida["probabilidades"][salida["prediccion"]])

    def test_coincide_con_el_modelo_directo(self):
        modelo, metadatos, tabla = cargar_artefactos()
        fila = tabla.loc[[("48201", 2024)], metadatos["variables"]]
        self.assertEqual(predecir({"county_fips": "48201", "anio_base": 2024})["prediccion"], modelo.predict(fila)[0])

    def test_entradas_invalidas_no_rompen(self):
        casos = [
            None, {}, {"county_fips": 48201, "anio_base": 2024}, {"county_fips": "4820", "anio_base": 2024},
            {"county_fips": "48201"}, {"county_fips": "48201", "anio_base": "2024"},
            {"county_fips": "48201", "anio_base": True},
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                self.assertEqual(predecir(caso)["error"], "entrada_invalida")

    def test_condado_o_anio_sin_datos(self):
        for caso in ({"county_fips": "99999", "anio_base": 2024}, {"county_fips": "48201", "anio_base": 1990}):
            with self.subTest(caso=caso):
                self.assertEqual(predecir(caso)["error"], "condado_sin_datos")

    def test_responde_en_menos_de_tres_segundos(self):
        cargar_artefactos()
        tiempos = [predecir({"county_fips": "48201", "anio_base": 2024})["tiempo_ms"] for _ in range(20)]
        self.assertLess(max(tiempos), 3000)


if __name__ == "__main__":
    unittest.main()
