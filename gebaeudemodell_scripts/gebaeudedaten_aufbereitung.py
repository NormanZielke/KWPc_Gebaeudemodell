from pathlib import Path
import geopandas as gpd
import json


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
        layer=layer,
        driver="GPKG"
    )

    print(
        f"\nAufbereitetes Gebäudemodell gespeichert unter:\n"
        f"{output_path}"
    )

    return output_path


def analyse_nutzungart_encoding(
        path,
        layer=None,
        column="NutzungArt"
):
    """
    Sucht in einer Spalte nach dem Unicode-Ersatzzeichen '�'
    und gibt alle betroffenen Kategorien mit ihrer Häufigkeit aus.

    Es werden noch keine Daten verändert.
    """

    path = Path(path)

    # ---------------------------------------------------------
    # Daten einlesen
    # ---------------------------------------------------------
    if layer is None:
        gdf = gpd.read_file(path)
    else:
        gdf = gpd.read_file(
            path,
            layer=layer
        )

    # ---------------------------------------------------------
    # Spalte prüfen
    # ---------------------------------------------------------
    if column not in gdf.columns:
        raise KeyError(
            f"Spalte '{column}' nicht im Gebäudemodell gefunden."
        )

    # ---------------------------------------------------------
    # Problematische Werte finden
    # ---------------------------------------------------------
    mask = (
        gdf[column]
        .astype("string")
        .str.contains(
            "�",
            regex=False,
            na=False
        )
    )

    problematic_values = (
        gdf.loc[
            mask,
            column
        ]
        .value_counts()
        .rename_axis(column)
        .reset_index(name="Anzahl")
    )

    # ---------------------------------------------------------
    # Ausgabe
    # ---------------------------------------------------------
    print(
        "\n"
        "============================================================"
    )

    print(
        f"Encoding-Prüfung: {column}"
    )

    print(
        "============================================================"
    )

    print(
        f"Betroffene Gebäude: {mask.sum()}"
    )

    print(
        f"Unterschiedliche problematische Werte: "
        f"{len(problematic_values)}"
    )

    if problematic_values.empty:

        print(
            "\nKeine problematischen Encoding-Werte gefunden."
        )

    else:

        print(
            "\nProblematische Werte:"
        )

        print(
            problematic_values.to_string(
                index=False
            )
        )

    return problematic_values


def fix_encoding(
        gdf,
        mapping_path,
        column="NutzungArt"
):
    """
    Korrigiert bekannte Encoding-Fehler anhand einer JSON-Mapping-Datei.

    Unbekannte fehlerhafte Werte mit '�' führen zu einem Fehler,
    damit keine problematischen Kategorien unbemerkt bestehen bleiben.
    """

    mapping_path = Path(mapping_path)

    if column not in gdf.columns:
        raise KeyError(
            f"Spalte '{column}' nicht im Gebäudemodell gefunden."
        )

    # ---------------------------------------------------------
    # Mapping laden
    # ---------------------------------------------------------
    with open(
        mapping_path,
        "r",
        encoding="utf-8"
    ) as file:

        encoding_mapping = json.load(file)

    gdf = gdf.copy()

    # ---------------------------------------------------------
    # Werte ersetzen
    # ---------------------------------------------------------
    gdf[column] = gdf[column].replace(
        encoding_mapping
    )

    # ---------------------------------------------------------
    # Prüfen, ob noch fehlerhafte Werte vorhanden sind
    # ---------------------------------------------------------
    remaining_mask = (
        gdf[column]
        .astype("string")
        .str.contains(
            "�",
            regex=False,
            na=False
        )
    )

    if remaining_mask.any():

        remaining_values = (
            gdf.loc[
                remaining_mask,
                column
            ]
            .value_counts()
        )

        raise ValueError(
            "Nach der Encoding-Korrektur existieren noch "
            "unbekannte problematische Werte:\n\n"
            f"{remaining_values.to_string()}"
        )

    print(
        f"\nEncoding-Korrektur für '{column}' abgeschlossen."
    )

    return gdf