from pathlib import Path
from collections import defaultdict
from datetime import datetime

import geopandas as gpd
import pandas as pd
import numpy as np


# =============================================================
# Pfade
# =============================================================

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

OUTPUT_DIR = Path(
    "outputs/gebaeduemodell/Analyse"
)

OUTPUT_FILE = OUTPUT_DIR / "analyse_datenquellen.txt"


# =============================================================
# Layer
# =============================================================

HN_LAYER = "gebudemodell_final_28042026_saniert"
ALKIS_LAYER = "alkis_eg_hn"
WK_LAYER = "WK_EG_HN"


# =============================================================
# Bekannte Zuordnung WK -> Gebäudemodell
# =============================================================
#
# Einige Spalten wurden mit gleichem Namen übernommen,
# andere wurden im HN-Modell verkürzt.
#
# Key   = Spaltenname im HN-Gebäudemodell
# Value = Spaltenname im Wärmekataster
#

WK_COLUMN_MAPPING = {
    "GebaeudeID": "GebaeudeID",
    "StrName": "StrName",
    "Hausnummer": "Hausnummer",
    "Stadtteil": "Stadtteil",
    "PLZ": "PLZ",
    "Gemeinde": "Gemeinde",
    "AGS": "AGS",
    "Landkreis": "Landkreis",
    "Flur": "Flur",
    "Flurstueck": "Flurstueck",
    "Gemarkung": "Gemarkung",
    "BauAltKl": "BauAltKl",
    "GebTyp": "GebTyp",
    "NutzungArt": "NutzungArt",
    "AnzlWhg": "AnzlWhg",
    "SolarPot_k": "SolarPot_kwh_a",
    "Waermebed_": "Waermebed_kwh_a",
    "ETraeger1": "ETraeger1",
    "ETraeger2": "ETraeger2",
    "HzngTec1": "HzngTec1",
    "HzngTec2": "HzngTec2",
    "EndEVer_RW": "EndEVer_RW_kwh_a",
    "EndEVer_kw": "EndEVer_kwh_a",
    "CO2_RW_tco": "CO2_RW_tco2_a",
    "CO2_tco2_a": "CO2_tco2_a",
    "Datenquali": "Datenqualitaet",
    "gemeinde_n": "gemeinde_name",
}


# =============================================================
# Hilfsfunktionen
# =============================================================

def clean_missing(series):
    """
    Behandelt leere Strings zusätzlich als fehlende Werte.
    Die Originaldaten werden dabei nicht verändert.
    """

    if series.dtype == "object":
        return series.replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

    return series


def compare_series(left, right):
    """
    Vergleicht zwei Series möglichst robust.

    Numerische Werte werden auch dann numerisch verglichen,
    wenn eine Quelle z. B. '005' und die andere 5.0 enthält.

    Textwerte werden dagegen exakt verglichen.
    Encodingfehler wie 'Geb�ude' werden NICHT korrigiert.

    Returns
    -------
    matches : int
    total : int
    percent : float
    """

    left = left.copy()
    right = right.copy()

    both_na = (
        left.isna()
        & right.isna()
    )

    left_num = pd.to_numeric(
        left,
        errors="coerce"
    )

    right_num = pd.to_numeric(
        right,
        errors="coerce"
    )

    # Prüfen, ob beide Spalten vollständig als numerisch
    # interpretiert werden können.
    left_numeric_possible = (
        left.isna()
        | left_num.notna()
    ).all()

    right_numeric_possible = (
        right.isna()
        | right_num.notna()
    ).all()

    if (
        left_numeric_possible
        and right_numeric_possible
    ):

        equal = (
            both_na
            |
            (
                left_num.notna()
                & right_num.notna()
                & np.isclose(
                    left_num,
                    right_num,
                    rtol=1e-9,
                    atol=1e-6
                )
            )
        )

    else:

        left_string = (
            left
            .fillna("<NA>")
            .astype(str)
            .str.strip()
        )

        right_string = (
            right
            .fillna("<NA>")
            .astype(str)
            .str.strip()
        )

        equal = (
            left_string
            == right_string
        )

    total = len(equal)
    matches = int(equal.sum())

    percent = (
        matches / total * 100
        if total > 0
        else np.nan
    )

    return matches, total, percent


