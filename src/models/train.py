"""Entrena y compara los modelos de riesgo de inundación por condado.

Todos usan la misma partición temporal. Los hiperparámetros se eligen con validación
cruzada por bloques de años dentro del entrenamiento; el conjunto de prueba solo se usa
para reportar.

Uso:
    python src/models/train.py --data data/processed/county_year_model.csv --output models/
"""
import argparse
import json
import logging
import platform
import time
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from matplotlib.colors import LinearSegmentedColormap
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

SEMILLA = 42
ANIO_PRUEBA = 2020
CLASES = ["bajo", "medio", "alto"]
VARIABLES_NUMERICAS = [
    "claims_1y",
    "claims_5y",
    "claims_10y",
    "paid_loss_5y_log",
    "severe_claims_5y",
    "flood_events_1y",
    "flood_events_5y",
    "flood_events_10y",
    "storm_events_1y",
    "storm_damage_10y_log",
    "storm_deaths_10y",
    "fema_decl_5y",
]
VARIABLES_CATEGORICAS = ["state_fips"]
VARIABLES = VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS
BLOQUES_VALIDACION = [(2008, 2010), (2011, 2013), (2014, 2016), (2017, 2019)]
OBJETIVO_F1 = 0.552
OBJETIVO_RECALL = 0.437

registro = logging.getLogger("entrenamiento")


def configurar_registro(archivo: Path) -> None:
    registro.setLevel(logging.INFO)
    formato = logging.Formatter("[%(levelname)s] %(message)s")
    for manejador in (logging.StreamHandler(), logging.FileHandler(archivo, "w", encoding="utf-8")):
        manejador.setFormatter(formato)
        registro.addHandler(manejador)


def bloques_temporales(anios: pd.Series) -> list:
    """Cada bloque se valida con un modelo entrenado solo con años anteriores."""
    posiciones = np.arange(len(anios))
    return [
        (posiciones[anios.to_numpy() < inicio], posiciones[anios.between(inicio, fin).to_numpy()])
        for inicio, fin in BLOQUES_VALIDACION
    ]


def preprocesador(numerico) -> ColumnTransformer:
    return ColumnTransformer(
        [
            ("numericas", numerico, VARIABLES_NUMERICAS),
            ("estado", OneHotEncoder(handle_unknown="ignore", sparse_output=False), VARIABLES_CATEGORICAS),
        ]
    )


def tubo_logistica(con_log: bool) -> Pipeline:
    pasos = [("estandarizar", StandardScaler())]
    if con_log:
        pasos.insert(0, ("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one")))
    return Pipeline(
        [
            ("preparar", preprocesador(Pipeline(pasos))),
            ("modelo", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEMILLA)),
        ]
    )


def tubo_arbol() -> Pipeline:
    return Pipeline(
        [
            ("preparar", preprocesador("passthrough")),
            ("modelo", DecisionTreeClassifier(class_weight="balanced", random_state=SEMILLA)),
        ]
    )


def tubo_bosque() -> Pipeline:
    return Pipeline(
        [
            ("preparar", preprocesador("passthrough")),
            (
                "modelo",
                RandomForestClassifier(
                    n_estimators=200, class_weight="balanced", n_jobs=-1, random_state=SEMILLA
                ),
            ),
        ]
    )


def buscar(tubo, parametros, bloques, datos, objetivo, azar=None) -> tuple:
    """Elige hiperparámetros por F1 macro en bloques de años. Devuelve búsqueda y tiempo."""
    inicio = time.perf_counter()
    if azar:
        busqueda = RandomizedSearchCV(
            tubo, parametros, n_iter=azar, scoring="f1_macro", cv=bloques, random_state=SEMILLA, refit=True
        )
    else:
        busqueda = GridSearchCV(tubo, parametros, scoring="f1_macro", cv=bloques, refit=True)
    busqueda.fit(datos, objetivo)
    return busqueda, time.perf_counter() - inicio


