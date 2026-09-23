from pathlib import Path

import geopandas as gpd
import pandas as pd


# -------------------------------------------------------------
# Pfade
# -------------------------------------------------------------
HN_PATH = Path(
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "260728_Gebäudemodell_HohenNeuendorf.gpkg"
)

ALKIS_PATH = Path(
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "alkis_EG_HN.gpkg"
)

WK_PATH = Path(
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "WK_EG_HN.gpkg"
)

OUTPUT_PATH = Path(
    "2_Datenaufbereitung/HN/HN-Gebäudemodell/"
    "260728_Gebäudemodell_HohenNeuendorf_preprocessed.gpkg"
)


# -------------------------------------------------------------
# Layer
# -------------------------------------------------------------
HN_LAYER = "gebudemodell_final_28042026_saniert"


def add_source_column(
    hn_path,
    output_path,
    layer=None,
):
    """
    Fügt dem HN-Gebäudemodell die Spalte 'Quelle' hinzu.

    Zuordnung:
        NutzungArt belegt -> WK
        funktion belegt   -> ALKIS

    Die ursprüngliche GeoPackage-Datei wird nicht verändert.
    Es wird ein neuer Zwischendatensatz erzeugt.

    Parameters
    ----------
    hn_path : str | pathlib.Path
        Pfad zum HN-Gebäudemodell.

    output_path : str | pathlib.Path
        Zielpfad des neuen GeoPackages.

    layer : str | None
        Layername des HN-Gebäudemodells.

    Returns
    -------
    geopandas.GeoDataFrame
        Gebäudemodell mit zusätzlicher Spalte 'Quelle'.
    """

    hn_path = Path(hn_path)
    output_path = Path(output_path)

    # ---------------------------------------------------------
    # Gebäudemodell einlesen
    # ---------------------------------------------------------
    if layer is None:
        gdf = gpd.read_file(hn_path)
    else:
        gdf = gpd.read_file(
            hn_path,
            layer=layer
        )

    # ---------------------------------------------------------
    # Prüfen, ob benötigte Spalten vorhanden sind
    # ---------------------------------------------------------
    required_cols = [
        "NutzungArt",
        "funktion"
    ]

    missing_cols = [
        col for col in required_cols
        if col not in gdf.columns
    ]

    if missing_cols:
        raise KeyError(
            f"Folgende Spalten fehlen im HN-Gebäudemodell: "
            f"{missing_cols}"
        )

    # ---------------------------------------------------------
    # Leere Strings als fehlende Werte behandeln
    # ---------------------------------------------------------
    nutzung = gdf["NutzungArt"].replace(
        r"^\s*$",
        pd.NA,
        regex=True
    )

    funktion = gdf["funktion"].replace(
        r"^\s*$",
        pd.NA,
        regex=True
    )

    # ---------------------------------------------------------
    # Gruppen definieren
    # ---------------------------------------------------------
    mask_wk = (
        nutzung.notna()
        & funktion.isna()
    )

    mask_alkis = (
        nutzung.isna()
        & funktion.notna()
    )

    mask_beide = (
        nutzung.notna()
        & funktion.notna()
    )

    mask_keine = (
        nutzung.isna()
        & funktion.isna()
    )

    # ---------------------------------------------------------
    # Neue Spalte "Quelle" anlegen
    # ---------------------------------------------------------
    gdf["Quelle"] = pd.NA

    gdf.loc[
        mask_wk,
        "Quelle"
    ] = "WK"

    gdf.loc[
        mask_alkis,
        "Quelle"
    ] = "ALKIS"

    # Falls sich der Datensatz später verändert,
    # werden unklare Fälle explizit gekennzeichnet.
    gdf.loc[
        mask_beide | mask_keine,
        "Quelle"
    ] = "unklar"

    # ---------------------------------------------------------
    # Kontrolle im Terminal
    # ---------------------------------------------------------
    print("\n--- Herkunft der Gebäude ---")

    print(
        gdf["Quelle"]
        .value_counts(dropna=False)
        .to_string()
    )

    print(
        f"\nGesamtzahl Gebäude: {len(gdf)}"
    )

    if mask_beide.any():
        print(
            f"\nWARNUNG: {mask_beide.sum()} Gebäude haben "
            f"sowohl 'NutzungArt' als auch 'funktion' belegt."
        )

    if mask_keine.any():
        print(
            f"\nWARNUNG: {mask_keine.sum()} Gebäude haben "
            f"weder 'NutzungArt' noch 'funktion' belegt."
        )

    # ---------------------------------------------------------
    # Zielordner erzeugen
    # ---------------------------------------------------------
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # Neues GeoPackage schreiben
    # ---------------------------------------------------------
    output_layer = (
        layer
        if layer is not None
        else "gebaeudemodell"
    )

    gdf.to_file(
        output_path,
        layer=output_layer,
        driver="GPKG"
    )

    print(
        f"\nZwischendatensatz gespeichert unter:\n"
        f"{output_path}"
    )

    print(
        f"\nLayer:\n"
        f"{output_layer}"
    )

    return gdf


# -------------------------------------------------------------
# Skript ausführen
# -------------------------------------------------------------
if __name__ == "__main__":

    gdf = add_source_column(
        hn_path=HN_PATH,
        output_path=OUTPUT_PATH,
        layer=HN_LAYER,
    )