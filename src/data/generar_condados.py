from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path("data/processed")
RAW_DIR = Path("data/raw")

GAZETTEER_URLS = [
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip",
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.txt",
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip",
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2022_Gazetteer/2022_Gaz_counties_national.txt",
]


def obtener_fips_disponibles() -> set[str]:
    """Busca todos los códigos county_fips presentes en los archivos de data/processed."""
    fips_set: set[str] = set()
    for archivo in PROCESSED_DIR.glob("*"):
        if archivo.name == "condados.csv":
            continue
        if archivo.suffix == ".csv":
            df = pd.read_csv(archivo, dtype=str)
        elif archivo.suffix == ".parquet":
            df = pd.read_parquet(archivo)
        else:
            continue

        col_fips = next((c for c in df.columns if c.lower() in ("county_fips", "fips")), None)
        if col_fips:
            codigos = df[col_fips].dropna().astype(str).str.strip().str.zfill(5)
            fips_set.update(codigos.tolist())

    return fips_set


def cargar_gazetteer() -> pd.DataFrame:
    """Carga el Gazetteer oficial desde data/raw si existe, o lo descarga del US Census."""
    if RAW_DIR.exists():
        locales = list(RAW_DIR.glob("*Gaz_counties_national*"))
        if locales:
            print(f"Usando archivo local: {locales[0]}")
            return pd.read_csv(locales[0], sep="\t", dtype={"GEOID": str}, encoding="latin1")

    for url in GAZETTEER_URLS:
        try:
            print(f"Intentando descargar: {url}")
            df = pd.read_csv(url, sep="\t", dtype={"GEOID": str}, encoding="latin1")
            print("Descarga exitosa.")
            return df
        except Exception as e:
            print(f"No disponible ({e}), probando siguiente fuente...")

    raise RuntimeError("No se pudo descargar el Gazetteer del Censo desde ninguna URL oficial.")


def generar_catalogo_condados(fips_disponibles: set[str]) -> pd.DataFrame:
    df_gaz = cargar_gazetteer()
    df_gaz.columns = df_gaz.columns.str.strip()

    df_gaz["county_fips"] = df_gaz["GEOID"].str.strip().str.zfill(5)
    df_gaz["condado"] = df_gaz["NAME"].str.strip()
    df_gaz["estado"] = df_gaz["USPS"].str.strip()

    catalogo = (
        df_gaz[df_gaz["county_fips"].isin(fips_disponibles)][["county_fips", "condado", "estado"]]
        .drop_duplicates(subset=["county_fips"])
        .sort_values(by=["estado", "condado"], ascending=[True, True])
        .reset_index(drop=True)
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    salida = PROCESSED_DIR / "condados.csv"
    catalogo.to_csv(salida, index=False)
    print(f"Catálogo generado en {salida} con {len(catalogo)} condados.")
    return catalogo


if __name__ == "__main__":
    fips = obtener_fips_disponibles()
    print(f"FIPS encontrados en data/processed: {len(fips)}")
    generar_catalogo_condados(fips)