def evaluar_bloques(tubo, bloques, datos, objetivo) -> np.ndarray:
    resultados = []
    for entrenar, validar in bloques:
        ajuste = clone(tubo).fit(datos.iloc[entrenar], objetivo.iloc[entrenar])
        resultados.append(f1_score(objetivo.iloc[validar], ajuste.predict(datos.iloc[validar]), average="macro"))
    return np.array(resultados)


def metricas(real, pred) -> dict:
    return {
        "f1_macro": float(f1_score(real, pred, average="macro", labels=CLASES)),
        "recall_alto": float(recall_score(real, pred, labels=["alto"], average=None, zero_division=0)[0]),
        "exactitud": float(accuracy_score(real, pred)),
    }


def tiempo_por_fila(modelo, fila: pd.DataFrame, repeticiones: int = 30) -> float:
    medidas = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        modelo.predict_proba(fila)
        medidas.append((time.perf_counter() - inicio) * 1000)
    return float(np.median(medidas))


def diagnostico(f1_train: float, f1_test: float) -> str:
    brecha = f1_train - f1_test
    if f1_test <= OBJETIVO_F1:
        return "Subajuste" if brecha < 0.05 else "Sobreajuste, sin superar la línea base"
    if brecha > 0.15:
        return "Sobreajuste"
    return "Generaliza bien"


def bootstrap_por_condado(prueba, pred_a, pred_b, repeticiones: int = 500) -> dict:
    """Intervalo de 95 % para la diferencia de F1 macro, remuestreando condados completos."""
    azar = np.random.default_rng(SEMILLA)
    grupos = pd.Series(np.arange(len(prueba))).groupby(prueba.county_fips.to_numpy()).apply(np.array).to_list()
    real = prueba.risk_class.to_numpy()
    diferencias = []
    for _ in range(repeticiones):
        elegidos = azar.integers(0, len(grupos), len(grupos))
        filas = np.concatenate([grupos[i] for i in elegidos])
        diferencias.append(
            f1_score(real[filas], pred_a[filas], average="macro", labels=CLASES)
            - f1_score(real[filas], pred_b[filas], average="macro", labels=CLASES)
        )
    bajo, alto = np.percentile(diferencias, [2.5, 97.5])
    return {"media": float(np.mean(diferencias)), "ic95_bajo": float(bajo), "ic95_alto": float(alto)}


def importancias_agrupadas(modelo: Pipeline) -> dict:
    """Suma la importancia de todas las columnas one-hot en una sola variable de estado."""
    nombres = modelo.named_steps["preparar"].get_feature_names_out()
    valores = modelo.named_steps["modelo"].feature_importances_
    salida = {variable: 0.0 for variable in VARIABLES}
    for nombre, valor in zip(nombres, valores):
        limpio = nombre.split("__", 1)[1]
        clave = "state_fips" if limpio.startswith("state_fips") else limpio
        salida[clave] += float(valor)
    return dict(sorted(salida.items(), key=lambda par: par[1], reverse=True))


def calibracion(probabilidades: np.ndarray, real: np.ndarray, clases: np.ndarray) -> dict:
    """Compara la confianza del modelo con su acierto real, por tramos de confianza."""
    confianza = probabilidades.max(axis=1)
    acierto = clases[probabilidades.argmax(axis=1)] == real
    tramos = {}
    for inicio, fin in [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]:
        filtro = (confianza >= inicio) & (confianza < fin)
        if filtro.any():
            tramos[f"{inicio:.1f}-{min(fin, 1.0):.1f}"] = {
                "casos": int(filtro.sum()),
                "confianza_media": float(confianza[filtro].mean()),
                "acierto": float(acierto[filtro].mean()),
            }
    return {"confianza_media": float(confianza.mean()), "acierto": float(acierto.mean()), "tramos": tramos}


