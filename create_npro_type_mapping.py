from pathlib import Path

import geopandas as gpd
import pandas as pd

from gebaeudetypen_common import (
    add_source_columns,
    make_columns_tag,
    prepare_category_data,
)


UNDECIDED = "muss fachlich entschieden werden"


# =============================================================
# nPro-Zuordnungen je Quellspalte
# =============================================================

NUTZUNGART_TO_NPRO = {
    # Wohnen
    "Wohnhaus": "Wohnen",
    "Wohngeb�ude": "Wohnen",
    "Wohnheim": "Wohnen",
    "Wochenendhaus": "Wohnen",

    # Büro / Verwaltung
    "Verwaltungsgeb�ude": "Büro",
    "Rathaus": "Büro",
    "B�rogeb�ude": "Büro",
    "Kreditinstitut": "Büro",

    # Bildung / Betreuung
    "Allgemein bildende Schule": "Schule",
    "Kinderkrippe, Kindergarten, Kindertagesst�tte": "Kindergarten",

    # Beherbergung / Gastronomie
    "Hotel, Motel, Pension": "Hotel",
    "Geb�ude f�r Beherbergung": "Hotel",
    "Gastst�tte, Restaurant": "Restaurant",
    "Geb�ude f�r Bewirtung": "Restaurant",

    # Produktion / Handel
    "Produktionsgeb�ude": "Produktion",
    "Kaufhaus": "Einzelhandel",

    # Explizit gemischte Nutzungen
    "Wohngeb�ude mit Gewerbe und Industrie": "Gemischt",
    "Wohngeb�ude mit Handel und Dienstleistungen": "Gemischt",
    "Geb�ude f�r Gewerbe und Industrie mit Wohnen": "Gemischt",
    "Geb�ude f�r Handel und Dienstleistung mit Wohnen": "Gemischt",
    "Wohn- und Gesch�ftsgeb�ude": "Gemischt",
    "Wohngeb�ude mit Gemeinbedarf": "Gemischt",
}


FUNKTION_TO_NPRO = {
    # Wohnen
    "Wohnhaus": "Wohnen",
    "Wochenendhaus": "Wohnen",

    # Parken
    "Garage": "Parkhaus",
    "Tiefgarage": "Parkhaus",
    "Gebäude zum Parken": "Parkhaus",

    # Sport
    "Sport-, Turnhalle": "Sporthalle",

    # Lager
    "Lagerhalle, Lagerschuppen, Lagerhaus": "Lagerhalle",
    "Gebäude für Vorratshaltung": "Lagerhalle",

    # Religion
    "Kirche": "Kirche",
    "Gebäude für religiöse Zwecke": "Kirche",
    "Kapelle": "Kirche",

    # Handel / Produktion
    "Einkaufszentrum": "Einkaufszentrum",
    "Produktionsgebäude": "Produktion",

    # Explizit gemischte Nutzung
    "Wohngebäude mit Handel und Dienstleistungen": "Gemischt",

    "Sonstiges": "Sonstiges",
}


# GebTyp ist gröber als NutzungArt.
# Deshalb werden nur fachlich eindeutige Kategorien automatisch gemappt.
GEBTYP_TO_NPRO = {
    "EFH": "Wohnen",
    "RH": "Wohnen",
    "MFH": "Wohnen",
    "GMH": "Wohnen",

    "B�ro-, Verwaltungs- oder Amtsgeb�ude": "Büro",
    "Handelsgeb�ude": "Einzelhandel",
}


COLUMN_TO_NPRO = {
    "NutzungArt": NUTZUNGART_TO_NPRO,
    "funktion": FUNKTION_TO_NPRO,
    "GebTyp": GEBTYP_TO_NPRO,
}


NPRO_TYPES = {
    "Wohnen",
    "Büro",
    "Schule",
    "Kindergarten",
    "Krankenhaus",
    "Pflegeheim",
    "Kantine",
    "Restaurant",
    "Hotel",
    "Museum",
    "Theater",
    "Parkhaus",
    "Einkaufszentrum",
    "Einzelhandel",
    "Supermarkt",
    "Sporthalle",
    "Fitnesscenter",
    "Schwimmbad",
    "Produktion",
    "Lagerhalle",
    "Bibliothek",
    "Kirche",
    "Gemischt",
    "Sonstiges",
}


