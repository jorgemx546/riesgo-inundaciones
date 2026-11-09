"""Construye la tabla para el modelo: una fila por condado y año base t, con variables
de 1, 5 y 10 años y la clase de riesgo del año t+1.

Uso:
    python src/data/preprocess.py --raw data/raw --output data/processed/county_year_model.csv
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNAS_ORIGEN = [
    "nfip_claim_count",
    "nfip_paid_loss_usd",
    "high_severity_claim_count",
    "storm_event_count",
    "flood_related_event_count",
    "storm_total_damage_usd",
    "storm_deaths",
    "fema_declaration_count",
]


def construir_tabla(crudo: pd.DataFrame) -> pd.DataFrame:
    """Limpia la tabla original y calcula variables y objetivo."""
    fips = crudo.county_fips

    # Se quedan los condados de los 50 estados y DC. 2026 está incompleto y queda fuera.
    es_condado = ~fips.str.endswith("000") & (fips.str[:2].astype(int) <= 56)
    base = crudo[es_condado & (crudo.year <= 2025)].copy()
    base["nfip_paid_loss_usd"] = base.nfip_paid_loss_usd.clip(lower=0)

    # Un año sin registro para un condado cuenta como cero.
    indice = pd.MultiIndex.from_product(
        [base.county_fips.unique(), range(2000, 2026)], names=["county_fips", "year"]
    )
    tabla = (
        base.set_index(["county_fips", "year"])[COLUMNAS_ORIGEN]
        .reindex(indice)
        .fillna(0)
        .reset_index()
        .sort_values(["county_fips", "year"])
    )
    grupos = tabla.groupby("county_fips")

    def ventana(columna: str, anios: int) -> pd.Series:
        return grupos[columna].transform(lambda s: s.rolling(anios, min_periods=1).sum())

    salida = pd.DataFrame(
        {
            "county_fips": tabla.county_fips,
            "year": tabla.year,
            "state_fips": tabla.county_fips.str[:2],
        }
    )
    salida["claims_1y"] = tabla.nfip_claim_count
    salida["claims_5y"] = ventana("nfip_claim_count", 5)
    salida["claims_10y"] = ventana("nfip_claim_count", 10)
    salida["paid_loss_5y_log"] = np.log1p(ventana("nfip_paid_loss_usd", 5))
    salida["severe_claims_5y"] = ventana("high_severity_claim_count", 5)
    salida["flood_events_1y"] = tabla.flood_related_event_count
    salida["flood_events_5y"] = ventana("flood_related_event_count", 5)
    salida["flood_events_10y"] = ventana("flood_related_event_count", 10)
    salida["storm_events_1y"] = tabla.storm_event_count
    salida["storm_damage_10y_log"] = np.log1p(ventana("storm_total_damage_usd", 10))
    salida["storm_deaths_10y"] = ventana("storm_deaths", 10)
    salida["fema_decl_5y"] = ventana("fema_declaration_count", 5)

    # El objetivo es lo que pasa el año siguiente. No entra al modelo como variable.
    siguiente = grupos.nfip_claim_count.shift(-1)
    salida["claims_next_year"] = siguiente
    salida["risk_class"] = np.select([siguiente == 0, siguiente < 10], ["bajo", "medio"], "alto")
    return salida[siguiente.notna()].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="data/raw", help="carpeta con los datos originales")
    parser.add_argument("--output", default="data/processed/county_year_model.csv")
    args = parser.parse_args()

    origen = Path(args.raw) / "county_year_climate_flood_risk.csv"
    crudo = pd.read_csv(origen, dtype={"county_fips": str})
    tabla = construir_tabla(crudo)

    destino = Path(args.output)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(destino, index=False)
    print(
        f"[INFO] Tabla procesada: {tabla.shape[0]:,} filas y {tabla.shape[1]} columnas | "
        f"años base {tabla.year.min()} a {tabla.year.max()} | "
        f"{tabla.county_fips.nunique():,} condados | archivo: {destino.as_posix()}"
    )


if __name__ == "__main__":
    main()