def grafica_matriz(real, pred, titulo: str, archivo: Path) -> None:
    matriz = confusion_matrix(real, pred, labels=CLASES)
    porcentaje = matriz / matriz.sum(axis=1, keepdims=True)
    mapa = LinearSegmentedColormap.from_list("azul", ["#eef4fc", "#2a78d6", "#123a6b"])
    figura, eje = plt.subplots(figsize=(5.6, 4.6), dpi=160)
    eje.imshow(porcentaje, cmap=mapa, vmin=0, vmax=1)
    etiquetas = ["Bajo", "Medio", "Alto"]
    eje.set_xticks(range(3), etiquetas)
    eje.set_yticks(range(3), etiquetas)
    eje.set_xlabel("Nivel predicho")
    eje.set_ylabel("Nivel real")
    eje.set_title(titulo, loc="left", fontweight="bold", fontsize=11)
    eje.tick_params(length=0)
    for lado in eje.spines.values():
        lado.set_visible(False)
    for i in range(3):
        for j in range(3):
            eje.text(
                j, i, f"{matriz[i, j]:,}\n{porcentaje[i, j]:.0%}", ha="center", va="center", fontsize=10,
                color="white" if porcentaje[i, j] > 0.45 else "#0b0b0b",
            )
    figura.tight_layout()
    figura.savefig(archivo)
    plt.close(figura)


