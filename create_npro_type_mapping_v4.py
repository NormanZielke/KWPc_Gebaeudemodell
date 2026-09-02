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


# Bevorzugte Reihenfolge für die 10 Testgebäude.
# Wohnen und Gemischt werden bewusst ausgelassen.
# Parkhaus/Sonstiges stehen hinten, weil die anderen Typen für Wärmelastprofile
# fachlich aussagekräftiger sind.
TEST_TYPE_PRIORITY = [
    "Büro",
    "Schule",
    "Kindergarten",
    "Hotel",
    "Restaurant",
    "Produktion",
    "Lagerhalle",
    "Sporthalle",
    "Kirche",
    "Einzelhandel",
    "Einkaufszentrum",
    "Parkhaus",
    "Sonstiges",
]


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


def add_npro_columns(gdf):
    """Fügt n_pro_type und Volllaststunden zu einem GeoDataFrame hinzu.

    Das übergebene GeoDataFrame wird nicht in-place verändert. Stattdessen
    wird eine Kopie mit den beiden zusätzlichen Spalten zurückgegeben.

    Volllaststunden werden berechnet als::

        Waermebed_ / P_th

    Für fehlende/nicht numerische Werte oder P_th <= 0 wird NaN gesetzt.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Ausgangs-GDF mit mindestens NutzungArt, funktion, Waermebed_ und P_th.

    Returns
    -------
    geopandas.GeoDataFrame
        Kopie des GDF mit den zusätzlichen Spalten:
        - n_pro_type
        - Volllaststunden
    """
    required_columns = {"NutzungArt", "funktion", "Waermebed_", "P_th"}
    missing_columns = required_columns.difference(gdf.columns)
    if missing_columns:
        raise KeyError(
            "Folgende benötigte Spalten fehlen im GeoDataFrame: "
            f"{sorted(missing_columns)}"
        )

    result = gdf.copy()

    result["n_pro_type"] = [
        _resolve_npro_type(nutzungart, funktion)
        for nutzungart, funktion in zip(result["NutzungArt"], result["funktion"])
    ]

    waermebedarf = pd.to_numeric(result["Waermebed_"], errors="coerce")
    p_th = pd.to_numeric(result["P_th"], errors="coerce")

    # Division nur für fachlich/numerisch sinnvolle Werte.
    valid = waermebedarf.notna() & p_th.notna() & (waermebedarf >= 0) & (p_th > 0)
    result["Volllaststunden"] = pd.NA
    result.loc[valid, "Volllaststunden"] = waermebedarf.loc[valid] / p_th.loc[valid]
    result["Volllaststunden"] = pd.to_numeric(
        result["Volllaststunden"], errors="coerce"
    )

    return result


def load_gdf_with_npro_columns(gpkg_path, layer=None):
    """Lädt ein GeoPackage und ergänzt n_pro_type sowie Volllaststunden."""
    gpkg_path = Path(gpkg_path)

    if layer is None:
        gdf = gpd.read_file(gpkg_path)
    else:
        gdf = gpd.read_file(gpkg_path, layer=layer)

    return add_npro_columns(gdf)


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