def normalized_geometry_key(geometry):
    """
    Erzeugt einen möglichst einheitlichen Geometrieschlüssel.

    normalize() vereinheitlicht unter anderem die Reihenfolge
    von Polygonringen. Dadurch können identische ALKIS-Geometrien
    auch dann erkannt werden, wenn die interne Reihenfolge
    unterschiedlich gespeichert wurde.
    """

    if geometry is None:
        return None

    try:
        geometry = geometry.normalize()
    except (AttributeError, NotImplementedError):
        pass

    return geometry.wkb


def add_section(report, title):
    """Fügt eine Überschrift zum Bericht hinzu."""

    report.append("")
    report.append("=" * 80)
    report.append(title)
    report.append("=" * 80)


def add_test_result(
    report,
    name,
    matches,
    total
):
    """Formatiert ein einfaches Testergebnis."""

    if total == 0:
        report.append(
            f"{name}: keine vergleichbaren Werte"
        )
        return

    percent = matches / total * 100

    report.append(
        f"{name}: "
        f"{matches:,} / {total:,} "
        f"({percent:.2f} %)"
    )


# =============================================================
# Hauptanalyse
# =============================================================

def analyse_data_sources():

    # ---------------------------------------------------------
    # Dateien einlesen
    # ---------------------------------------------------------

    print("Lese GeoPackages ein ...")

    hn = gpd.read_file(
        HN_PATH,
        layer=HN_LAYER
    )

    alkis = gpd.read_file(
        ALKIS_PATH,
        layer=ALKIS_LAYER
    )

    wk = gpd.read_file(
        WK_PATH,
        layer=WK_LAYER
    )

    report = []

    report.append(
        "Analyse der Datenquellen des HN-Gebäudemodells"
    )

    report.append(
        f"Erstellt: {datetime.now():%Y-%m-%d %H:%M:%S}"
    )

    report.append("")
    report.append(
        "Hinweis: Die Analyse verändert keine der drei Rohdateien."
    )

    report.append(
        "HN-only-Spalten werden nicht automatisch als vom "
        "Planungsbüro selbst erzeugt interpretiert. "
        "Sie können auch aus weiteren, hier nicht vorliegenden "
        "Datenquellen stammen."
    )

    # =========================================================
    # 1. Grunddaten
    # =========================================================

    add_section(
        report,
        "1. Übersicht der Datensätze"
    )

    datasets = [
        (
            "HN-Gebäudemodell",
            hn,
            HN_LAYER
        ),
        (
            "Wärmekataster",
            wk,
            WK_LAYER
        ),
        (
            "ALKIS",
            alkis,
            ALKIS_LAYER
        ),
    ]

    for name, gdf, layer in datasets:

        report.append("")
        report.append(name)
        report.append("-" * len(name))

        report.append(
            f"Layer: {layer}"
        )

        report.append(
            f"Objekte: {len(gdf):,}"
        )

        report.append(
            f"Spalten inkl. Geometrie: {len(gdf.columns)}"
        )

        report.append(
            f"Geometrietypen: "
            f"{', '.join(gdf.geom_type.dropna().unique())}"
        )

        report.append(
            f"CRS: {gdf.crs}"
        )

    # =========================================================
    # 2. Spalten der drei Datensätze
    # =========================================================

    add_section(
        report,
        "2. Spaltenschemata"
    )

    report.append("")
    report.append("HN-Gebäudemodell:")
    for col in hn.columns:
        report.append(
            f"  - {col}"
        )

    report.append("")
    report.append("Wärmekataster:")
    for col in wk.columns:
        report.append(
            f"  - {col}"
        )

    report.append("")
    report.append("ALKIS:")
    for col in alkis.columns:
        report.append(
            f"  - {col}"
        )

    # =========================================================
    # 3. Herkunft über NutzungArt / funktion
    # =========================================================

    add_section(
        report,
        "3. Einfache Quellenzuordnung im HN-Gebäudemodell"
    )

    nutzung = clean_missing(
        hn["NutzungArt"]
    )

    funktion = clean_missing(
        hn["funktion"]
    )

    mask_wk = (
        nutzung.notna()
        & funktion.isna()
    )

    mask_alkis = (
        nutzung.isna()
        & funktion.notna()
    )

    mask_both = (
        nutzung.notna()
        & funktion.notna()
    )

    mask_none = (
        nutzung.isna()
        & funktion.isna()
    )

    report.append(
        f"Gesamtzahl HN-Gebäude: {len(hn):,}"
    )

    report.append(
        f"NutzungArt belegt / funktion leer -> WK: "
        f"{mask_wk.sum():,}"
    )

    report.append(
        f"funktion belegt / NutzungArt leer -> ALKIS: "
        f"{mask_alkis.sum():,}"
    )

    report.append(
        f"Beide Spalten belegt: "
        f"{mask_both.sum():,}"
    )

    report.append(
        f"Beide Spalten leer: "
        f"{mask_none.sum():,}"
    )

    report.append("")
    report.append(
        "Interpretation:"
    )

    if (
        mask_both.sum() == 0
        and mask_none.sum() == 0
    ):
        report.append(
            "Die beiden Spalten sind im HN-Modell vollständig "
            "komplementär belegt."
        )

    # =========================================================
    # 4. Spaltenzuordnung WK
    # =========================================================

    add_section(
        report,
        "4. Spalten mit direkter Entsprechung im Wärmekataster"
    )

    for hn_col, wk_col in WK_COLUMN_MAPPING.items():

        status = []

        if hn_col in hn.columns:
            status.append("HN vorhanden")
        else:
            status.append("HN FEHLT")

        if wk_col in wk.columns:
            status.append("WK vorhanden")
        else:
            status.append("WK FEHLT")

        if hn_col == wk_col:
            relation = "gleicher Name"
        else:
            relation = "umbenannt/gekürzt"

        report.append(
            f"{hn_col:<20} <- "
            f"{wk_col:<25} "
            f"[{relation}; {', '.join(status)}]"
        )

    # =========================================================
    # 5. HN-Spalten ohne direkte Entsprechung
    # =========================================================

    add_section(
        report,
        "5. Spalten, die erst im HN-Gebäudemodell auftreten"
    )

    mapped_hn_columns = (
        set(WK_COLUMN_MAPPING.keys())
        | {"funktion"}
    )

    hn_only = sorted(
        set(hn.columns)
        - mapped_hn_columns
        - {"geometry"}
    )

    report.append(
        "Diese Spalten besitzen keine direkte Entsprechung "
        "in den beiden bereitgestellten Rohdatensätzen "
        "(WK bzw. ALKIS):"
    )

    report.append("")

    for col in hn_only:
        report.append(
            f"  - {col}"
        )

    report.append("")
    report.append(
        "Sie wurden daher entweder durch die Weiterverarbeitung "
        "erzeugt/berechnet oder aus einer weiteren Datenquelle "
        "ergänzt."
    )

    # =========================================================
    # 6. Nicht direkt übernommene WK-Spalten
    # =========================================================

    add_section(
        report,
        "6. WK-Spalten ohne direkte Zielspalte im HN-Modell"
    )

    mapped_wk_columns = set(
        WK_COLUMN_MAPPING.values()
    )

    wk_not_directly_transferred = sorted(
        set(wk.columns)
        - mapped_wk_columns
        - {"geometry"}
    )

    for col in wk_not_directly_transferred:
        report.append(
            f"  - {col}"
        )

    # =========================================================
    # 7. Nicht direkt übernommene ALKIS-Spalten
    # =========================================================

    add_section(
        report,
        "7. ALKIS-Spalten ohne direkte Zielspalte im HN-Modell"
    )

    alkis_not_directly_transferred = sorted(
        set(alkis.columns)
        - {"funktion", "geometry"}
    )

    for col in alkis_not_directly_transferred:
        report.append(
            f"  - {col}"
        )

    # =========================================================
    # 8. Prüfung WK über GebaeudeID
    # =========================================================

    add_section(
        report,
        "8. Prüfung der WK-Herkunft über GebaeudeID"
    )

    hn_wk = hn.loc[
        mask_wk
    ].copy()

    wk_ids = set(
        wk["GebaeudeID"].dropna()
    )

    hn_wk_ids = hn_wk[
        "GebaeudeID"
    ].dropna()

    id_matches = hn_wk_ids.isin(
        wk_ids
    ).sum()

    add_test_result(
        report,
        "HN-WK-Gebäude mit GebaeudeID im Wärmekataster",
        int(id_matches),
        len(hn_wk)
    )

    report.append(
        f"Eindeutige NutzungArt-Kategorien im HN-WK-Anteil: "
        f"{hn_wk['NutzungArt'].dropna().nunique()}"
    )

    report.append(
        f"Eindeutige NutzungArt-Kategorien im gesamten WK: "
        f"{wk['NutzungArt'].dropna().nunique()}"
    )

    # =========================================================
    # 9. Geometrieprüfung WK
    # =========================================================

    add_section(
        report,
        "9. Geometrieprüfung HN <-> Wärmekataster"
    )

    wk_geometry_lookup = (
        wk[
            [
                "GebaeudeID",
                "geometry"
            ]
        ]
        .dropna(
            subset=["GebaeudeID"]
        )
        .drop_duplicates(
            subset=["GebaeudeID"]
        )
        .set_index(
            "GebaeudeID"
        )
    )

    geometry_matches = 0
    geometry_total = 0

    for _, row in hn_wk.iterrows():

        building_id = row["GebaeudeID"]

        if pd.isna(building_id):
            continue

        if building_id not in wk_geometry_lookup.index:
            continue

        geometry_total += 1

        source_geometry = (
            wk_geometry_lookup.loc[
                building_id,
                "geometry"
            ]
        )

        if (
            row.geometry is not None
            and source_geometry is not None
            and row.geometry.equals(
                source_geometry
            )
        ):
            geometry_matches += 1

    add_test_result(
        report,
        "Topologisch gleiche Geometrie bei identischer GebaeudeID",
        geometry_matches,
        geometry_total
    )

    # =========================================================
    # 10. Inhaltlicher Vergleich WK-Spalten
    # =========================================================

    add_section(
        report,
        "10. Vergleich der WK-Attribute mit dem HN-Modell"
    )

    report.append(
        "Verglichen werden nur die HN-Gebäude, die über "
        "'NutzungArt' der Quelle WK zugeordnet wurden."
    )

    report.append(
        "Encodingprobleme werden dabei bewusst NICHT korrigiert."
    )

    report.append("")

    wk_lookup = (
        wk
        .dropna(
            subset=["GebaeudeID"]
        )
        .drop_duplicates(
            subset=["GebaeudeID"]
        )
        .set_index(
            "GebaeudeID"
        )
    )

    hn_wk_with_id = (
        hn_wk
        .dropna(
            subset=["GebaeudeID"]
        )
        .set_index(
            "GebaeudeID"
        )
    )

    common_ids = (
        hn_wk_with_id.index
        .intersection(
            wk_lookup.index
        )
    )

    for hn_col, wk_col in WK_COLUMN_MAPPING.items():

        if hn_col == "GebaeudeID":
            continue

        if (
            hn_col not in hn_wk_with_id.columns
            or wk_col not in wk_lookup.columns
        ):
            continue

        left = (
            hn_wk_with_id
            .loc[common_ids, hn_col]
        )

        right = (
            wk_lookup
            .loc[common_ids, wk_col]
        )

        matches, total, percent = (
            compare_series(
                left,
                right
            )
        )

        report.append(
            f"{hn_col:<20} <- "
            f"{wk_col:<25}: "
            f"{matches:>5,} / {total:<5,} "
            f"= {percent:6.2f} %"
        )

    # =========================================================
    # 11. Prüfung ALKIS über funktion
    # =========================================================

    add_section(
        report,
        "11. Prüfung der ALKIS-Herkunft über funktion"
    )

    hn_alkis = hn.loc[
        mask_alkis
    ].copy()

    hn_functions = set(
        hn_alkis[
            "funktion"
        ].dropna()
    )

    alkis_functions = set(
        alkis[
            "funktion"
        ].dropna()
    )

    functions_found = (
        hn_functions
        & alkis_functions
    )

    functions_missing = (
        hn_functions
        - alkis_functions
    )

    report.append(
        f"Eindeutige funktion-Kategorien im HN-ALKIS-Anteil: "
        f"{len(hn_functions)}"
    )

    report.append(
        f"Eindeutige funktion-Kategorien im gesamten ALKIS: "
        f"{len(alkis_functions)}"
    )

    add_test_result(
        report,
        "HN-funktion-Kategorien, die auch in ALKIS vorkommen",
        len(functions_found),
        len(hn_functions)
    )

    if functions_missing:

        report.append("")
        report.append(
            "HN-funktion-Werte ohne Entsprechung in ALKIS:"
        )

        for value in sorted(
            functions_missing
        ):
            report.append(
                f"  - {value}"
            )

    # =========================================================
    # 12. Geometrieprüfung ALKIS
    # =========================================================

    add_section(
        report,
        "12. Geometrieprüfung HN <-> ALKIS"
    )

    report.append(
        "Da HN und ALKIS keine gemeinsame Gebäude-ID besitzen, "
        "wird hier nur geprüft, ob eine geometrisch identische "
        "Gebäudegeometrie in ALKIS vorhanden ist."
    )

    geometry_to_functions = defaultdict(
        set
    )

    for geometry, function_value in zip(
        alkis.geometry,
        alkis["funktion"]
    ):

        if geometry is None:
            continue

        key = normalized_geometry_key(
            geometry
        )

        geometry_to_functions[
            key
        ].add(
            function_value
        )

    alkis_geometry_matches = 0
    alkis_function_matches = 0

    for geometry, function_value in zip(
        hn_alkis.geometry,
        hn_alkis["funktion"]
    ):

        if geometry is None:
            continue

        key = normalized_geometry_key(
            geometry
        )

        if key in geometry_to_functions:

            alkis_geometry_matches += 1

            if (
                function_value
                in geometry_to_functions[key]
            ):
                alkis_function_matches += 1

    add_test_result(
        report,
        "HN-ALKIS-Gebäude mit identischer ALKIS-Geometrie",
        alkis_geometry_matches,
        len(hn_alkis)
    )

    add_test_result(
        report,
        "Davon mit gleicher funktion",
        alkis_function_matches,
        alkis_geometry_matches
    )

    # =========================================================
    # 13. Prüfung: Etagen
    # =========================================================

    add_section(
        report,
        "13. Test berechneter Spalten"
    )

    report.append("")
    report.append(
        "13.1 Etagen = round(BruGeschFl_qm / GrundFl_qm)"
    )

    if (
        "Etagen" in hn.columns
        and "GrundFl_qm" in wk.columns
        and "BruGeschFl_qm" in wk.columns
    ):

        wk_area = (
            wk[
                [
                    "GebaeudeID",
                    "GrundFl_qm",
                    "BruGeschFl_qm"
                ]
            ]
            .drop_duplicates(
                subset=["GebaeudeID"]
            )
        )

        etagen_test = (
            hn_wk[
                [
                    "GebaeudeID",
                    "Etagen"
                ]
            ]
            .merge(
                wk_area,
                on="GebaeudeID",
                how="inner"
            )
        )

        ground_area = pd.to_numeric(
            etagen_test["GrundFl_qm"],
            errors="coerce"
        )

        gross_area = pd.to_numeric(
            etagen_test["BruGeschFl_qm"],
            errors="coerce"
        )

        etagen_original = pd.to_numeric(
            etagen_test["Etagen"],
            errors="coerce"
        )

        etagen_calculated = np.rint(
            gross_area / ground_area
        )

        valid = (
            etagen_original.notna()
            & etagen_calculated.notna()
            & np.isfinite(
                etagen_calculated
            )
        )

        matches = np.isclose(
            etagen_original[valid],
            etagen_calculated[valid],
            rtol=0,
            atol=0
        ).sum()

        add_test_result(
            report,
            "Übereinstimmung",
            int(matches),
            int(valid.sum())
        )

    # =========================================================
    # 14. Prüfung Bedarf_katatster
    # =========================================================

    report.append("")
    report.append(
        "13.2 Bedarf_katatster = Waermebed_"
    )

    if (
        "Bedarf_katatster" in hn.columns
        and "Waermebed_" in hn.columns
    ):

        a = pd.to_numeric(
            hn["Bedarf_katatster"],
            errors="coerce"
        )

        b = pd.to_numeric(
            hn["Waermebed_"],
            errors="coerce"
        )

        valid = (
            a.notna()
            & b.notna()
        )

        matches = np.isclose(
            a[valid],
            b[valid],
            rtol=1e-9,
            atol=1e-6
        ).sum()

        add_test_result(
            report,
            "Übereinstimmung",
            int(matches),
            int(valid.sum())
        )

    # =========================================================
    # 15. Prüfung demand_spec
    # =========================================================

    report.append("")
    report.append(
        "13.3 demand_spec = demand_kwh / nutzflaeche_korr"
    )

    required = {
        "demand_spec",
        "demand_kwh",
        "nutzflaeche_korr"
    }

    if required.issubset(
        hn.columns
    ):

        demand = pd.to_numeric(
            hn["demand_kwh"],
            errors="coerce"
        )

        area = pd.to_numeric(
            hn["nutzflaeche_korr"],
            errors="coerce"
        )

        demand_spec = pd.to_numeric(
            hn["demand_spec"],
            errors="coerce"
        )

        calculated = (
            demand / area
        )

        valid = (
            demand_spec.notna()
            & calculated.notna()
            & np.isfinite(
                calculated
            )
        )

        matches = np.isclose(
            demand_spec[valid],
            calculated[valid],
            rtol=1e-9,
            atol=1e-6
        ).sum()

        add_test_result(
            report,
            "Übereinstimmung",
            int(matches),
            int(valid.sum())
        )

    # =========================================================
    # 16. Prüfung demand_2045
    # =========================================================

    report.append("")
    report.append(
        "13.4 demand_2045 = "
        "demand_spec_san * nutzflaeche_korr"
    )

    required = {
        "demand_2045",
        "demand_spec_san",
        "nutzflaeche_korr"
    }

    if required.issubset(
        hn.columns
    ):

        demand_2045 = pd.to_numeric(
            hn["demand_2045"],
            errors="coerce"
        )

        demand_spec_san = pd.to_numeric(
            hn["demand_spec_san"],
            errors="coerce"
        )

        area = pd.to_numeric(
            hn["nutzflaeche_korr"],
            errors="coerce"
        )

        calculated = (
            demand_spec_san
            * area
        )

        valid = (
            demand_2045.notna()
            & calculated.notna()
        )

        matches = np.isclose(
            demand_2045[valid],
            calculated[valid],
            rtol=1e-9,
            atol=1e-6
        ).sum()

        add_test_result(
            report,
            "Übereinstimmung",
            int(matches),
            int(valid.sum())
        )

    # =========================================================
    # 17. Kurze Zusammenfassung
    # =========================================================

    add_section(
        report,
        "14. Zusammenfassung"
    )

    report.append(
        "Auf Basis der vorhandenen drei GeoPackages wird "
        "folgende Arbeitshypothese geprüft:"
    )

    report.append("")
    report.append(
        "  NutzungArt belegt -> Gebäude basiert auf Wärmekataster (WK)"
    )

    report.append(
        "  funktion belegt   -> Gebäude basiert auf ALKIS"
    )

    report.append("")
    report.append(
        "Spalten, die weder im bereitgestellten WK noch im "
        "bereitgestellten ALKIS vorkommen, sind als "
        "Weiterverarbeitung bzw. zusätzliche Quelle zu behandeln."
    )

    report.append(
        "Aus der bloßen Abwesenheit in WK/ALKIS kann jedoch nicht "
        "geschlossen werden, dass diese Information vom "
        "Planungsbüro selbst erzeugt wurde."
    )

    # =========================================================
    # Bericht speichern
    # =========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report_text = "\n".join(
        report
    )

    OUTPUT_FILE.write_text(
        report_text,
        encoding="utf-8"
    )

    # Gleiche Ausgabe auch im Terminal
    print("\n")
    print(report_text)

    print(
        "\n\nAnalyse gespeichert unter:"
    )

    print(
        OUTPUT_FILE
    )

    return report_text


# =============================================================
# Skript ausführen
# =============================================================

if __name__ == "__main__":

    analyse_data_sources()