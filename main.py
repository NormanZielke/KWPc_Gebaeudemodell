from check_dataframe import check_dataframe


# ==============================================================
# Einstellungen
# ==============================================================

path = (
    "1_Rohdaten/HN/HN-Gebäudemodell/"
    "HN-Gebäudemodell_04_08_2026/"
    "260728_Gebäudemodell_HohenNeuendorf.gpkg"
)

cols = [
    "GebaeudeID",
    "GebTyp",
    "NutzungArt",
    "P_th",
    "nutzflaeche_korr",
    "AnzlWhg",
    "Baualter_int",
    "funktion",
    "Waermebed_",
    "demand_kwh",
    "demand_2035",
    "demand_2045",
]


# ==============================================================
# Gebäudemodell prüfen
# ==============================================================

data = check_dataframe(
    path,
    cols
)


# ==============================================================
# DataFrames für Debug-Modus
# ==============================================================

gdf = data["gdf"]

gdf_check = data["gdf_check"]

gdf_nutzungart = data["gdf_nutzungart"]

gdf_funktion = data["gdf_funktion"]

gdf_wohnen = data["gdf_wohnen"]

gdf_nicht_wohnen = data["gdf_nicht_wohnen"]

gdf_mixed = data["gdf_mixed"]

gdf_both = data["gdf_both"]

gdf_neither = data["gdf_neither"]

gdf_either = data["gdf_either"]


# ==============================================================
# Beispiel: einzelne NutzungArt untersuchen
# ==============================================================

gdf_hotel = gdf_nicht_wohnen[
    gdf_nicht_wohnen["NutzungArt"] == "Hotel, Motel, Pension"
].copy()

gdf_buero = gdf_nicht_wohnen[
    gdf_nicht_wohnen["NutzungArt"] == "B�rogeb�ude"
].copy()

print("DEBUG")