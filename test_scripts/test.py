import geopandas as gpd


def check_prepared_geodataframe(
        gpkg_path,
        layer=None
):
    """
    Liest das aufbereitete Gebäudemodell für einen manuellen
    Debug-Check ein.

    Der GeoDataFrame wird zurückgegeben, damit er z. B. in main.py
    im Debug-Modus als Variable untersucht werden kann.
    """

    # ---------------------------------------------------------
    # GeoPackage einlesen
    # ---------------------------------------------------------
    if layer is None:

        gdf = gpd.read_file(
            gpkg_path
        )

    else:

        gdf = gpd.read_file(
            gpkg_path,
            layer=layer
        )

    # ---------------------------------------------------------
    # Kurze Plausibilitätsprüfung
    # ---------------------------------------------------------
    check_cols = [
        "NutzungArt",
        "funktion",
        "Quelle",
        "NutzungArt_und_funktion"
    ]

    missing_cols = [
        col
        for col in check_cols
        if col not in gdf.columns
    ]

    if missing_cols:

        print(
            "\nFolgende erwartete Spalten fehlen:"
        )

        print(
            missing_cols
        )

    else:

        print(
            "\n"
            "============================================================"
        )

        print(
            "Test: aufbereitetes Gebäudemodell"
        )

        print(
            "============================================================"
        )

        print(
            gdf[
                check_cols
            ].head(20)
        )

        print(
            f"\nAnzahl Gebäude: {len(gdf)}"
        )

        print(
            "\nQuelle:"
        )

        print(
            gdf["Quelle"]
            .value_counts(
                dropna=False
            )
        )

    return gdf