def _resolve_npro_type(source_col, category):
    """
    Quellspaltenspezifische nPro-Zuordnung.
    """
    mapping = COLUMN_TO_NPRO.get(
        source_col,
        {}
    )

    return mapping.get(
        category,
        UNDECIDED
    )


def create_npro_type_mapping(
        gpkg_path,
        category_cols,
        excel_path=None,
        output_dir="outputs/gebaeudemodell",
        layer=None,
        overwrite=False,
):
    """
    Erstellt eine nPro-Mapping-Tabelle für frei wählbare
    Klassifikationsspalten.

    Beispiele
    ---------
    category_cols=["GebTyp"]
    category_cols=["GebTyp", "funktion"]
    category_cols=["NutzungArt", "funktion"]

    Wird excel_path nicht explizit übergeben, wird der Dateiname
    automatisch anhand der Spalten erzeugt.

    overwrite=False schützt eine bereits vorhandene und ggf. manuell
    bearbeitete Mapping-Datei vor Überschreiben.
    """
    gpkg_path = Path(gpkg_path)
    output_dir = Path(output_dir)

    if isinstance(category_cols, str):
        category_cols = [category_cols]

    category_cols = list(category_cols)

    tag = make_columns_tag(
        category_cols
    )

    if excel_path is None:
        excel_path = (
            output_dir
            / f"npro_type_mapping_{tag}.xlsx"
        )
    else:
        excel_path = Path(excel_path)

    # ---------------------------------------------------------
    # Bestehendes Mapping wiederverwenden
    # ---------------------------------------------------------
    if excel_path.exists() and not overwrite:
        print(
            f"Vorhandene Mapping-Datei wird wiederverwendet:\n"
            f"{excel_path}"
        )

        return pd.read_excel(
            excel_path
        )

    # ---------------------------------------------------------
    # GeoPackage einlesen
    # ---------------------------------------------------------
    if layer is None:
        gdf = gpd.read_file(
            gpkg_path
        )
    else:
        gdf = gpd.read_file(
            gpkg_path,
            layer=layer
        )

    data = prepare_category_data(
        gdf=gdf,
        category_cols=category_cols
    )

    # ---------------------------------------------------------
    # Mapping-Tabelle erzeugen
    # ---------------------------------------------------------
    mapping_df = (
        data
        .groupby(
            ["Kategorie", "Quellspalte"],
            dropna=False
        )
        .size()
        .reset_index(
            name="Anzahl - gdf"
        )
    )

    mapping_df = add_source_columns(
        result=mapping_df,
        category_cols=category_cols
    )

    mapping_df["npro_type"] = mapping_df.apply(
        lambda row: (
            _resolve_npro_type(
                row["Quellspalte"],
                row["Kategorie"]
            )
            if row["Quellspalte"] != "Keine Zuordnung"
            else UNDECIDED
        ),
        axis=1
    )

    # ---------------------------------------------------------
    # Plausibilitätscheck nPro-Typen
    # ---------------------------------------------------------
    automatic_types = (
        set(mapping_df["npro_type"])
        - {UNDECIDED}
    )

    invalid_types = (
        automatic_types
        .difference(NPRO_TYPES)
    )

    if invalid_types:
        raise ValueError(
            f"Ungültige nPro-Typen im Mapping: "
            f"{sorted(invalid_types)}"
        )

    source_output_cols = [
        f"{col} - gdf"
        for col in category_cols
    ]

    mapping_df = mapping_df[
        source_output_cols
        + [
            "Anzahl - gdf",
            "npro_type"
        ]
    ].reset_index(drop=True)

    # ---------------------------------------------------------
    # Excel speichern
    # ---------------------------------------------------------
    excel_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    mapping_df.to_excel(
        excel_path,
        index=False
    )

    print(
        f"Mapping-Datei geschrieben:\n"
        f"{excel_path}"
    )

    return mapping_df
