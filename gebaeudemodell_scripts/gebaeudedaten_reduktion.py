from datetime import datetime
from pathlib import Path

import geopandas as gpd


def reduce_gebaeudemodell(
        input_path,
        output_base_dir,
        remove_categories,
        layer=None,
        category_col="NutzungArt_und_funktion"
):
    """
    Entfernt ausgewählte Gebäudekategorien aus einem GeoPackage
    und speichert den reduzierten Datensatz in einem eigenen,
    zeitgestempelten Verzeichnis.

    Zusätzlich wird eine Textdatei erzeugt, die dokumentiert,
    welche Kategorien entfernt wurden.

    Parameters
    ----------
    input_path : str | Path
        Pfad zum aufbereiteten GeoPackage.

    output_base_dir : str | Path
        Basisverzeichnis für den reduzierten Datensatz.

    remove_categories : list[str]
        Kategorien, die entfernt werden sollen.

    layer : str | None
        Layername des GeoPackages.

    category_col : str
        Spalte, anhand der gefiltert wird.

    Returns
    -------
    dict
        Enthält u. a.:
        - output_dir
        - gpkg_path
        - info_path
        - removed_count
        - remaining_count
    """

    input_path = Path(input_path)
    output_base_dir = Path(output_base_dir)

    # ---------------------------------------------------------
    # 1. Daten einlesen
    # ---------------------------------------------------------
    if layer is None:

        gdf = gpd.read_file(
            input_path
        )

    else:

        gdf = gpd.read_file(
            input_path,
            layer=layer
        )

    # ---------------------------------------------------------
    # 2. Spalte prüfen
    # ---------------------------------------------------------
    if category_col not in gdf.columns:

        raise KeyError(
            f"Spalte '{category_col}' "
            "nicht im Gebäudemodell gefunden."
        )

    # ---------------------------------------------------------
    # 3. Kategorien prüfen
    # ---------------------------------------------------------
    available_categories = set(
        gdf[category_col]
        .dropna()
        .unique()
    )

    missing_categories = [
        category
        for category in remove_categories
        if category not in available_categories
    ]

    if missing_categories:

        raise ValueError(
            "\nFolgende zu entfernende Kategorien "
            "wurden im Datensatz nicht gefunden:\n"
            + "\n".join(
                f"- {category}"
                for category in missing_categories
            )
        )

    # ---------------------------------------------------------
    # 4. Anzahl je zu entfernender Kategorie bestimmen
    # ---------------------------------------------------------
    removed_statistics = (
        gdf[
            gdf[category_col].isin(
                remove_categories
            )
        ][category_col]
        .value_counts()
    )

    # ---------------------------------------------------------
    # 5. Datensatz filtern
    # ---------------------------------------------------------
    remove_mask = (
        gdf[category_col]
        .isin(remove_categories)
    )

    gdf_reduced = (
        gdf.loc[
            ~remove_mask
        ]
        .copy()
    )

    removed_count = int(
        remove_mask.sum()
    )

    remaining_count = len(
        gdf_reduced
    )

    # ---------------------------------------------------------
    # 6. Zeitstempel erzeugen
    # ---------------------------------------------------------
    timestamp = datetime.now().strftime(
        "%H-%M-%S_%Y-%m-%d"
    )

    name = (
        f"gebaeudemodell_reduziert_{timestamp}"
    )

    output_dir = (
        output_base_dir / name
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=False
    )

    # ---------------------------------------------------------
    # 7. Outputpfade
    # ---------------------------------------------------------
    gpkg_path = (
        output_dir
        / f"{name}.gpkg"
    )

    info_path = (
        output_dir
        / f"{name}.txt"
    )

    # ---------------------------------------------------------
    # 8. Reduziertes GeoPackage speichern
    # ---------------------------------------------------------
    if layer is None:

        gdf_reduced.to_file(
            gpkg_path,
            driver="GPKG"
        )

    else:

        gdf_reduced.to_file(
            gpkg_path,
            layer=layer,
            driver="GPKG"
        )

    # ---------------------------------------------------------
    # 9. Dokumentation schreiben
    # ---------------------------------------------------------
    with open(
        info_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "Reduziertes Gebäudemodell\n"
        )

        file.write(
            "==========================\n\n"
        )

        file.write(
            f"Ausgangsdatensatz:\n"
            f"{input_path}\n\n"
        )

        file.write(
            f"Filterspalte:\n"
            f"{category_col}\n\n"
        )

        file.write(
            "Entfernte Kategorien:\n"
        )

        for category in remove_categories:

            count = int(
                removed_statistics.get(
                    category,
                    0
                )
            )

            file.write(
                f"- {category}: "
                f"{count} Gebäude\n"
            )

        file.write(
            "\n"
            f"Insgesamt entfernte Gebäude: "
            f"{removed_count}\n"
        )

        file.write(
            f"Verbleibende Gebäude: "
            f"{remaining_count}\n"
        )

    # ---------------------------------------------------------
    # 10. Terminal-Ausgabe
    # ---------------------------------------------------------
    print(
        "\n"
        "============================================================"
    )

    print(
        "Gebäudemodell reduziert"
    )

    print(
        "============================================================"
    )

    print(
        f"Entfernte Gebäude: "
        f"{removed_count}"
    )

    print(
        f"Verbleibende Gebäude: "
        f"{remaining_count}"
    )

    print(
        f"\nOutput:\n"
        f"{output_dir}"
    )

    # ---------------------------------------------------------
    # 11. Pfade zurückgeben
    # ---------------------------------------------------------
    return {
        "output_dir": output_dir,
        "gpkg_path": gpkg_path,
        "info_path": info_path,
        "removed_count": removed_count,
        "remaining_count": remaining_count,
    }