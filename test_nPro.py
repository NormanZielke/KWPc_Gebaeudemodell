import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go


# --------------------------------------------------
# Einstellungen
# --------------------------------------------------

DATA_PATH = Path("nPro/ID_1")

FILES = {
    "59 MWh / 39 kW": (
        DATA_PATH
        / "Lastprofile_Waerme_Einzelhandel_63m2_59MWh_39kW.csv"
    ),
    "100 MWh / 67 kW": (
        DATA_PATH
        / "Lastprofile_Waerme_Einzelhandel_63m2_100MWh_67kW.csv"
    ),
    "500 MWh / 334 kW": (
        DATA_PATH
        / "Lastprofile_Waerme_Einzelhandel_63m2_500MWh_334kW.csv"
    ),
}

# Peak-Werte aus den Dateinamen nur als Referenz
PEAK_FROM_FILENAME = {
    "59 MWh / 39 kW": 39,
    "100 MWh / 67 kW": 67,
    "500 MWh / 334 kW": 334,
}

TIME_COL = "Zeit (TT-MM hh:mm)"
HEAT_COL = "Wärme gesamt (kW)"

OUTPUT_PATH = Path("outputs/test_nPro")

OUTPUT_PATH.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Lastprofile einlesen und normieren
# --------------------------------------------------

profiles = {}

for name, file_path in FILES.items():

    if not file_path.exists():
        raise FileNotFoundError(
            f"Datei nicht gefunden:\n{file_path}"
        )

    df = pd.read_csv(file_path)

    required_cols = [
        TIME_COL,
        HEAT_COL,
    ]

    missing_cols = [
        col
        for col in required_cols
        if col not in df.columns
    ]

    if missing_cols:
        raise KeyError(
            f"In {file_path.name} fehlen folgende Spalten:\n"
            f"{missing_cols}"
        )

    # Wärmeleistung numerisch machen
    df[HEAT_COL] = pd.to_numeric(
        df[HEAT_COL],
        errors="coerce"
    )

    if df[HEAT_COL].isna().any():
        raise ValueError(
            f"In {file_path.name} befinden sich "
            f"nicht numerische Werte in '{HEAT_COL}'."
        )

    # Zeitachse erzeugen
    df["datetime"] = pd.to_datetime(
        "2025-" + df[TIME_COL],
        format="%Y-%d-%m %H:%M"
    )

    # Tatsächliche Peak-Last der Zeitreihe
    actual_peak_kw = df[HEAT_COL].max()

    if actual_peak_kw <= 0:
        raise ValueError(
            f"Ungültige Peak-Last in {file_path.name}: "
            f"{actual_peak_kw}"
        )

    # --------------------------------------------------
    # Normierung
    #
    # Maximum jedes Profils wird exakt 1
    # --------------------------------------------------

    df["heat_normalized"] = (
        df[HEAT_COL]
        / actual_peak_kw
    )

    profiles[name] = {
        "df": df,
        "actual_peak_kw": actual_peak_kw,
        "filename_peak_kw": PEAK_FROM_FILENAME[name],
    }


# --------------------------------------------------
# Zeitachsen prüfen
# --------------------------------------------------

reference_name = list(profiles.keys())[0]
reference_df = profiles[reference_name]["df"]

for name, profile in profiles.items():

    df = profile["df"]

    if len(df) != len(reference_df):
        raise ValueError(
            f"Unterschiedliche Anzahl an Zeitschritten:\n"
            f"{reference_name}: {len(reference_df)}\n"
            f"{name}: {len(df)}"
        )

    if not df[TIME_COL].equals(
        reference_df[TIME_COL]
    ):
        raise ValueError(
            f"Die Zeitachsen von '{reference_name}' "
            f"und '{name}' stimmen nicht überein."
        )


# --------------------------------------------------
# Peak-Werte ausgeben
# --------------------------------------------------

print("\n" + "=" * 70)
print("PEAK-LASTEN")
print("=" * 70)

for name, profile in profiles.items():

    actual = profile["actual_peak_kw"]
    filename_peak = profile["filename_peak_kw"]

    difference = actual - filename_peak

    print(
        f"\n{name}"
        f"\n  Peak laut Dateiname: {filename_peak:.3f} kW"
        f"\n  tatsächlicher Peak:  {actual:.6f} kW"
        f"\n  Differenz:            {difference:.6f} kW"
    )


# --------------------------------------------------
# Vergleich der normierten Profile
# --------------------------------------------------

