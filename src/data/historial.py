from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED_DIR = RAIZ / "data" / "processed"
CONDADOS_CSV = PROCESSED_DIR / "condados.csv"
MODELO_CSV = PROCESSED_DIR / "county_year_model.csv"


def _normalizar_fips(fips: str | int) -> str:
    return str(fips).strip().zfill(5)


@lru_cache(maxsize=1)
def _cargar_condados() -> pd.DataFrame:
    df = pd.read_csv(CONDADOS_CSV, dtype={"county_fips": str})
    df["county_fips"] = df["county_fips"].apply(_normalizar_fips)
    return df.sort_values(by=["estado", "condado"], ascending=[True, True]).reset_index(drop=True)


@lru_cache(maxsize=1)
def _cargar_datos_modelo() -> pd.DataFrame:
    df = pd.read_csv(MODELO_CSV, dtype={"county_fips": str})
    df["county_fips"] = df["county_fips"].apply(_normalizar_fips)
    df["year"] = df["year"].astype(int)
    return df.sort_values(by=["county_fips", "year"]).reset_index(drop=True)


def listar_condados() -> list[dict[str, str]]:
    """Devuelve la lista de condados disponibles ordenados por estado y nombre."""
    df = _cargar_condados()
    return df[["county_fips", "condado", "estado"]].to_dict(orient="records")


def _reconstruir_declaratorias_anuales(df_condado: pd.DataFrame) -> dict[int, int]:
    """
    Reconstruye el conteo anual de declaratorias FEMA a partir de la ventana móvil fema_decl_5y.
    Si un año no tiene historia previa suficiente, estima el promedio anual de la ventana.
    """
    por_anio = df_condado.set_index("year")["fema_decl_5y"].to_dict()
    anios_ord = sorted(por_anio.keys())
    anuales: dict[int, int] = {}

    for anio in anios_ord:
        d_actual = int(round(por_anio[anio]))
        if (anio - 1) in por_anio and (anio - 5) in anuales:
            d_prev = int(round(por_anio[anio - 1]))
            val = d_actual - d_prev + anuales[anio - 5]
            anuales[anio] = max(0, val)
        else:
            # Inicialización para los primeros años de la serie
            anuales[anio] = max(0, round(d_actual / 5)) if (anio - 1) not in por_anio else max(0, d_actual - int(round(por_anio[anio - 1])))

    return anuales


def historial_condado(fips: str, anios: int = 10) -> dict | None:
    """
    Devuelve el historial anual (10 o 20 años) y KPIs del condado.
    Si el condado no existe, devuelve None.
    """
    if anios not in (10, 20):
        anios = 10

    fips_norm = _normalizar_fips(fips)
    condados = _cargar_condados()
    fila_condado = condados[condados["county_fips"] == fips_norm]
    if fila_condado.empty:
        return None

    df_modelo = _cargar_datos_modelo()
    df_c = df_modelo[df_modelo["county_fips"] == fips_norm].sort_values("year")
    if df_c.empty:
        return None

    info = fila_condado.iloc[0]
    anio_fin = int(df_c["year"].max())
    lista_anios = list(range(anio_fin - anios + 1, anio_fin + 1))

    # Mapear series anuales desde county_year_model.csv
    rec_por_anio = df_c.set_index("year")["claims_1y"].to_dict()
    evt_por_anio = df_c.set_index("year")["flood_events_1y"].to_dict()
    dec_por_anio = _reconstruir_declaratorias_anuales(df_c)

    reclamaciones = [int(round(rec_por_anio.get(a, 0))) for a in lista_anios]
    eventos_inundacion = [int(round(evt_por_anio.get(a, 0))) for a in lista_anios]
    declaratorias = [int(dec_por_anio.get(a, 0)) for a in lista_anios]

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
        "condado": str(info["condado"]),
        "estado": str(info["estado"]),
        "anios": lista_anios,
        "reclamaciones": reclamaciones,
        "eventos_inundacion": eventos_inundacion,
        "declaratorias": declaratorias,
        "kpis": kpis,
    }