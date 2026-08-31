from dataclasses import dataclass
import geopandas as gpd


@dataclass
class BuildingModelCheck:
    gdf: gpd.GeoDataFrame
    gdf_funktion: gpd.GeoDataFrame
    gdf_check: gpd.GeoDataFrame
    gdf_funktion_check: gpd.GeoDataFrame
    nutzungarten: object
    gdf_mixed: gpd.GeoDataFrame
    gdf_nicht_wohnen: gpd.GeoDataFrame
    Nutzungsarten_nicht_wohnen: object


def check_dataframe(path):

    gdf = gpd.read_file(path)

    gdf_funktion = gdf[
        gdf["funktion"].notna()
    ].copy()

    cols = [
        "GebaeudeID",
        "GebTyp",
        "NutzungArt",
        "Waermebed_",
        "P_th",
        "nutzflaeche_korr",
        "AnzlWhg",
    ]

    gdf_check = gdf[cols].copy()
    gdf_funktion_check = gdf_funktion[cols].copy()

    nutzungarten = gdf["NutzungArt"].unique()

    mixed_use = [
        "Gebäude für Handel und Dienstleistung mit Wohnen",
        "Gebäude für Gewerbe und Industrie mit Wohnen",
        "Wohngebäude mit Gewerbe und Industrie",
        "Wohngebäude mit Handel und Dienstleistungen",
        "Wohn- und Geschäftsgebäude",
        "Wohngebäude mit Gemeinbedarf",
    ]

    gdf_mixed = gdf[
        gdf["NutzungArt"].isin(mixed_use)
    ].copy()

    wohn_kategorien = [
        "Wohnhaus",
        "Wohngebäude",
        "Wohnheim",
        "Wochenendhaus",
        "Wohn- und Geschäftsgebäude",
        "Wohngebäude mit Gemeinbedarf",
        "Wohngebäude mit Gewerbe und Industrie",
        "Wohngebäude mit Handel und Dienstleistungen",
        "Gebäude für Gewerbe und Industrie mit Wohnen",
        "Gebäude für Handel und Dienstleistung mit Wohnen",
    ]

    gdf_nicht_wohnen = gdf[
        ~gdf["NutzungArt"].isin(wohn_kategorien)
    ].copy()

    Nutzungsarten_nicht_wohnen = gdf_nicht_wohnen["NutzungArt"].unique()

    return BuildingModelCheck(
        gdf=gdf,
        gdf_funktion=gdf_funktion,
        gdf_check=gdf_check,
        gdf_funktion_check=gdf_funktion_check,
        nutzungarten=nutzungarten,
        gdf_mixed=gdf_mixed,
        gdf_nicht_wohnen=gdf_nicht_wohnen,
        Nutzungsarten_nicht_wohnen = Nutzungsarten_nicht_wohnen,
    )


path = "1_Rohdaten/HN/HN-Gebäudemodell/HN-Gebäudemodell_04_08_2026/260728_Gebäudemodell_HohenNeuendorf.gpkg"

data = check_dataframe(path)

print("DEBUG")