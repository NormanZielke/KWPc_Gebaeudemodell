import geopandas as gpd

file_path = "1_Rohdaten/HN/HN-Gebäudemodell/HN-Gebäudemodell_04_08_2026/260728_Gebäudemodell_HohenNeuendorf.gpkg"

HN_gdf = gpd.read_file(file_path)

HN_gdf_funktion = HN_gdf[HN_gdf["funktion"].notna()]

cols = [
    "GebaeudeID",
    "GebTyp",
    "NutzungArt",
    "Waermebed_",
    "P_th",
    "nutzflaeche_korr",
#    "Nutzung",
#    "funktion",
 #   "sector",
 #   "komm",
    "AnzlWhg"
]
HN_gdf_check = HN_gdf[cols]
HN_gdf_funktion_check = HN_gdf_funktion[cols]
#HN_gdf_nicht_wohnen = HN_gdf[HN_gdf["NutzungArt"] ]
list_GebTyp = HN_gdf.GebTyp.unique()
list_NutzungArt = HN_gdf.NutzungArt.unique()
print(list_NutzungArt)
print(len(list_NutzungArt))



mixed_use = [
    'Geb�ude f�r Handel und Dienstleistung mit Wohnen',
    'Geb�ude f�r Gewerbe und Industrie mit Wohnen',
    'Wohngeb�ude mit Gewerbe und Industrie',
    'Wohngeb�ude mit Handel und Dienstleistungen',
    'Wohn- und Gesch�ftsgeb�ude',
    'Wohngeb�ude mit Gemeinbedarf'
]

HN_gdf_mixed = HN_gdf[
    HN_gdf["NutzungArt"].isin(mixed_use)
].copy()

print(HN_gdf_mixed["NutzungArt"].unique())

HN_gdf_Hotel = HN_gdf_check.iloc[25,:]

HN_gdf_mixed = HN_gdf_mixed[cols]

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

HN_gdf_nicht_wohnen = HN_gdf[
    ~HN_gdf["NutzungArt"].isin(wohn_kategorien)
].copy()

print(len(HN_gdf_nicht_wohnen))

print(HN_gdf_check.head())
