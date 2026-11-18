from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED_DIR = RAIZ / "data" / "processed"
CONDADOS_CSV = PROCESSED_DIR / "condados.csv"
MODELO_CSV = PROCESSED_DIR / "county_year_model.csv"
ORIGINAL_CSV = RAIZ / "data" / "raw" / "county_year_climate_flood_risk.csv"

# Código FIPS de cada estado (2 dígitos) y su abreviatura
ESTADOS_FIPS = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC",
    "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT",
    "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
}

# Los 8 condados de Connecticut que el Censo reemplazó por regiones en 2022: el Gazetteer actual
# ya no los trae, pero los datos del proyecto sí.
CONDADOS_CT_ANTERIORES = {
    "09001": "Fairfield County", "09003": "Hartford County", "09005": "Litchfield County", "09007": "Middlesex County",
    "09009": "New Haven County", "09011": "New London County", "09013": "Tolland County", "09015": "Windham County",
}


def _normalizar_fips(fips: str | int) -> str:
    return str(fips).strip().zfill(5)


@lru_cache(maxsize=1)
def _cargar_condados() -> pd.DataFrame:
    df = pd.read_csv(CONDADOS_CSV, dtype={"county_fips": str})
    df["county_fips"] = df["county_fips"].apply(_normalizar_fips)
    faltantes = pd.DataFrame(
        [{"county_fips": f, "condado": n, "estado": "CT"} for f, n in CONDADOS_CT_ANTERIORES.items()
         if f not in set(df["county_fips"])]
    )
    df = pd.concat([df, faltantes], ignore_index=True)
    return df.sort_values(by=["estado", "condado"], ascending=[True, True]).reset_index(drop=True)


@lru_cache(maxsize=1)
def _cargar_datos_modelo() -> pd.DataFrame:
    df = pd.read_csv(MODELO_CSV, dtype={"county_fips": str})
    df["county_fips"] = df["county_fips"].apply(_normalizar_fips)
    df["year"] = df["year"].astype(int)
    return df.sort_values(by=["county_fips", "year"]).reset_index(drop=True)


@lru_cache(maxsize=1)
def _cargar_declaratorias() -> pd.Series:
    """Declaratorias de FEMA de cada condado y año, tal como vienen en los datos originales."""
    df = pd.read_csv(ORIGINAL_CSV, usecols=["county_fips", "year", "fema_declaration_count"], dtype={"county_fips": str})
    df["county_fips"] = df["county_fips"].apply(_normalizar_fips)
    return df.set_index(["county_fips", "year"])["fema_declaration_count"]


def listar_condados() -> list[dict[str, str]]:
    """Devuelve la lista de condados disponibles ordenados por estado y nombre."""
    df = _cargar_condados()
    return df[["county_fips", "condado", "estado"]].to_dict(orient="records")


def historial_condado(fips: str, anios: int = 10) -> dict | None:
    """
    Devuelve el historial anual (10 o 20 años) y KPIs del condado.
    Si el condado no tiene datos, devuelve None. Si tiene datos pero no aparece en el
    catálogo del Censo, el nombre va vacío y el estado se toma del FIPS.
    """
    if anios not in (10, 20):
        anios = 10

    fips_norm = _normalizar_fips(fips)
    df_modelo = _cargar_datos_modelo()
    df_c = df_modelo[df_modelo["county_fips"] == fips_norm].sort_values("year")
    if df_c.empty:
        return None

    condados = _cargar_condados()
    fila_condado = condados[condados["county_fips"] == fips_norm]
    if fila_condado.empty:
        nombre, estado = "", ESTADOS_FIPS.get(fips_norm[:2], "")
    else:
        nombre, estado = str(fila_condado.iloc[0]["condado"]), str(fila_condado.iloc[0]["estado"])

    anio_fin = int(df_c["year"].max())
    lista_anios = list(range(anio_fin - anios + 1, anio_fin + 1))

    # Series anuales: reclamaciones y eventos de la tabla del modelo; declaratorias de los datos originales
    rec_por_anio = df_c.set_index("year")["claims_1y"].to_dict()
    evt_por_anio = df_c.set_index("year")["flood_events_1y"].to_dict()
    declaratorias_originales = _cargar_declaratorias()

    reclamaciones = [int(round(rec_por_anio.get(a, 0))) for a in lista_anios]
    eventos_inundacion = [int(round(evt_por_anio.get(a, 0))) for a in lista_anios]
    declaratorias = [int(declaratorias_originales.get((fips_norm, a), 0)) for a in lista_anios]

    # Fila del último año disponible (anio_fin) para extraer los KPIs acumulados
    ultima_fila = df_c[df_c["year"] == anio_fin].iloc[0]
    monto_5y_usd = float(np.expm1(ultima_fila["paid_loss_5y_log"]))

    kpis = {
        "reclamaciones_5y": int(round(ultima_fila["claims_5y"])),
        "monto_pagado_5y_usd": round(monto_5y_usd, 2),
        "eventos_inundacion_10y": int(round(ultima_fila["flood_events_10y"])),
        "declaratorias_5y": int(round(ultima_fila["fema_decl_5y"])),
    }

    return {
        "county_fips": fips_norm,
        "condado": nombre,
        "estado": estado,
        "anios": lista_anios,
        "reclamaciones": reclamaciones,
        "eventos_inundacion": eventos_inundacion,
        "declaratorias": declaratorias,
        "kpis": kpis,
    }
