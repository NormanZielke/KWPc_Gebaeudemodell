from pathlib import Path

import geopandas as gpd
import pandas as pd


UNDECIDED = "muss fachlich entschieden werden"

DEFAULT_GPKG_PATH = (
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "260728_Gebäudemodell_HohenNeuendorf.gpkg"
)

# nPro-Gebäudetypen, die wir in diesem Mapping verwenden.
# Wichtig: Die Werte in 'NutzungArt' wurden exakt so übernommen,
# wie sie im GeoPackage vorliegen. Die Zeichen '�' daher NICHT ersetzen,
# sonst greifen die String-Mappings nicht mehr.

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

    # Funktion ist bereits nur als Sonstiges klassifiziert
    "Sonstiges": "Sonstiges",
}


# Gültige nPro-Typen. Dient nur als Plausibilitätscheck für das Mapping.
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


def _resolve_npro_type(nutzungart, funktion):
    """Ordnet eine Kombination aus NutzungArt und funktion einem nPro-Typ zu.

    Regeln:
    - Eindeutige Zuordnung aus NutzungArt oder funktion wird übernommen.
    - Explizit gemischte Nutzung wird als 'Gemischt' klassifiziert.
    - Falls beide Felder unterschiedliche eindeutige Typen liefern,
      wird keine automatische Entscheidung getroffen.
    - Nicht eindeutig zuordenbare Fälle werden gekennzeichnet.
    """
    type_from_nutzung = NUTZUNGART_TO_NPRO.get(nutzungart)
    type_from_funktion = FUNKTION_TO_NPRO.get(funktion)

    # Explizite gemischte Nutzung hat Vorrang.
    if type_from_nutzung == "Gemischt" or type_from_funktion == "Gemischt":
        return "Gemischt"

    # Beide Felder liefern dieselbe eindeutige Zuordnung.
    if type_from_nutzung and type_from_funktion:
        if type_from_nutzung == type_from_funktion:
            return type_from_nutzung
        return UNDECIDED

    # Nur eines der beiden Felder ist eindeutig.
    if type_from_nutzung:
        return type_from_nutzung
    if type_from_funktion:
        return type_from_funktion

    return UNDECIDED


def create_npro_type_mapping(
    gpkg_path,
    excel_path="npro_type_mapping.xlsx",
    layer=None,
):
    """Erstellt ausschließlich eine Mapping-Tabelle aus dem GeoPackage.

    Das eingelesene GeoDataFrame wird NICHT verändert.

    Parameters
    ----------
    gpkg_path : str | pathlib.Path
        Pfad zum GeoPackage.
    excel_path : str | pathlib.Path
        Zielpfad der Excel-Datei.
    layer : str | None
        Optionaler Layername. Bei nur einem Layer kann None verwendet werden.

    Returns
    -------
    pandas.DataFrame
        Mapping-Tabelle mit den Spalten:
        - Gebäudetyp - gdf   (Quelle: NutzungArt)
        - Funktion - gdf     (Quelle: funktion)
        - Anzahl - gdf       (Anzahl dieser Kombination im GeoDataFrame)
        - npro_type
    """
    gpkg_path = Path(gpkg_path)
    excel_path = Path(excel_path)

    if layer is None:
        gdf = gpd.read_file(gpkg_path)
    else:
        gdf = gpd.read_file(gpkg_path, layer=layer)

    required_columns = {"NutzungArt", "funktion"}
    missing_columns = required_columns.difference(gdf.columns)
    if missing_columns:
        raise KeyError(
            f"Folgende benötigte Spalten fehlen im GeoPackage: "
            f"{sorted(missing_columns)}"
        )

    # Neue Tabelle erzeugen; das GeoDataFrame selbst bleibt unverändert.
    # Eine Zeile entspricht einer eindeutigen Kombination aus NutzungArt und
    # funktion. Zusätzlich wird gezählt, wie oft diese Kombination im GDF vorkommt.
    mapping_df = (
        gdf.groupby(["NutzungArt", "funktion"], dropna=False)
        .size()
        .reset_index(name="Anzahl - gdf")
        .rename(
            columns={
                "NutzungArt": "Gebäudetyp - gdf",
                "funktion": "Funktion - gdf",
            }
        )
    )

    mapping_df["npro_type"] = mapping_df.apply(
        lambda row: _resolve_npro_type(
            row["Gebäudetyp - gdf"],
            row["Funktion - gdf"],
        ),
        axis=1,
    )

    # Plausibilitätscheck: automatisch vergebene Werte müssen nPro-Typen sein.
    automatic_types = set(mapping_df["npro_type"]) - {UNDECIDED}
    invalid_types = automatic_types.difference(NPRO_TYPES)
    if invalid_types:
        raise ValueError(f"Ungültige nPro-Typen im Mapping: {sorted(invalid_types)}")

    # Gewünschte Spaltenreihenfolge.
    mapping_df = mapping_df[
        ["Gebäudetyp - gdf", "Funktion - gdf", "Anzahl - gdf", "npro_type"]
    ].reset_index(drop=True)

    # Excel-Ausgabe.
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_df.to_excel(excel_path, index=False)

    return mapping_df


if __name__ == "__main__":
    GPKG_PATH = DEFAULT_GPKG_PATH
    EXCEL_PATH = "npro_type_mapping.xlsx"

    df_mapping = create_npro_type_mapping(
        gpkg_path=GPKG_PATH,
        excel_path=EXCEL_PATH,
    )

    print(df_mapping.to_string(index=False))
    print(f"\nExcel-Datei geschrieben: {EXCEL_PATH}")
