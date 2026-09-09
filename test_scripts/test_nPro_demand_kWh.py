from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go


DEFAULT_TIME_COL = "Zeit (TT-MM hh:mm)"
DEFAULT_HEAT_COL = "Wärme gesamt (kW)"


def _load_profile(file_path, time_col, heat_col):
    """Liest ein nPro-Wärmelastprofil ein und bereitet es vor."""
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(
            f"Datei nicht gefunden:\n{file_path}"
        )

    df = pd.read_csv(file_path)

    required_cols = [time_col, heat_col]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        raise KeyError(
            f"In {file_path.name} fehlen folgende Spalten:\n"
            f"{missing_cols}\n\n"
            f"Vorhandene Spalten:\n{list(df.columns)}"
        )

    df[heat_col] = pd.to_numeric(
        df[heat_col],
        errors="coerce",
    )

    if df[heat_col].isna().any():
        raise ValueError(
            f"In {file_path.name} befinden sich nicht numerische "
            f"Werte in '{heat_col}'."
        )

    df["datetime"] = pd.to_datetime(
        "2025-" + df[time_col].astype(str),
        format="%Y-%d-%m %H:%M",
    )

    return df


def run_demand_test(
    files,
    output_dir,
    dt_hours=1.0,
    time_col=DEFAULT_TIME_COL,
    heat_col=DEFAULT_HEAT_COL,
    show_plot=True,
):
    """
    Vergleicht mehrere nPro-Lastprofile nach Normierung
    über den Jahreswärmebedarf.

    Normierung je Zeitschritt:

        heat_normalized[t]
            = P[t] * dt / E_year

    Damit gilt für jedes Profil:

        sum(heat_normalized) = 1

    Parameters
    ----------
    files : dict
        Mapping aus Anzeigename -> CSV-Pfad.
    output_dir : str | pathlib.Path
        Zielordner für CSV- und HTML-Ausgaben.
    dt_hours : float
        Dauer eines Zeitschritts in Stunden.
        Für stündliche Profile: 1.0.
    time_col : str
        Name der Zeitspalte.
    heat_col : str
        Name der Wärmeleistungsspalte [kW].
    show_plot : bool
        Wenn True, wird der interaktive Plot zusätzlich geöffnet.

    Returns
    -------
    dict
        Pfade der erzeugten Dateien sowie Vergleichsergebnisse.
    """
    if not files:
        raise ValueError("Es wurden keine Eingabedateien angegeben.")

    if dt_hours <= 0:
        raise ValueError("dt_hours muss größer als 0 sein.")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = {}

    print("\n" + "=" * 80)
    print("nPro-Test: Normierung über Jahreswärmebedarf")
    print("=" * 80)

    for name, file_path in files.items():
        df = _load_profile(
            file_path=file_path,
            time_col=time_col,
            heat_col=heat_col,
        )

        annual_demand_kwh = (
            df[heat_col] * dt_hours
        ).sum()

        if annual_demand_kwh <= 0:
            raise ValueError(
                f"Ungültiger Jahreswärmebedarf "
                f"in {Path(file_path).name}: "
                f"{annual_demand_kwh} kWh"
            )

        df["heat_normalized"] = (
            df[heat_col]
            * dt_hours
            / annual_demand_kwh
        )

        profiles[name] = {
            "df": df,
            "annual_demand_kwh": annual_demand_kwh,
        }

        print(f"\n{name}")
        print(f"  Datei: {Path(file_path).resolve()}")
        print(
            f"  Jahresbedarf aus CSV: "
            f"{annual_demand_kwh / 1000:.6f} MWh/a"
        )
        print(
            f"  Summe normiertes Profil: "
            f"{df['heat_normalized'].sum():.12f}"
        )

    _check_time_axes(
        profiles=profiles,
        time_col=time_col,
    )

    comparison_df = _compare_profiles(
        profiles=profiles,
        column="heat_normalized",
    )

    comparison_file = (
        output_dir
        / "Vergleich_normierte_Lastprofile_Jahresbedarf.csv"
    )
    comparison_df.to_csv(
        comparison_file,
        index=False,
    )

    reference_name = next(iter(profiles))
    reference_df = profiles[reference_name]["df"]

    normalized_profiles_df = pd.DataFrame({
        "datetime": reference_df["datetime"]
    })

    for name, profile in profiles.items():
        normalized_profiles_df[name] = (
            profile["df"]["heat_normalized"].to_numpy()
        )

    normalized_profiles_file = (
        output_dir
        / "Normierte_Lastprofile_Jahresbedarf.csv"
    )
    normalized_profiles_df.to_csv(
        normalized_profiles_file,
        index=False,
    )

    fig = go.Figure()

    for name, profile in profiles.items():
        df = profile["df"]

        fig.add_trace(
            go.Scatter(
                x=df["datetime"],
                y=df["heat_normalized"],
                mode="lines",
                name=name,
            )
        )

    fig.update_layout(
        title=(
            "Vergleich über Jahreswärmebedarf normierter "
            "nPro-Wärmelastprofile"
        ),
        xaxis_title="Zeit",
        yaxis_title=(
            "Anteil am Jahreswärmebedarf "
            "je Zeitschritt [-]"
        ),
        hovermode="x unified",
        template="plotly_white",
    )

    fig.update_xaxes(
        rangeslider_visible=True
    )

    interactive_file = (
        output_dir
        / "Vergleich_normierte_Lastprofile_"
          "Jahresbedarf_interaktiv.html"
    )
    fig.write_html(
        interactive_file
    )

    if show_plot:
        fig.show()

    print("\nErgebnisse Jahresbedarfs-Normierung:")
    print(f"  Vergleichstabelle:\n  {comparison_file}")
    print(f"  Normierte Profile:\n  {normalized_profiles_file}")
    print(f"  Interaktiver Plot:\n  {interactive_file}")

    return {
        "comparison_file": comparison_file,
        "normalized_profiles_file": normalized_profiles_file,
        "interactive_file": interactive_file,
        "comparison_df": comparison_df,
        "profiles": profiles,
    }


