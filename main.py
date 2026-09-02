from pathlib import Path

from create_npro_type_mapping import create_npro_type_mapping
from gebaeudetypen_common import make_columns_tag
from gebaeudetypen_histogramm import plot_gebaeudetypen
from gebaeudetypen_tabelle import create_gebaeudetypen_table


# =============================================================
# ZENTRALE EINSTELLUNGEN
# =============================================================

GPKG_PATH = (
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "260728_Gebäudemodell_HohenNeuendorf.gpkg"
)

LAYER = (
    "gebudemodell_final_28042026_saniert"
)

DEMAND_COL = (
    "demand_kwh"
)


# =============================================================
# DIESE DREI VARIANTEN WERDEN AUTOMATISCH DURCHLAUFEN
# =============================================================

CATEGORY_VARIANTS = [
    ["GebTyp"],
    ["GebTyp", "funktion"],
    ["NutzungArt", "funktion"],
]


# =============================================================
# BASIS-OUTPUTORDNER
# =============================================================

OUTPUT_DIR = Path(
    "outputs/gebaeudemodell"
)


# =============================================================
# SCHWELLENWERTE
# =============================================================

THRESHOLDS = (
    0.90,
    0.95,
    0.98,
    0.99,
    1.00,
)


# =============================================================
# MAPPING-VERHALTEN
# =============================================================
#
# False:
#     Vorhandene Mapping-Dateien werden wiederverwendet.
#     Manuelle Änderungen an npro_type bleiben erhalten.
#
# True:
#     Mapping-Dateien werden neu erzeugt und überschrieben.
# =============================================================

RECREATE_MAPPING = False


def run_variant(
        category_cols
):
    """
    Führt Mapping, Diagramm und Tabelle für genau eine
    Spaltenvariante aus.
    """

    tag = make_columns_tag(
        category_cols
    )

    # ---------------------------------------------------------
    # Eigener Ordner pro Variante
    # ---------------------------------------------------------
    variant_output_dir = (
        OUTPUT_DIR / tag
    )

    variant_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    plot_output_dir = (
        variant_output_dir
        / "plots"
    )

    # ---------------------------------------------------------
    # Variable Dateinamen
    # ---------------------------------------------------------
    mapping_path = (
        variant_output_dir
        / f"npro_type_mapping_{tag}.xlsx"
    )

    table_output_path = (
        variant_output_dir
        / (
            "gebaeudetypen_auswertung_"
            f"kumuliert_{tag}.xlsx"
        )
    )

    print(
        "\n"
        "============================================================"
    )
    print(
        f"Variante: {tag}"
    )
    print(
        "============================================================"
    )
    print(
        f"Ausgewählte Spalten: {category_cols}"
    )
    print(
        f"Output-Ordner: {variant_output_dir}"
    )

    # ---------------------------------------------------------
    # 1. nPro-Mapping
    # ---------------------------------------------------------
    mapping_result = create_npro_type_mapping(
        gpkg_path=GPKG_PATH,
        category_cols=category_cols,
        excel_path=mapping_path,
        layer=LAYER,
        overwrite=RECREATE_MAPPING
    )

    # ---------------------------------------------------------
    # 2. Diagramm
    # ---------------------------------------------------------
    plot_result = plot_gebaeudetypen(
        path=GPKG_PATH,
        category_cols=category_cols,
        output_dir=plot_output_dir,
        layer=LAYER,
        demand_col=DEMAND_COL,
        thresholds=THRESHOLDS
    )

    # ---------------------------------------------------------
    # 3. Excel-Tabelle
    # ---------------------------------------------------------
    table_result = create_gebaeudetypen_table(
        path=GPKG_PATH,
        category_cols=category_cols,
        mapping_path=mapping_path,
        output_path=table_output_path,
        layer=LAYER,
        demand_col=DEMAND_COL,
        thresholds=THRESHOLDS
    )

    print(
        "\nVariante abgeschlossen:"
    )
    print(
        f"  {tag}"
    )
    print(
        f"  Mapping-Zeilen: {len(mapping_result)}"
    )
    print(
        f"  Diagramm-Gruppen: {len(plot_result)}"
    )
    print(
        f"  Tabellen-Zeilen: {len(table_result)}"
    )

    return {
        "tag": tag,
        "variant_output_dir": variant_output_dir,
        "mapping_path": mapping_path,
        "table_output_path": table_output_path,
        "plot_output_dir": plot_output_dir,
        "mapping_rows": len(mapping_result),
        "plot_rows": len(plot_result),
        "table_rows": len(table_result),
    }


def main():

    results = []

    print(
        "\n"
        "############################################################"
    )
    print(
        "Starte Gebäudetypen-Auswertung für alle Varianten"
    )
    print(
        "############################################################"
    )

    for category_cols in CATEGORY_VARIANTS:

        result = run_variant(
            category_cols
        )

        results.append(
            result
        )

    # ---------------------------------------------------------
    # Zusammenfassung
    # ---------------------------------------------------------
    print(
        "\n"
        "############################################################"
    )
    print(
        "Alle Varianten abgeschlossen"
    )
    print(
        "############################################################"
    )

    for result in results:

        print(
            f"\n{result['tag']}"
        )

        print(
            f"  Ordner:  "
            f"{result['variant_output_dir']}"
        )

        print(
            f"  Mapping: "
            f"{result['mapping_path']}"
        )

        print(
            f"  Tabelle: "
            f"{result['table_output_path']}"
        )

        print(
            f"  Plots:   "
            f"{result['plot_output_dir']}"
        )


if __name__ == "__main__":
    main()
