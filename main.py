from pathlib import Path
import geopandas as gpd

from gebaeudeauswertung import run_gebaeudeauswertung
from gebaeudemodell_scripts.gebaeudedaten_aufbereitung import (
    prepare_gebaeudemodell,
    analyse_nutzungart_encoding,
)
from gebaeudemodell_scripts.gebaeudedaten_reduktion import (
    reduce_gebaeudemodell,
)

from test_scripts.test import check_prepared_geodataframe

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
    OUTPUT_DIR
    / "prepared"
    / "gebaeudemodell_prepared.gpkg"
)

PREPARED_OUTPUT_DIR = (
    OUTPUT_DIR
    / "prepared"
    / "auswertung"
)

ENCODING_MAPPING_PATH = (
    "gebaeudemodell_scripts/config/"
    "nutzungart_encoding.json"
)

# =============================================================
# AUSWERTUNGSVARIANTEN
# =============================================================

CATEGORY_VARIANTS = [
    ["GebTyp"],
    ["GebTyp", "funktion"],
    ["NutzungArt", "funktion"],
]

PREPARED_VARIANTS = [
    ["NutzungArt_und_funktion"],
]


REMOVE_CATEGORIES = [
    "Garage",
    "Schuppen",
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


# Vorhandene Mapping-Dateien überschreiben?
RECREATE_MAPPING = False


# =============================================================
# PROGRAMMABLAUF
# =============================================================

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
        encoding_mapping_path=ENCODING_MAPPING_PATH,
        layer=LAYER
    )

    # ---------------------------------------------------------
    # 3. Gebäudeauswertung der aufbereiteten Daten
    # ---------------------------------------------------------
    for category_cols in PREPARED_VARIANTS:
        run_gebaeudeauswertung(
            gpkg_path=PREPARED_GPKG_PATH,
            category_cols=category_cols,
            output_dir=PREPARED_OUTPUT_DIR,
            layer=LAYER,
            demand_col=DEMAND_COL,
            thresholds=THRESHOLDS,
            recreate_mapping=RECREATE_MAPPING
        )

    # ---------------------------------------------------------
    # 4. Vorbereitete Gebäudedaten reduzieren
    # ---------------------------------------------------------
    reduced_model = reduce_gebaeudemodell(
        input_path=PREPARED_GPKG_PATH,
        output_base_dir=PREPARED_OUTPUT_DIR,
        remove_categories=REMOVE_CATEGORIES,
        layer=LAYER,
        category_col="NutzungArt_und_funktion"
    )

    # ---------------------------------------------------------
    # 5. Gebäudeauswertung des reduzierten Datensatzes
    # ---------------------------------------------------------
    for category_cols in PREPARED_VARIANTS:
        run_gebaeudeauswertung(
            gpkg_path=reduced_model["gpkg_path"],
            category_cols=category_cols,
            output_dir=reduced_model["output_dir"],
            layer=LAYER,
            demand_col=DEMAND_COL,
            thresholds=THRESHOLDS,
            recreate_mapping=RECREATE_MAPPING
        )

    # ---------------------------------------------------------
    # DEBUG-TEST
    # ---------------------------------------------------------
    #gdf_test = check_prepared_geodataframe(
    #    gpkg_path=PREPARED_GPKG_PATH,
    #    layer=LAYER
    #)

    #print("Debug_Test")