def _check_time_axes(profiles, time_col):
    reference_name = next(iter(profiles))
    reference_df = profiles[reference_name]["df"]

    for name, profile in profiles.items():
        df = profile["df"]

        if len(df) != len(reference_df):
            raise ValueError(
                f"Unterschiedliche Anzahl an Zeitschritten:\n"
                f"{reference_name}: {len(reference_df)}\n"
                f"{name}: {len(df)}"
            )

        if not df[time_col].equals(reference_df[time_col]):
            raise ValueError(
                f"Die Zeitachsen von '{reference_name}' "
                f"und '{name}' stimmen nicht überein."
            )


def _compare_profiles(profiles, column):
    profile_names = list(profiles.keys())
    comparison_results = []

    print("\n" + "-" * 80)
    print("Vergleich der normierten Profile")
    print("-" * 80)

    for i in range(len(profile_names)):
        for j in range(i + 1, len(profile_names)):
            name_1 = profile_names[i]
            name_2 = profile_names[j]

            values_1 = (
                profiles[name_1]["df"][column].to_numpy()
            )
            values_2 = (
                profiles[name_2]["df"][column].to_numpy()
            )

            difference = values_1 - values_2

            max_abs_difference = np.max(
                np.abs(difference)
            )
            mean_abs_difference = np.mean(
                np.abs(difference)
            )
            rmse = np.sqrt(
                np.mean(difference ** 2)
            )

            identical = np.allclose(
                values_1,
                values_2,
                rtol=1e-8,
                atol=1e-10,
            )

            comparison_results.append({
                "Profil 1": name_1,
                "Profil 2": name_2,
                "Max. absolute Abweichung":
                    max_abs_difference,
                "Mittlere absolute Abweichung":
                    mean_abs_difference,
                "RMSE": rmse,
                "Identisch": identical,
            })

            print(f"\n{name_1} vs. {name_2}")
            print(
                f"  Max. absolute Abweichung: "
                f"{max_abs_difference:.12e}"
            )
            print(
                f"  Mittlere absolute Abweichung: "
                f"{mean_abs_difference:.12e}"
            )
            print(
                f"  RMSE: {rmse:.12e}"
            )
            print(
                f"  Profile identisch: {identical}"
            )

    comparison_df = pd.DataFrame(
        comparison_results
    )

    if not comparison_df.empty:
        print("\n" + "-" * 80)

        if comparison_df["Identisch"].all():
            print(
                "ERGEBNIS: Alle über den Jahresbedarf normierten "
                "Profile sind innerhalb der Toleranz identisch."
            )
        else:
            print(
                "ERGEBNIS: Die über den Jahresbedarf normierten "
                "Profile sind nicht vollständig identisch."
            )

    return comparison_df


if __name__ == "__main__":
    raise SystemExit(
        "Dieses Skript ist als Testmodul gedacht. "
        "Bitte test_nPro.py im Projekt-Hauptverzeichnis starten."
    )
