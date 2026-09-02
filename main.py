from gebaeudetypen_histogramm import plot_gebaeudetypen
from gebaeudetypen_tabelle import create_gebaeudetypen_table


# -------------------------------------------------------------
# Zentrale Einstellungen
# -------------------------------------------------------------
GPKG_PATH = (
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "260728_Gebäudemodell_HohenNeuendorf.gpkg"
)

LAYER = "gebudemodell_final_28042026_saniert"

MAPPING_PATH = "outputs/gebaeudemodell/npro_type_mapping.xlsx"

PLOT_OUTPUT_DIR = "outputs/gebaeudemodell/plots"

TABLE_OUTPUT_PATH = (
    "outputs/gebaeudemodell/"
    "gebaeudetypen_auswertung_kumuliert.xlsx"
)

# Dieselben Schwellenwerte werden für Diagramm und Tabelle verwendet.
THRESHOLDS = (
    0.90,
    0.95,
    0.98,
    0.99,
    1
)


def main():

    # ---------------------------------------------------------
    # 1. Diagramm erstellen
    # ---------------------------------------------------------
    plot_result = plot_gebaeudetypen(
        path=GPKG_PATH,
        output_dir=PLOT_OUTPUT_DIR,
        layer=LAYER,
        demand_col="demand_kwh",
        nutzung_col="NutzungArt",
        funktion_col="funktion",
        thresholds=THRESHOLDS
    )

    # ---------------------------------------------------------
    # 2. Excel-Tabelle erstellen
    # ---------------------------------------------------------
    table_result = create_gebaeudetypen_table(
        path=GPKG_PATH,
        mapping_path=MAPPING_PATH,
        output_path=TABLE_OUTPUT_PATH,
        layer=LAYER,
        demand_col="demand_kwh",
        nutzung_col="NutzungArt",
        funktion_col="funktion",
        thresholds=THRESHOLDS
    )

    print("\nAuswertung abgeschlossen.")
    print(
        f"Gebäudetypen im Diagramm: "
        f"{len(plot_result)}"
    )
    print(
        f"Gebäudetypen in der Tabelle: "
        f"{len(table_result)}"
    )


if __name__ == "__main__":
    main()