def create_test_gpkg(
    gdf,
    output_path="Test.gpkg",
    n_buildings=10,
    layer_name="test_gebaeude",
):
    """Erstellt ein Test-GeoPackage mit möglichst diversen Nichtwohngebäuden.

    Auswahlregeln
    -------------
    - n_pro_type muss eindeutig automatisch zugeordnet sein.
    - 'Wohnen' und 'Gemischt' werden ausgeschlossen.
    - Volllaststunden müssen > 0 und <= 8760 h/a sein.
    - Es wird möglichst genau ein Gebäude je nPro-Typ ausgewählt.
    - Innerhalb eines nPro-Typs wird das Gebäude gewählt, dessen
      Volllaststunden dem Median des Typs am nächsten liegen.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GDF, idealerweise bereits mit add_npro_columns() ergänzt. Fehlen die
        beiden Spalten, werden sie automatisch ergänzt.
    output_path : str | pathlib.Path
        Zielpfad des Test-GeoPackages.
    n_buildings : int
        Gewünschte Anzahl Gebäude. Standard: 10.
    layer_name : str
        Name des Layers im Test-GeoPackage.

    Returns
    -------
    geopandas.GeoDataFrame
        Die ausgewählten Testgebäude, reduziert auf:
        - GebaeudeID
        - n_pro_type
        - P_th
        - Waermebed_
        - demand_kwh
        - nutzflaeche_korr
        - Volllaststunden
        - geometry
    """
    if n_buildings <= 0:
        raise ValueError("n_buildings muss größer als 0 sein.")

    if "n_pro_type" not in gdf.columns or "Volllaststunden" not in gdf.columns:
        gdf = add_npro_columns(gdf)
    else:
        gdf = gdf.copy()

    # Nur eindeutig zugeordnete, plausible Nichtwohngebäude.
    candidates = gdf[
        (~gdf["n_pro_type"].isin([UNDECIDED, "Wohnen", "Gemischt"]))
        & gdf["Volllaststunden"].notna()
        & (gdf["Volllaststunden"] > 0)
        & (gdf["Volllaststunden"] <= 8760)
    ].copy()

    if candidates.empty:
        raise ValueError("Keine geeigneten Gebäude für Test.gpkg gefunden.")

    selected_indices = []

    # Erst die fachlich bevorzugten, unterschiedlichen Typen auswählen.
    available_types = set(candidates["n_pro_type"].unique())
    ordered_types = [t for t in TEST_TYPE_PRIORITY if t in available_types]

    # Falls später weitere automatisch gemappte nPro-Typen hinzukommen,
    # werden sie nicht ignoriert, sondern hinten ergänzt.
    remaining_types = sorted(available_types.difference(ordered_types))
    ordered_types.extend(remaining_types)

    for npro_type in ordered_types:
        subset = candidates[candidates["n_pro_type"] == npro_type]
        if subset.empty:
            continue

        median_hours = subset["Volllaststunden"].median()
        idx = (subset["Volllaststunden"] - median_hours).abs().idxmin()
        selected_indices.append(idx)

        if len(selected_indices) == n_buildings:
            break

    # Falls weniger unterschiedliche Typen als gewünscht verfügbar sind,
    # mit weiteren geeigneten Gebäuden auffüllen.
    if len(selected_indices) < n_buildings:
        remaining = candidates.drop(index=selected_indices)
        additional_needed = n_buildings - len(selected_indices)
        selected_indices.extend(remaining.head(additional_needed).index.tolist())

    test_gdf = gdf.loc[selected_indices].copy().reset_index(drop=True)

    # Test-GeoPackage bewusst auf die für nPro bzw. unsere Prüfung
    # relevanten Spalten reduzieren. 'geometry' muss erhalten bleiben,
    # damit die Datei weiterhin ein räumliches GeoPackage ist.
    test_columns = [
        "GebaeudeID",
        "n_pro_type",
        "P_th",
        "Waermebed_",
        "demand_kwh",
        "nutzflaeche_korr",
        "Volllaststunden",
        "geometry",
    ]

    missing_test_columns = [col for col in test_columns if col not in test_gdf.columns]
    if missing_test_columns:
        raise KeyError(
            "Folgende für Test.gpkg benötigte Spalten fehlen im GeoDataFrame: "
            f"{missing_test_columns}"
        )

    test_gdf = test_gdf[test_columns].copy()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Bestehende Testdatei bewusst überschreiben.
    if output_path.exists():
        output_path.unlink()

    test_gdf.to_file(output_path, layer=layer_name, driver="GPKG")

    return test_gdf


if __name__ == "__main__":
    GPKG_PATH = DEFAULT_GPKG_PATH
    EXCEL_PATH = "npro_type_mapping.xlsx"
    TEST_GPKG_PATH = "Test.gpkg"

    # 1) Mapping-Tabelle + Excel erzeugen.
    df_mapping = create_npro_type_mapping(
        gpkg_path=GPKG_PATH,
        excel_path=EXCEL_PATH,
    )

    # 2) Ausgangs-GDF laden und die beiden neuen Spalten ergänzen.
    gdf = load_gdf_with_npro_columns(GPKG_PATH)

    # 3) Test.gpkg mit 10 möglichst unterschiedlichen Nichtwohngebäuden erzeugen.
    gdf_test = create_test_gpkg(
        gdf=gdf,
        output_path=TEST_GPKG_PATH,
        n_buildings=10,
    )

    print(df_mapping.to_string(index=False))
    print(f"\nExcel-Datei geschrieben: {EXCEL_PATH}")

    print("\nNeue Spalten im GeoDataFrame:")
    print(gdf[["NutzungArt", "funktion", "n_pro_type", "Volllaststunden"]].head())

    print(f"\nTest-GeoPackage geschrieben: {TEST_GPKG_PATH}")
    print("Ausgewählte nPro-Typen:")
    print(gdf_test["n_pro_type"].value_counts().to_string())