profile_names = list(profiles.keys())

comparison_results = []

print("\n" + "=" * 70)
print("VERGLEICH DER NORMIERTEN PROFILE")
print("=" * 70)

for i in range(len(profile_names)):

    for j in range(
        i + 1,
        len(profile_names)
    ):

        name_1 = profile_names[i]
        name_2 = profile_names[j]

        values_1 = profiles[
            name_1
        ]["df"]["heat_normalized"].to_numpy()

        values_2 = profiles[
            name_2
        ]["df"]["heat_normalized"].to_numpy()

        difference = (
            values_1
            - values_2
        )

        max_abs_difference = (
            np.max(
                np.abs(difference)
            )
        )

        mean_abs_difference = (
            np.mean(
                np.abs(difference)
            )
        )

        rmse = np.sqrt(
            np.mean(
                difference ** 2
            )
        )

        identical = np.allclose(
            values_1,
            values_2,
            rtol=1e-8,
            atol=1e-10
        )

        comparison_results.append({
            "Profil 1": name_1,
            "Profil 2": name_2,
            "Max. absolute Abweichung":
                max_abs_difference,
            "Mittlere absolute Abweichung":
                mean_abs_difference,
            "RMSE":
                rmse,
            "Identisch":
                identical,
        })

        print(
            f"\n{name_1}"
            f"\nvs."
            f"\n{name_2}"
        )

        print(
            f"  Max. absolute Abweichung: "
            f"{max_abs_difference:.12f}"
        )

        print(
            f"  Mittlere absolute Abweichung: "
            f"{mean_abs_difference:.12f}"
        )

        print(
            f"  RMSE: "
            f"{rmse:.12f}"
        )

        print(
            f"  Profile identisch: "
            f"{identical}"
        )


# --------------------------------------------------
# Gesamtergebnis
# --------------------------------------------------

comparison_df = pd.DataFrame(
    comparison_results
)

all_identical = (
    comparison_df["Identisch"].all()
)

print("\n" + "=" * 70)

if all_identical:

    print(
        "ERGEBNIS: Alle drei normierten Profile "
        "sind identisch."
    )

    print(
        "Der angegebene Jahreswärmebedarf verändert "
        "damit in diesem Test NICHT die Form "
        "des Lastprofils."
    )

else:

    print(
        "ERGEBNIS: Die normierten Profile "
        "sind NICHT identisch."
    )

    print(
        "Der Jahreswärmebedarf und/oder ein anderer "
        "nPro-Parameter beeinflusst damit die "
        "Form des erzeugten Lastprofils."
    )

print("=" * 70)


# --------------------------------------------------
# Vergleichsergebnisse speichern
# --------------------------------------------------

comparison_file = (
    OUTPUT_PATH
    / "Vergleich_normierte_Lastprofile.csv"
)

comparison_df.to_csv(
    comparison_file,
    index=False
)


# --------------------------------------------------
# Interaktiver Plot
# --------------------------------------------------

fig = go.Figure()

for name, profile in profiles.items():

    df = profile["df"]

    fig.add_trace(
        go.Scatter(
            x=df["datetime"],
            y=df["heat_normalized"],
            mode="lines",
            name=name
        )
    )


fig.update_layout(
    title=(
         "Vergleich normierter nPro-Wärmelastprofile – Einzelhandel, 63 m²"
        "<br>"
        "Jahreswärmebedarf jeweils vorgegeben: 59 MWh/a, 100 MWh/a und 500 MWh/a"
    ),
    xaxis_title="Zeit",
    yaxis_title="Normierte Wärmeleistung [-]",
    hovermode="x unified",
    template="plotly_white",
)


# --------------------------------------------------
# Zoom / Navigationsleiste
# --------------------------------------------------

fig.update_xaxes(
    rangeslider_visible=True
)


# --------------------------------------------------
# HTML speichern
# --------------------------------------------------

interactive_file = (
    OUTPUT_PATH
    / "Vergleich_normierte_Lastprofile_interaktiv.html"
)

fig.write_html(
    interactive_file
)


# --------------------------------------------------
# Plot anzeigen
# --------------------------------------------------

fig.show()


# --------------------------------------------------
# Speicherorte ausgeben
# --------------------------------------------------

print(
    "\nErgebnisse gespeichert unter:"
)

print(
    f"  Vergleichstabelle:\n"
    f"  {comparison_file}"
)

print(
    f"\n  Interaktiver Plot:\n"
    f"  {interactive_file}"
)