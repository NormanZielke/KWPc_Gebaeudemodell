from pathlib import Path

from gebaeudemodell_scripts.create_npro_type_mapping import create_npro_type_mapping
from gebaeudemodell_scripts.gebaeudetypen_common import make_columns_tag
from gebaeudemodell_scripts.gebaeudetypen_histogramm import plot_gebaeudetypen
from gebaeudemodell_scripts.gebaeudetypen_tabelle import create_gebaeudetypen_table

def run_gebaeudeauswertung(
        gpkg_path,
        category_cols,
        output_dir,
        layer=None,
        demand_col="demand_kwh",
        thresholds=(0.90, 0.95, 0.98, 0.99, 1.00),
        recreate_mapping=False
):
    """
    Führt die komplette Gebäudetypen-Auswertung für eine Variante aus.

    Ablauf:
        1. Varianten-Outputordner erzeugen
        2. nPro-Mapping erzeugen bzw. wiederverwenden
        3. Histogramm erzeugen
        4. kumulierte Excel-Tabelle erzeugen

    Parameters
    ----------
    gpkg_path : str | Path
        Pfad zum Gebäudemodell.

    category_cols : list[str]
        Spalten, die für die Gebäudetypen-Auswertung verwendet werden.

        Beispiele:
            ["GebTyp"]
            ["GebTyp", "funktion"]
            ["NutzungArt", "funktion"]

    output_dir : str | Path
        Basisordner der Auswertung.

    layer : str | None
        Layer des GeoPackages.

    demand_col : str
        Spalte mit dem Wärmebedarf.

    thresholds : tuple
        Schwellenwerte für den kumulierten Wärmebedarf.

    recreate_mapping : bool
        True:
            Mapping-Datei neu erzeugen.

        False:
            vorhandene Mapping-Datei wiederverwenden.

    Returns
    -------
    dict
        Informationen und Ergebnisse der Auswertung.
    """

    output_dir = Path(output_dir)

    # ---------------------------------------------------------
    # Variantenname erzeugen
    # ---------------------------------------------------------
    tag = make_columns_tag(
        category_cols
    )

    # ---------------------------------------------------------
    # Eigener Outputordner für die Variante
    # ---------------------------------------------------------
    variant_output_dir = (
        output_dir / tag
    )

    variant_output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    plot_output_dir = (
        variant_output_dir / "plots"
    )

    # ---------------------------------------------------------
    # Dateipfade
    # ---------------------------------------------------------
    mapping_path = (
        variant_output_dir
        / f"npro_type_mapping_{tag}.xlsx"
    )

    table_output_path = (
        variant_output_dir
        / f"gebaeudetypen_auswertung_kumuliert_{tag}.xlsx"
    )

    print(
        "\n"
        "============================================================"
    )
    print(
        f"Gebäudeauswertung: {tag}"
    )
    print(
        "============================================================"
    )

    print(
        f"Spalten: {category_cols}"
    )

    print(
        f"Output: {variant_output_dir}"
    )

    # ---------------------------------------------------------
    # 1. nPro-Mapping
    # ---------------------------------------------------------
    mapping_result = create_npro_type_mapping(
        gpkg_path=gpkg_path,
        category_cols=category_cols,
        excel_path=mapping_path,
        layer=layer,
        overwrite=recreate_mapping
    )

    # ---------------------------------------------------------
    # 2. Histogramm
    # ---------------------------------------------------------
    plot_result = plot_gebaeudetypen(
        path=gpkg_path,
        category_cols=category_cols,
        output_dir=plot_output_dir,
        layer=layer,
        demand_col=demand_col,
        thresholds=thresholds
    )

    # ---------------------------------------------------------
    # 3. Tabelle
    # ---------------------------------------------------------
    table_result = create_gebaeudetypen_table(
        path=gpkg_path,
        category_cols=category_cols,
        mapping_path=mapping_path,
        output_path=table_output_path,
        layer=layer,
        demand_col=demand_col,
        thresholds=thresholds
    )

    # ---------------------------------------------------------
    # Rückgabe
    # ---------------------------------------------------------
    return {
        "tag": tag,
        "output_dir": variant_output_dir,
        "mapping_path": mapping_path,
        "table_path": table_output_path,
        "plot_dir": plot_output_dir,
        "mapping_result": mapping_result,
        "plot_result": plot_result,
        "table_result": table_result,
    }

