from pathlib import Path
from collections import defaultdict
from datetime import datetime

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd


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
# Bekannte direkte Spaltenzuordnungen
# =============================================================

# Key   = Spaltenname im HN-Gebäudemodell
# Value = Spaltenname im Wärmekataster
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

# Direkte Attributentsprechungen zwischen HN und ALKIS.
# geometry wird separat behandelt.
ALKIS_COLUMN_MAPPING = {
    "funktion": "funktion",
}


# =============================================================
# Hilfsfunktionen
# =============================================================


def get_gpkg_schema(path, layer):
    """
    Liest das im GeoPackage deklarierte Feldschema aus.

    Returns
    -------
    properties : dict
        Attributspalten mit gespeichertem GeoPackage/Fiona-Datentyp.

    geometry_type : str
        Im GeoPackage deklarierter Geometrietyp.
    """
    with fiona.open(path, layer=layer) as src:
        properties = dict(src.schema["properties"])
        geometry_type = src.schema["geometry"]

    return properties, geometry_type


def check_schema_dtype_compatibility(gdf, schema):
    """
    Prüft, ob der von GeoPandas eingelesene dtype grundsätzlich
    zum im GeoPackage deklarierten Feldtyp passt.

    Hinweis:
    Ein Integerfeld kann in pandas als float64 erscheinen, wenn
    fehlende Werte (NaN) vorhanden sind. Das ist kein Datenfehler,
    solange alle vorhandenen Werte ganzzahlig sind.
    """

    results = []

    for col, declared_type in schema.items():

        if col not in gdf.columns:
            results.append({
                "Spalte": col,
                "GPKG-Typ": declared_type,
                "GeoPandas-dtype": "FEHLT",
                "Status": "Spalte fehlt"
            })
            continue

        series = gdf[col]
        pandas_dtype = str(series.dtype)

        status = "OK"

        if declared_type.startswith("str"):
            if not (
                series.dtype == "object"
                or pd.api.types.is_string_dtype(series)
            ):
                status = "ABWEICHUNG"

        elif declared_type.startswith("float"):
            if not pd.api.types.is_numeric_dtype(series):
                status = "ABWEICHUNG"

        elif declared_type.startswith("int"):
            if pd.api.types.is_integer_dtype(series):
                status = "OK"

            elif pd.api.types.is_float_dtype(series):
                non_null = series.dropna()

                if len(non_null) == 0:
                    status = (
                        "OK: float64 durch fehlende Werte möglich"
                    )
                elif np.all(
                    np.isclose(
                        non_null % 1,
                        0,
                        rtol=0,
                        atol=0
                    )
                ):
                    status = (
                        "OK: als float64 eingelesen wegen NaN; "
                        "vorhandene Werte sind ganzzahlig"
                    )
                else:
                    status = (
                        "ABWEICHUNG: Integerfeld enthält "
                        "nicht-ganzzahlige Werte"
                    )

            else:
                status = "ABWEICHUNG"

        results.append({
            "Spalte": col,
            "GPKG-Typ": declared_type,
            "GeoPandas-dtype": pandas_dtype,
            "Status": status
        })

    return pd.DataFrame(results)


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
    Vergleicht zwei Series elementweise möglichst robust.

    Vorgehen:
    - fehlend / fehlend -> gleich
    - wenn beide Einzelwerte numerisch interpretierbar sind:
      numerischer Vergleich
    - ansonsten:
      exakter Textvergleich

    Dadurch führen einzelne fehlerhaft formatierte Werte nicht mehr
    dazu, dass die gesamte Spalte als Text verglichen wird.

    Encodingfehler wie 'Geb�ude' werden bewusst NICHT korrigiert.

    Returns
    -------
    matches : int
        Anzahl identischer Werte.

    total : int
        Anzahl verglichener Werte.

    percent : float
        Prozentuale Übereinstimmung.

    numeric_unparseable : int
        Anzahl Fälle, bei denen nur eine der beiden Seiten numerisch
        interpretiert werden konnte.
    """

    left = left.reset_index(drop=True)
    right = right.reset_index(drop=True)

    matches = 0
    numeric_unparseable = 0

    for value_left, value_right in zip(left, right):

        # Beide Werte fehlen
        if (
            pd.isna(value_left)
            and pd.isna(value_right)
        ):
            matches += 1
            continue

        # Nur einer der beiden Werte fehlt
        if (
            pd.isna(value_left)
            or pd.isna(value_right)
        ):
            continue

        # Numerische Interpretation beider Einzelwerte versuchen
        left_num = pd.to_numeric(
            pd.Series([value_left]),
            errors="coerce"
        ).iloc[0]

        right_num = pd.to_numeric(
            pd.Series([value_right]),
            errors="coerce"
        ).iloc[0]

        # Beide Werte numerisch interpretierbar
        if (
            pd.notna(left_num)
            and pd.notna(right_num)
        ):
            if np.isclose(
                left_num,
                right_num,
                rtol=1e-9,
                atol=1e-6
            ):
                matches += 1

            continue

        # Nur eine Seite numerisch interpretierbar
        if (
            pd.notna(left_num)
            != pd.notna(right_num)
        ):
            numeric_unparseable += 1

        # Textvergleich
        if (
            str(value_left).strip()
            == str(value_right).strip()
        ):
            matches += 1

    total = len(left)

    percent = (
        matches / total * 100
        if total > 0
        else np.nan
    )

    return (
        matches,
        total,
        percent,
        numeric_unparseable
    )


def normalized_geometry_key(geometry):
    """
    Erzeugt einen möglichst einheitlichen Geometrieschlüssel.

    normalize() vereinheitlicht u. a. die interne Reihenfolge
    von Polygonringen. Dadurch können geometrisch identische
    Objekte zuverlässiger erkannt werden.
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

    # ---------------------------------------------------------
    # Grundlegende Spaltenprüfung
    # ---------------------------------------------------------

    required_hn = {
        "NutzungArt",
        "funktion"
    }

    missing_hn = required_hn.difference(
        hn.columns
    )

    if missing_hn:
        raise KeyError(
            "Im HN-Gebäudemodell fehlen benötigte Spalten: "
            f"{sorted(missing_hn)}"
        )

    if "GebaeudeID" not in wk.columns:
        raise KeyError(
            "Im Wärmekataster fehlt die Spalte 'GebaeudeID'."
        )

    if "NutzungArt" not in wk.columns:
        raise KeyError(
            "Im Wärmekataster fehlt die Spalte 'NutzungArt'."
        )

    if "funktion" not in alkis.columns:
        raise KeyError(
            "In ALKIS fehlt die Spalte 'funktion'."
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
            "Geometrietypen: "
            f"{', '.join(gdf.geom_type.dropna().unique())}"
        )

        report.append(
            f"CRS: {gdf.crs}"
        )

    # =========================================================
    # 2. Spaltenschemata und Datentypen
    # =========================================================

    add_section(
        report,
        "2. Spaltenschemata und Datentypen"
    )

    dataset_schema_info = [
        (
            "HN-Gebäudemodell",
            HN_PATH,
            HN_LAYER,
            hn
        ),
        (
            "Wärmekataster",
            WK_PATH,
            WK_LAYER,
            wk
        ),
        (
            "ALKIS",
            ALKIS_PATH,
            ALKIS_LAYER,
            alkis
        ),
    ]

    schema_cache = {}

    for name, path, layer, gdf in dataset_schema_info:

        schema, geometry_type = get_gpkg_schema(
            path,
            layer
        )

        schema_cache[name] = schema

        report.append("")
        report.append(name)
        report.append("-" * len(name))

        report.append(
            f"{'Spalte':<25}"
            f"{'GPKG-Typ':<18}"
            f"{'GeoPandas-dtype':<20}"
            f"{'Nicht leer':>12}"
            f"{'Fehlend':>12}"
        )

        report.append("-" * 87)

        for col in gdf.columns:

            if col == gdf.geometry.name:
                gpkg_type = (
                    f"geometry ({geometry_type})"
                )
            else:
                gpkg_type = schema.get(
                    col,
                    "nicht im Schema"
                )

            non_null = int(
                gdf[col].notna().sum()
            )

            missing = int(
                gdf[col].isna().sum()
            )

            report.append(
                f"{col:<25}"
                f"{gpkg_type:<18}"
                f"{str(gdf[col].dtype):<20}"
                f"{non_null:>12,}"
                f"{missing:>12,}"
            )

    # ---------------------------------------------------------
    # 2.1 Technische Datentypprüfung
    # ---------------------------------------------------------

    report.append("")
    report.append(
        "2.1 Prüfung: deklarierter GPKG-Typ "
        "vs. eingelesener GeoPandas-dtype"
    )
    report.append("-" * 75)

    for name, path, layer, gdf in dataset_schema_info:

        schema = schema_cache[name]

        type_check = check_schema_dtype_compatibility(
            gdf,
            schema
        )

        report.append("")
        report.append(name + ":")

        non_ok = type_check[
            ~type_check["Status"].eq("OK")
        ]

        if non_ok.empty:
            report.append(
                "  Keine technischen Datentyp-Auffälligkeiten."
            )
        else:
            for _, row in non_ok.iterrows():
                report.append(
                    f"  - {row['Spalte']}: "
                    f"GPKG={row['GPKG-Typ']}, "
                    f"GeoPandas={row['GeoPandas-dtype']} -> "
                    f"{row['Status']}"
                )

    # ---------------------------------------------------------
    # 2.2 Auffällige Typ-/Formatänderungen zwischen WK und HN
    # ---------------------------------------------------------

    report.append("")
    report.append(
        "2.2 Auffällige Typ- oder Formatänderungen "
        "zwischen Wärmekataster und HN-Modell"
    )
    report.append("-" * 75)

    hn_schema = schema_cache[
        "HN-Gebäudemodell"
    ]

    wk_schema = schema_cache[
        "Wärmekataster"
    ]

    differing_mapped_types = []

    for hn_col, wk_col in WK_COLUMN_MAPPING.items():

        if (
            hn_col in hn_schema
            and wk_col in wk_schema
            and hn_schema[hn_col] != wk_schema[wk_col]
        ):
            differing_mapped_types.append(
                (
                    hn_col,
                    hn_schema[hn_col],
                    wk_col,
                    wk_schema[wk_col]
                )
            )

    if differing_mapped_types:
        report.append(
            "Direkt zugeordnete Spalten mit unterschiedlichem "
            "gespeicherten Datentyp:"
        )

        for (
            hn_col,
            hn_type,
            wk_col,
            wk_type
        ) in differing_mapped_types:

            report.append(
                f"  - HN {hn_col} [{hn_type}] "
                f"<- WK {wk_col} [{wk_type}]"
            )

    # Flur: führende Nullen können durch String -> Float verloren gehen.
    if (
        "Flur" in hn.columns
        and "Flur" in wk.columns
    ):
        wk_flur = (
            wk["Flur"]
            .dropna()
            .astype(str)
        )

        leading_zero_count = int(
            wk_flur.str.match(
                r"^0+\d+$"
            ).sum()
        )

        report.append("")
        report.append(
            "Flur:"
        )
        report.append(
            "  WK speichert 'Flur' als Text, HN als float."
        )
        report.append(
            f"  WK-Werte mit führenden Nullen: "
            f"{leading_zero_count:,}."
        )

        examples = (
            wk_flur[
                wk_flur.str.match(
                    r"^0+\d+$"
                )
            ]
            .drop_duplicates()
            .head(10)
            .tolist()
        )

        if examples:
            report.append(
                "  Beispiele WK: "
                + ", ".join(examples)
            )
            report.append(
                "  Bei der Umwandlung zu float gehen "
                "führende Nullen verloren "
                "(z. B. '005' -> 5.0)."
            )

    # Für die folgenden Prüfungen nur WK-basierte HN-Gebäude
    # per GebaeudeID zusammenführen.
    hn_wk_for_format = hn.loc[
        (
            clean_missing(hn["NutzungArt"]).notna()
            & clean_missing(hn["funktion"]).isna()
        )
    ].copy()

    wk_format_columns = [
        col
        for col in [
            "GebaeudeID",
            "AnzlWhg",
            "Flurstueck",
            "Waermebed_kwh_a"
        ]
        if col in wk.columns
    ]

    hn_format_columns = [
        col
        for col in [
            "GebaeudeID",
            "AnzlWhg",
            "Flurstueck",
            "Waermebed_"
        ]
        if col in hn_wk_for_format.columns
    ]

    if (
        "GebaeudeID" in wk_format_columns
        and "GebaeudeID" in hn_format_columns
    ):

        format_compare = (
            hn_wk_for_format[
                hn_format_columns
            ]
            .merge(
                wk[
                    wk_format_columns
                ],
                on="GebaeudeID",
                how="left",
                suffixes=("_HN", "_WK")
            )
        )

        # AnzlWhg
        if (
            "AnzlWhg_HN" in format_compare.columns
            and "AnzlWhg_WK" in format_compare.columns
        ):
            left = (
                format_compare[
                    "AnzlWhg_HN"
                ]
                .fillna("<NA>")
                .astype(str)
            )

            right = (
                format_compare[
                    "AnzlWhg_WK"
                ]
                .fillna("<NA>")
                .astype(str)
            )

            diff = left != right

            report.append("")
            report.append("AnzlWhg:")
            report.append(
                f"  Abweichende WK/HN-Werte: "
                f"{int(diff.sum()):,}."
            )

            examples = (
                format_compare.loc[
                    diff,
                    [
                        "AnzlWhg_HN",
                        "AnzlWhg_WK"
                    ]
                ]
                .value_counts()
                .head(10)
            )

            for (
                hn_value,
                wk_value
            ), count in examples.items():
                report.append(
                    f"  - WK '{wk_value}' -> "
                    f"HN '{hn_value}': {count:,} Fälle"
                )

        # Flurstueck
        if (
            "Flurstueck_HN" in format_compare.columns
            and "Flurstueck_WK" in format_compare.columns
        ):
            left = (
                format_compare[
                    "Flurstueck_HN"
                ]
                .fillna("<NA>")
                .astype(str)
            )

            right = (
                format_compare[
                    "Flurstueck_WK"
                ]
                .fillna("<NA>")
                .astype(str)
            )

            diff = left != right

            report.append("")
            report.append("Flurstueck:")
            report.append(
                f"  Abweichende WK/HN-Werte: "
                f"{int(diff.sum()):,}."
            )

            examples = (
                format_compare.loc[
                    diff,
                    [
                        "Flurstueck_HN",
                        "Flurstueck_WK"
                    ]
                ]
                .value_counts()
                .head(10)
            )

            for (
                hn_value,
                wk_value
            ), count in examples.items():
                report.append(
                    f"  - WK '{wk_value}' -> "
                    f"HN '{hn_value}': {count:,} Fälle"
                )

        # Waermebed_
        if (
            "Waermebed_" in format_compare.columns
            and "Waermebed_kwh_a" in format_compare.columns
        ):
            hn_heat_text = (
                format_compare[
                    "Waermebed_"
                ]
                .astype("string")
                .str.strip()
            )

            hn_heat_numeric = pd.to_numeric(
                hn_heat_text,
                errors="coerce"
            )

            wk_heat_numeric = pd.to_numeric(
                format_compare[
                    "Waermebed_kwh_a"
                ],
                errors="coerce"
            )

            invalid_hn_heat = (
                hn_heat_text.notna()
                & hn_heat_numeric.isna()
            )

            report.append("")
            report.append("Waermebed_:")
            report.append(
                "  WK speichert Waermebed_kwh_a als float, "
                "HN speichert Waermebed_ als Text."
            )
            report.append(
                f"  HN-Werte, die nicht numerisch interpretierbar "
                f"sind: {int(invalid_hn_heat.sum()):,}."
            )

            invalid_examples = (
                hn_heat_text[
                    invalid_hn_heat
                ]
                .drop_duplicates()
                .head(10)
                .tolist()
            )

            for value in invalid_examples:
                report.append(
                    f"  - auffälliger HN-Wert: {value}"
                )

    report.append("")
    report.append(
        "Bewertung:"
    )
    report.append(
        "  Ein anderer pandas-dtype als der gespeicherte "
        "GPKG-Typ ist nicht automatisch ein Fehler."
    )
    report.append(
        "  Besonders bei Integerfeldern mit NULL-Werten kann "
        "GeoPandas/pandas float64 verwenden."
    )
    report.append(
        "  Inhaltlich auffälliger sind Formatänderungen, bei "
        "denen Informationen verloren gehen oder Werte offenbar "
        "als Datum interpretiert wurden."
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
        "NutzungArt belegt / funktion leer -> WK: "
        f"{mask_wk.sum():,}"
    )

    report.append(
        "funktion belegt / NutzungArt leer -> ALKIS: "
        f"{mask_alkis.sum():,}"
    )

    report.append(
        "Beide Spalten belegt: "
        f"{mask_both.sum():,}"
    )

    report.append(
        "Beide Spalten leer: "
        f"{mask_none.sum():,}"
    )

    report.append("")
    report.append("Interpretation:")

    if (
        mask_both.sum() == 0
        and mask_none.sum() == 0
    ):
        report.append(
            "Die beiden Spalten sind im HN-Modell vollständig "
            "komplementär belegt."
        )
    else:
        report.append(
            "Die beiden Spalten sind nicht vollständig "
            "komplementär belegt. Die abweichenden Fälle sollten "
            "separat geprüft werden."
        )

    # =========================================================
    # 4. Direkte Spaltenentsprechungen WK und ALKIS
    # =========================================================

    add_section(
        report,
        "4. Spalten mit direkter Entsprechung in den Quelldatensätzen"
    )

    # ---------------------------------------------------------
    # 4.1 Wärmekataster
    # ---------------------------------------------------------

    report.append("")
    report.append(
        "4.1 Direkte Entsprechungen zum Wärmekataster"
    )
    report.append("-" * 60)

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

    report.append(
        f"{'geometry':<20} <- "
        f"{'geometry':<25} "
        "[Geometrie in beiden Datensätzen vorhanden]"
    )

    # ---------------------------------------------------------
    # 4.2 ALKIS
    # ---------------------------------------------------------

    report.append("")
    report.append(
        "4.2 Direkte Entsprechungen zu ALKIS"
    )
    report.append("-" * 60)

    for hn_col, alkis_col in ALKIS_COLUMN_MAPPING.items():

        status = []

        if hn_col in hn.columns:
            status.append("HN vorhanden")
        else:
            status.append("HN FEHLT")

        if alkis_col in alkis.columns:
            status.append("ALKIS vorhanden")
        else:
            status.append("ALKIS FEHLT")

        if hn_col == alkis_col:
            relation = "gleicher Name"
        else:
            relation = "umbenannt"

        report.append(
            f"{hn_col:<20} <- "
            f"{alkis_col:<25} "
            f"[{relation}; {', '.join(status)}]"
        )

    report.append(
        f"{'geometry':<20} <- "
        f"{'geometry':<25} "
        "[Geometrie in beiden Datensätzen vorhanden]"
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
        | set(ALKIS_COLUMN_MAPPING.keys())
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

    mapped_alkis_columns = set(
        ALKIS_COLUMN_MAPPING.values()
    )

    alkis_not_directly_transferred = sorted(
        set(alkis.columns)
        - mapped_alkis_columns
        - {"geometry"}
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
        "Eindeutige NutzungArt-Kategorien im HN-WK-Anteil: "
        f"{hn_wk['NutzungArt'].dropna().nunique()}"
    )

    report.append(
        "Eindeutige NutzungArt-Kategorien im gesamten WK: "
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
        "Numerisch interpretierbare Einzelwerte werden numerisch "
        "verglichen. Einzelne fehlerhaft formatierte Werte führen "
        "nicht mehr dazu, dass eine gesamte Spalte als Text "
        "verglichen wird."
    )

    report.append(
        "Encodingprobleme werden bewusst NICHT korrigiert."
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

        (
            matches,
            total,
            percent,
            numeric_unparseable
        ) = compare_series(
            left,
            right
        )

        report.append(
            f"{hn_col:<20} <- "
            f"{wk_col:<25}: "
            f"{matches:>5,} / {total:<5,} "
            f"= {percent:6.2f} %"
        )

        if numeric_unparseable > 0:
            report.append(
                f"{'':<49}Hinweis: "
                f"{numeric_unparseable} Werte konnten nicht auf "
                "beiden Seiten numerisch interpretiert werden."
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
        "Eindeutige funktion-Kategorien im HN-ALKIS-Anteil: "
        f"{len(hn_functions)}"
    )

    report.append(
        "Eindeutige funktion-Kategorien im gesamten ALKIS: "
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
        "wird hier geprüft, ob eine geometrisch identische "
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
    # 13. Tests berechneter / weiterverarbeiteter Spalten
    # =========================================================

    add_section(
        report,
        "13. Tests berechneter bzw. weiterverarbeiteter Spalten"
    )

    # ---------------------------------------------------------
    # 13.1 Etagen
    # ---------------------------------------------------------

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
            .dropna(
                subset=["GebaeudeID"]
            )
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
            .dropna(
                subset=["GebaeudeID"]
            )
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

        calculated = np.rint(
            gross_area / ground_area
        )

        valid = (
            etagen_original.notna()
            & calculated.notna()
            & np.isfinite(
                calculated
            )
        )

        matches = np.isclose(
            etagen_original[valid],
            calculated[valid],
            rtol=0,
            atol=0
        ).sum()

        add_test_result(
            report,
            "Übereinstimmung",
            int(matches),
            int(valid.sum())
        )

    else:
        report.append(
            "Test nicht möglich: benötigte Spalten fehlen."
        )

    # ---------------------------------------------------------
    # 13.2 Bedarf_katatster
    # ---------------------------------------------------------

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

    else:
        report.append(
            "Test nicht möglich: benötigte Spalten fehlen."
        )

    # ---------------------------------------------------------
    # 13.3 demand_spec
    # ---------------------------------------------------------

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

    else:
        report.append(
            "Test nicht möglich: benötigte Spalten fehlen."
        )

    # ---------------------------------------------------------
    # 13.4 demand_2045
    # ---------------------------------------------------------

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
            & np.isfinite(
                calculated
            )
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

    else:
        report.append(
            "Test nicht möglich: benötigte Spalten fehlen."
        )

    # =========================================================
    # 14. Zusammenfassung
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
        "Weiterverarbeitung bzw. mögliche zusätzliche Quelle "
        "zu behandeln."
    )

    report.append(
        "Aus der bloßen Abwesenheit in WK/ALKIS kann nicht "
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

    # Gleiche Ausgabe zusätzlich im Terminal
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
