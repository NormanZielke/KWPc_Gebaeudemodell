from pathlib import Path
import geopandas as gpd


def prepare_gebaeudemodell(
        input_path,
        output_path,
        layer=None
):
    """
    Liest das Gebäudemodell ein und schreibt eine Kopie,
    die später für die Datenaufbereitung verwendet wird.

    Die Rohdaten werden nicht verändert.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    # ---------------------------------------------------------
    # Daten einlesen
    # ---------------------------------------------------------
    if layer is None:
        gdf = gpd.read_file(input_path)
    else:
        gdf = gpd.read_file(
            input_path,
            layer=layer
        )

    # ---------------------------------------------------------
    # Aufbereitete Daten als eigene Kopie
    # ---------------------------------------------------------
    gdf_prepared = gdf.copy()

    # ---------------------------------------------------------
    # Zielordner erzeugen
    # ---------------------------------------------------------
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # GeoPackage speichern
    # ---------------------------------------------------------
    gdf_prepared.to_file(
        output_path,
        driver="GPKG"
    )

    print(
        f"\nAufbereitetes Gebäudemodell gespeichert unter:\n"
        f"{output_path}"
    )

    return output_path