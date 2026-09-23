from pathlib import Path

from gebaeudeauswertung import run_gebaeudeauswertung


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

    # ---------------------------------------------------------
    # Gebäudeauswertung der Rohdaten
    # ---------------------------------------------------------
    for category_cols in CATEGORY_VARIANTS:

        run_gebaeudeauswertung(
            gpkg_path=GPKG_PATH,
            category_cols=category_cols,
            output_dir=OUTPUT_DIR,
            layer=LAYER,
            demand_col=DEMAND_COL,
            thresholds=THRESHOLDS,
            recreate_mapping=RECREATE_MAPPING
        )