def grafica_experimentos(tabla: pd.DataFrame, archivo: Path) -> None:
    filas = tabla[tabla["f1_train"].notna()].iloc[::-1]
    posiciones = np.arange(len(filas))
    figura, eje = plt.subplots(figsize=(8.2, 3.9), dpi=160)
    eje.axvline(OBJETIVO_F1, color="#52514e", linewidth=1.2, linestyle="--", zorder=1)
    eje.text(OBJETIVO_F1 + 0.006, len(filas) - 0.45, "Línea base 0.552", color="#52514e", fontsize=9)
    for pos, (_, fila) in zip(posiciones, filas.iterrows()):
        eje.plot([fila.f1_test, fila.f1_train], [pos, pos], color="#d6d5d0", linewidth=2, zorder=2)
    eje.scatter(filas.f1_train, posiciones, s=62, marker="s", color="#eb6834", edgecolors="white", zorder=3, label="Entrenamiento")
    eje.scatter(filas.f1_test, posiciones, s=70, marker="o", color="#2a78d6", edgecolors="white", zorder=3, label="Prueba")
    eje.set_yticks(posiciones, filas.experimento)
    eje.set_xlabel("F1 macro")
    eje.set_title("La distancia entre puntos muestra el sobreajuste", loc="left", fontweight="bold", fontsize=11, pad=24)
    eje.legend(ncols=2, loc="lower right", bbox_to_anchor=(1, 0.98), frameon=False)
    eje.spines[["top", "right", "left"]].set_visible(False)
    eje.tick_params(axis="y", length=0)
    eje.grid(axis="x", color="#e4e3df", linewidth=0.8)
    eje.set_axisbelow(True)
    figura.tight_layout()
    figura.savefig(archivo)
    plt.close(figura)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/processed/county_year_model.csv")
    parser.add_argument("--output", default="models/")
    parser.add_argument("--results", default="results/")
    args = parser.parse_args()

    salida = Path(args.output)
    resultados = Path(args.results)
    salida.mkdir(parents=True, exist_ok=True)
    resultados.mkdir(parents=True, exist_ok=True)
    configurar_registro(resultados / "entrenamiento.log")

    ruta_datos = Path(args.data)
    registro.info(f"Cargando dataset: {ruta_datos.as_posix()}")
    datos = pd.read_csv(ruta_datos, dtype={"county_fips": str, "state_fips": str})
    entrenamiento = datos[datos.year < ANIO_PRUEBA].reset_index(drop=True)
    prueba = datos[datos.year >= ANIO_PRUEBA].reset_index(drop=True)
    x_train, y_train = entrenamiento[VARIABLES], entrenamiento.risk_class
    x_test, y_test = prueba[VARIABLES], prueba.risk_class
    registro.info(f"Total: {len(datos):,} filas | {datos.county_fips.nunique():,} condados | {len(VARIABLES)} variables")
    registro.info(f"Entrenamiento: {len(x_train):,} filas (años base {entrenamiento.year.min()} a {entrenamiento.year.max()})")
    registro.info(f"Prueba: {len(x_test):,} filas (años base {prueba.year.min()} a {prueba.year.max()})")
    registro.info(f"Clases en prueba: {y_test.value_counts(normalize=True).round(3).to_dict()}")

    bloques = bloques_temporales(entrenamiento.year)
    registro.info(f"Validación por bloques: {BLOQUES_VALIDACION}")

    clase = lambda x: np.select([x == 0, x < 10], ["bajo", "medio"], "alto")
    persistencia_test = clase(prueba.claims_1y)
    filas = []
    for nombre, pred in {
        "Exp 0a: siempre bajo": np.full(len(y_test), "bajo"),
        "Exp 0b: persistencia": persistencia_test,
    }.items():
        m = metricas(y_test, pred)
        filas.append(
            {
                "experimento": nombre, "modelo": "Regla", "hiperparametros": "Sin parámetros",
                "f1_cv_media": np.nan, "f1_cv_desv": np.nan, "f1_train": np.nan, "f1_test": m["f1_macro"],
                "recall_alto_test": m["recall_alto"], "exactitud_test": m["exactitud"],
                "buscar_s": 0.0, "entrenar_s": 0.0, "predecir_ms_fila": 0.0, "diagnostico": "Referencia",
            }
        )
        registro.info(f"{nombre}: F1 macro {m['f1_macro']:.4f} | recall alto {m['recall_alto']:.4f}")

    def registrar(nombre, familia, modelo, parametros, tubo_cv=None, f1_cv=None, buscar_s=0.0, entrenar_s=None) -> tuple:
        if tubo_cv is not None:
            inicio = time.perf_counter()
            modelo.fit(x_train, y_train)
            entrenar_s = time.perf_counter() - inicio
            f1_cv = evaluar_bloques(tubo_cv, bloques, x_train, y_train)
        if hasattr(modelo.named_steps["modelo"], "n_jobs"):
            modelo.named_steps["modelo"].n_jobs = 1
            ms_fila = tiempo_por_fila(modelo, x_test.iloc[[0]])
            modelo.named_steps["modelo"].n_jobs = -1
        else:
            ms_fila = tiempo_por_fila(modelo, x_test.iloc[[0]])
        pred_train = modelo.predict(x_train)
        pred_test = modelo.predict(x_test)
        m_train, m_test = metricas(y_train, pred_train), metricas(y_test, pred_test)
        fila = {
            "experimento": nombre, "modelo": familia, "hiperparametros": parametros,
            "f1_cv_media": float(np.mean(f1_cv)), "f1_cv_desv": float(np.std(f1_cv)),
            "f1_train": m_train["f1_macro"], "f1_test": m_test["f1_macro"],
            "recall_alto_test": m_test["recall_alto"], "exactitud_test": m_test["exactitud"],
            "buscar_s": float(buscar_s), "entrenar_s": float(entrenar_s), "predecir_ms_fila": ms_fila,
            "diagnostico": diagnostico(m_train["f1_macro"], m_test["f1_macro"]),
        }
        filas.append(fila)
        registro.info(
            f"{nombre}: CV {fila['f1_cv_media']:.4f} ± {fila['f1_cv_desv']:.4f} | train {fila['f1_train']:.4f} | "
            f"test {fila['f1_test']:.4f} | recall alto {fila['recall_alto_test']:.4f} | "
            f"entrenar {fila['entrenar_s']:.1f} s | {ms_fila:.1f} ms por fila | {fila['diagnostico']}"
        )
        return modelo, pred_test

    def f1_del_mejor(busqueda) -> np.ndarray:
        i = busqueda.best_index_
        return np.array([busqueda.cv_results_[f"split{k}_test_score"][i] for k in range(len(bloques))])

    registro.info("Entrenando Exp 1: regresión logística con estandarización")
    registrar("Exp 1: logística base", "Regresión logística", tubo_logistica(False), "C=1.0, estandarización", tubo_cv=tubo_logistica(False))

    registro.info("Buscando hiperparámetros de Exp 2: regresión logística con log(1+x)")
    busqueda_log, s = buscar(tubo_logistica(True), {"modelo__C": [0.01, 0.1, 1.0, 10.0]}, bloques, x_train, y_train)
    logistica, pred_logistica = registrar(
        "Exp 2: logística ajustada", "Regresión logística", busqueda_log.best_estimator_,
        f"C={busqueda_log.best_params_['modelo__C']}, log(1+x) y estandarización",
        f1_cv=f1_del_mejor(busqueda_log), buscar_s=s, entrenar_s=busqueda_log.refit_time_,
    )

    registro.info("Entrenando Exp 3: árbol sin límite de profundidad")
    registrar("Exp 3: árbol base", "Árbol de decisión", tubo_arbol(), "Sin límite de profundidad", tubo_cv=tubo_arbol())

    registro.info("Buscando hiperparámetros de Exp 4: árbol regularizado")
    busqueda_arbol, s = buscar(
        tubo_arbol(),
        {"modelo__max_depth": [4, 6, 8, 10, 14], "modelo__min_samples_leaf": [1, 10, 50, 200]},
        bloques, x_train, y_train,
    )
    p = busqueda_arbol.best_params_
    registrar(
        "Exp 4: árbol ajustado", "Árbol de decisión", busqueda_arbol.best_estimator_,
        f"max_depth={p['modelo__max_depth']}, min_samples_leaf={p['modelo__min_samples_leaf']}",
        f1_cv=f1_del_mejor(busqueda_arbol), buscar_s=s, entrenar_s=busqueda_arbol.refit_time_,
    )

    registro.info("Entrenando Exp 5: Random Forest sin regularizar")
    registrar("Exp 5: bosque base", "Random Forest", tubo_bosque(), "200 árboles, sin límite de profundidad", tubo_cv=tubo_bosque())

    registro.info("Buscando hiperparámetros de Exp 6: Random Forest regularizado (12 combinaciones)")
    busqueda_rf, s = buscar(
        tubo_bosque(),
        {
            "modelo__max_depth": [10, 14, 18, 24, None],
            "modelo__min_samples_leaf": [2, 5, 10, 20, 50],
            "modelo__max_features": ["sqrt", 0.33, 0.5],
            "modelo__class_weight": ["balanced", "balanced_subsample"],
        },
        bloques, x_train, y_train, azar=12,
    )
    p = busqueda_rf.best_params_
    bosque, pred_bosque = registrar(
        "Exp 6: bosque ajustado", "Random Forest", busqueda_rf.best_estimator_,
        ", ".join(f"{k.replace('modelo__', '')}={v}" for k, v in p.items()) + ", 200 árboles",
        f1_cv=f1_del_mejor(busqueda_rf), buscar_s=s, entrenar_s=busqueda_rf.refit_time_,
    )
    registro.info(f"Búsqueda de hiperparámetros del bosque: {s:.0f} s")

    tabla = pd.DataFrame(filas)
    tabla.to_csv(resultados / "experimentos.csv", index=False, encoding="utf-8")
    con_cv = tabla[tabla.f1_cv_media.notna()]
    ganador_cv = con_cv.loc[con_cv.f1_cv_media.idxmax()]
    registro.info(f"Mejor F1 macro en validación por bloques: {ganador_cv.experimento} ({ganador_cv.f1_cv_media:.4f})")

    registro.info("[RESULTADOS EN CONJUNTO DE PRUEBA: Exp 6, bosque ajustado]")
    registro.info("\n" + classification_report(y_test, pred_bosque, labels=CLASES, digits=4))
    matriz = confusion_matrix(y_test, pred_bosque, labels=CLASES)
    registro.info("Matriz de confusión (filas = real, columnas = predicho; bajo, medio, alto):\n" + str(matriz))

    sin_2025 = prueba.year < 2024
    m_sin_2025 = {
        "persistencia": metricas(y_test[sin_2025], persistencia_test[sin_2025]),
        "bosque": metricas(y_test[sin_2025], pred_bosque[sin_2025]),
        "logistica": metricas(y_test[sin_2025], pred_logistica[sin_2025]),
    }
    registro.info(
        f"Sin el objetivo 2025: bosque F1 {m_sin_2025['bosque']['f1_macro']:.4f} | "
        f"persistencia F1 {m_sin_2025['persistencia']['f1_macro']:.4f}"
    )
    por_anio = {
        int(anio): {
            "bosque": metricas(y_test[prueba.year == anio], pred_bosque[prueba.year == anio]),
            "logistica": metricas(y_test[prueba.year == anio], pred_logistica[prueba.year == anio]),
            "persistencia": metricas(y_test[prueba.year == anio], persistencia_test[prueba.year == anio]),
        }
        for anio in sorted(prueba.year.unique())
    }
    for anio, valores in por_anio.items():
        registro.info(
            f"Año base {anio}: bosque {valores['bosque']['f1_macro']:.4f} | "
            f"logística {valores['logistica']['f1_macro']:.4f} | persistencia {valores['persistencia']['f1_macro']:.4f}"
        )

    comparaciones = {
        "bosque_menos_persistencia": bootstrap_por_condado(prueba, pred_bosque, persistencia_test),
        "bosque_menos_logistica": bootstrap_por_condado(prueba, pred_bosque, pred_logistica),
    }
    for nombre, valor in comparaciones.items():
        registro.info(f"{nombre}: {valor['media']:+.4f} (IC 95 %: {valor['ic95_bajo']:+.4f} a {valor['ic95_alto']:+.4f})")

    importancias = importancias_agrupadas(bosque)
    probabilidades = bosque.predict_proba(x_test)
    calibrado = calibracion(probabilidades, y_test.to_numpy(), bosque.classes_)
    registro.info(f"Confianza media {calibrado['confianza_media']:.3f} contra acierto {calibrado['acierto']:.3f}")

    grafica_matriz(y_test, pred_bosque, "Random Forest ajustado, conjunto de prueba", resultados / "matriz_confusion_rf.png")
    grafica_experimentos(tabla, resultados / "comparacion_experimentos.png")

    bosque.named_steps["modelo"].n_jobs = 1
    joblib.dump(bosque, salida / "modelo_rf.joblib", compress=3)
    joblib.dump(logistica, salida / "modelo_logistica.joblib", compress=3)
    metadatos = {
        "modelo": "modelo_rf.joblib",
        "variables": VARIABLES,
        "clases": CLASES,
        "importancias": importancias,
        "semilla": SEMILLA,
        "anio_prueba_desde": ANIO_PRUEBA,
        "hiperparametros": {k.replace("modelo__", ""): v for k, v in busqueda_rf.best_params_.items()},
        "versiones": {
            "python": platform.python_version(), "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__, "numpy": np.__version__, "joblib": joblib.__version__,
        },
    }
    (salida / "metadata.json").write_text(json.dumps(metadatos, ensure_ascii=False, indent=2), encoding="utf-8")
    resumen = {
        "objetivos": {"f1_macro": OBJETIVO_F1, "recall_alto": OBJETIVO_RECALL},
        "ganador_cv": ganador_cv.experimento,
        "matriz_confusion_rf": matriz.tolist(),
        "sin_objetivo_2025": m_sin_2025,
        "por_anio_base": por_anio,
        "bootstrap_por_condado": comparaciones,
        "calibracion_rf": calibrado,
        "busqueda_rf": pd.DataFrame(busqueda_rf.cv_results_)[
            ["param_modelo__max_depth", "param_modelo__min_samples_leaf", "param_modelo__max_features",
             "param_modelo__class_weight", "mean_test_score", "std_test_score"]
        ].astype(str).to_dict(orient="records"),
    }
    (resultados / "metricas.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    for archivo in ("modelo_rf.joblib", "modelo_logistica.joblib"):
        registro.info(f"[SUCCESS] Modelo guardado: {(salida / archivo).as_posix()} ({(salida / archivo).stat().st_size / 1e6:.1f} MB)")
    registro.info(f"[SUCCESS] Metadatos guardados: {(salida / 'metadata.json').as_posix()}")
    registro.info(f"[SUCCESS] Resultados guardados en: {resultados.as_posix()}")


if __name__ == "__main__":
    main()
