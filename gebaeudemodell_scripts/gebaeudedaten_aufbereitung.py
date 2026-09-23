from pathlib import Path
import json

import geopandas as gpd
import pandas as pd


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


def combine_exclusive_columns(
        gdf,
        primary_col,
        fallback_col,
        output_col
):
    """
    Vereint zwei sich gegenseitig ausschließende Spalten
    zu einer neuen Spalte.

    Regeln:
        1. Wert aus primary_col verwenden, falls vorhanden.
        2. Sonst Wert aus fallback_col verwenden.
        3. Sind beide Spalten befüllt, wird abgebrochen.
        4. Sind beide leer, bleibt auch output_col leer.

    Das ursprüngliche GeoDataFrame wird nicht verändert.
    """

    required_cols = [
        primary_col,
        fallback_col
    ]

    missing_cols = [
        col for col in required_cols
        if col not in gdf.columns
    ]

    if missing_cols:
        raise KeyError(
            f"Folgende Spalten fehlen im Gebäudemodell: "
            f"{missing_cols}"
        )

    data = gdf.copy()

    # ---------------------------------------------------------
    # Leere Strings als fehlende Werte behandeln
    # ---------------------------------------------------------
    for col in required_cols:

        data[col] = data[col].replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

    # ---------------------------------------------------------
    # Prüfen, ob beide Spalten gleichzeitig befüllt sind
    # ---------------------------------------------------------
    both_filled = (
        data[primary_col].notna()
        & data[fallback_col].notna()
    )

    if both_filled.any():

        examples = (
            data.loc[
                both_filled,
                [
                    primary_col,
                    fallback_col
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

        raise ValueError(
            f"\nDie Spalten '{primary_col}' und "
            f"'{fallback_col}' sind bei "
            f"{both_filled.sum()} Gebäuden gleichzeitig befüllt.\n"
            "Eine eindeutige Zusammenführung ist daher nicht möglich.\n\n"
            f"Beispiele:\n{examples}"
        )

    # ---------------------------------------------------------
    # Neue kombinierte Spalte erzeugen
    # ---------------------------------------------------------
    data[output_col] = (
        data[primary_col]
        .fillna(data[fallback_col])
    )

    # ---------------------------------------------------------
    # Plausibilitätsausgabe
    # ---------------------------------------------------------
    from_primary = data[primary_col].notna().sum()
    from_fallback = data[fallback_col].notna().sum()
    without_value = data[output_col].isna().sum()

    print(
        "\n"
        "============================================================"
    )

    print(
        f"Neue Spalte: {output_col}"
    )

    print(
        "============================================================"
    )

    print(
        f"Aus '{primary_col}': "
        f"{from_primary}"
    )

    print(
        f"Aus '{fallback_col}': "
        f"{from_fallback}"
    )

    print(
        f"Ohne Zuordnung: "
        f"{without_value}"
    )

    return data


def add_source_column(
        gdf,
        nutzung_col="NutzungArt",
        funktion_col="funktion",
        output_col="Quelle"
):
    """
    Ergänzt eine Spalte mit der Herkunft der Gebäudeklassifikation.

    Regeln:
        NutzungArt befüllt -> WK
        funktion befüllt   -> ALKIS
        beide leer         -> unklar
        beide befüllt      -> unklar

    Das ursprüngliche GeoDataFrame wird nicht verändert.
    """

    required_cols = [
        nutzung_col,
        funktion_col
    ]

    missing_cols = [
        col for col in required_cols
        if col not in gdf.columns
    ]

    if missing_cols:
        raise KeyError(
            f"Folgende Spalten fehlen im Gebäudemodell: "
            f"{missing_cols}"
        )

    data = gdf.copy()

    # ---------------------------------------------------------
    # Leere Strings als fehlende Werte behandeln
    # ---------------------------------------------------------
    for col in required_cols:

        data[col] = data[col].replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

    # ---------------------------------------------------------
    # Quelle bestimmen
    # ---------------------------------------------------------
    nutzung_filled = data[nutzung_col].notna()
    funktion_filled = data[funktion_col].notna()

    data[output_col] = "unklar"

    data.loc[
        nutzung_filled & ~funktion_filled,
        output_col
    ] = "WK"

    data.loc[
        ~nutzung_filled & funktion_filled,
        output_col
    ] = "ALKIS"

    # ---------------------------------------------------------
    # Ausgabe
    # ---------------------------------------------------------
    print(
        "\n"
        "============================================================"
    )

    print(
        f"Quellspalte erzeugt: {output_col}"
    )

    print(
        "============================================================"
    )

    print(
        data[output_col]
        .value_counts(dropna=False)
        .to_string()
    )

    return data


def prepare_gebaeudemodell(
        input_path,
        output_path,
        encoding_mapping_path,
        layer=None,
        encoding_column="NutzungArt",
        primary_col="NutzungArt",
        fallback_col="funktion",
        combined_col="NutzungArt_und_funktion",
        source_col="Quelle"
):
    """
    Bereitet das Gebäudemodell auf und speichert das Ergebnis
    als neues GeoPackage.

    Verarbeitung:
        1. Gebäudemodell einlesen
        2. Encoding-Fehler korrigieren
        3. Zwei exklusive Spalten zusammenführen
        4. Aufbereitetes GeoPackage speichern

    Die Rohdaten werden nicht verändert.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)
    encoding_mapping_path = Path(
        encoding_mapping_path
    )

    # ---------------------------------------------------------
    # 1. Daten einlesen
    # ---------------------------------------------------------
    if layer is None:

        gdf = gpd.read_file(
            input_path
        )

    else:

        gdf = gpd.read_file(
            input_path,
            layer=layer
        )

    print(
        "\n"
        "============================================================"
    )

    print(
        "Gebäudemodell aufbereiten"
    )

    print(
        "============================================================"
    )

    print(
        f"Input: {input_path}"
    )

    # ---------------------------------------------------------
    # 2. Encoding korrigieren
    # ---------------------------------------------------------
    gdf = fix_encoding(
        gdf=gdf,
        mapping_path=encoding_mapping_path,
        column=encoding_column
    )

    # ---------------------------------------------------------
    # 3. Datenquelle bestimmen
    # ---------------------------------------------------------
    gdf = add_source_column(
        gdf=gdf,
        nutzung_col=primary_col,
        funktion_col=fallback_col,
        output_col=source_col
    )

    # ---------------------------------------------------------
    # 4. NutzungArt und funktion zusammenführen
    # ---------------------------------------------------------
    gdf = combine_exclusive_columns(
        gdf=gdf,
        primary_col=primary_col,
        fallback_col=fallback_col,
        output_col=combined_col
    )

    # ---------------------------------------------------------
    # 5. Zielordner erzeugen
    # ---------------------------------------------------------
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # 6. GeoPackage speichern
    # ---------------------------------------------------------
    if layer is None:

        gdf.to_file(
            output_path,
            driver="GPKG"
        )

    else:

        gdf.to_file(
            output_path,
            layer=layer,
            driver="GPKG"
        )

    print(
        "\nAufbereitung abgeschlossen."
    )

    print(
        f"Neue Spalte: {combined_col}"
    )

    print(
        f"Output: {output_path}"
    )

    return output_path