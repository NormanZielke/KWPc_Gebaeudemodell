from pathlib import Path

from gebaeudeauswertung import run_gebaeudeauswertung
from gebaeudemodell_scripts.gebaeudedaten_aufbereitung import prepare_gebaeudemodell

# =============================================================
# INPUT
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
# OUTPUT
# =============================================================

OUTPUT_DIR = Path(
    "outputs/gebaeudemodell"
)

PREPARED_GPKG_PATH = (
    "outputs/gebaeudemodell/"
    "prepared/"
    "gebaeudemodell_prepared.gpkg"
)

# =============================================================
# AUSWERTUNGSVARIANTEN
# =============================================================

CATEGORY_VARIANTS = [
    ["GebTyp"],
    ["GebTyp", "funktion"],
    ["NutzungArt", "funktion"],
]


# =============================================================
# PARAMETER
# =============================================================

THRESHOLDS = (
    0.90,
    0.95,
    0.98,
    0.99,
    1.00,
)


# Vorhandene Mapping-Dateien wiederverwenden
RECREATE_MAPPING = False


# =============================================================
# PROGRAMMABLAUF
# =============================================================

if __name__ == "__main__":

    if __name__ == "__main__":

        # ---------------------------------------------------------
        # 1. Gebäudeauswertung der Rohdaten
        # ---------------------------------------------------------
        for category_cols in CATEGORY_VARIANTS:
            run_gebaeudeauswertung(
                gpkg_path=GPKG_PATH,
                category_cols=category_cols,
                output_dir=OUTPUT_DIR / "raw",
                layer=LAYER,
                demand_col=DEMAND_COL,
                thresholds=THRESHOLDS,
                recreate_mapping=RECREATE_MAPPING
            )

        # ---------------------------------------------------------
        # 2. Gebäudedaten aufbereiten
        # ---------------------------------------------------------
        prepare_gebaeudemodell(
            input_path=GPKG_PATH,
            output_path=PREPARED_GPKG_PATH,
            layer=LAYER
        )