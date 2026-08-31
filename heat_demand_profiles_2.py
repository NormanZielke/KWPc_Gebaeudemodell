import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from pathlib import Path


def compare_heat_profiles(
        normalized_path,
        specific_path,
        peak_load_kw
):
    """
    Vergleicht eine normierte Wärme-Zeitreihe mit einer spezifischen
    Wärme-Zeitreihe.

    Die normierte Zeitreihe wird mit der Spitzenlast der spezifischen
    Zeitreihe multipliziert.

    Parameters
    ----------
    normalized_path : str | Path
        Pfad zur normierten Zeitreihe.

    specific_path : str | Path
        Pfad zur spezifischen Zeitreihe.

    peak_load_kw : float
        Spitzenlast der spezifischen Zeitreihe in kW.

    Returns
    -------
    pd.DataFrame
        DataFrame mit spezifischem Profil, skaliertem normierten Profil
        und deren Differenz.
    """

    # --------------------------------------------------
    # Pfade
    # --------------------------------------------------

    normalized_path = Path(normalized_path)
    specific_path = Path(specific_path)

    # Ausgabeordner im Ordner der spezifischen Zeitreihe
    plot_path = specific_path.parent / "plots"
    plot_path.mkdir(parents=True, exist_ok=True)


    # --------------------------------------------------
    # Dateien einlesen
    # --------------------------------------------------

    df_norm = pd.read_csv(normalized_path)
    df_spec = pd.read_csv(specific_path)


    # --------------------------------------------------
    # Relevante Spalten
    # --------------------------------------------------

    time_col = "Zeit (TT-MM hh:mm)"
    heat_col = "Wärme gesamt (kW)"


    # --------------------------------------------------
    # Eingaben prüfen
    # --------------------------------------------------

    if peak_load_kw <= 0:
        raise ValueError(
            "Die Spitzenlast muss größer als 0 kW sein."
        )

    for name, df in [
        ("normierte Zeitreihe", df_norm),
        ("spezifische Zeitreihe", df_spec)
    ]:
        if time_col not in df.columns:
            raise ValueError(
                f"Spalte '{time_col}' fehlt in der {name}."
            )

        if heat_col not in df.columns:
            raise ValueError(
                f"Spalte '{heat_col}' fehlt in der {name}."
            )


    # --------------------------------------------------
    # Zeitreihen prüfen
    # --------------------------------------------------

    if len(df_norm) != len(df_spec):
        raise ValueError(
            "Die beiden Lastprofile haben unterschiedlich viele Zeitschritte."
        )

    if not df_norm[time_col].equals(df_spec[time_col]):
        raise ValueError(
            "Die Zeitachsen der beiden Lastprofile stimmen nicht überein."
        )


    # --------------------------------------------------
    # Zeitachse erzeugen
    # --------------------------------------------------

    df_norm["datetime"] = pd.to_datetime(
        "2025-" + df_norm[time_col],
        format="%Y-%d-%m %H:%M"
    )

    df_spec["datetime"] = pd.to_datetime(
        "2025-" + df_spec[time_col],
        format="%Y-%d-%m %H:%M"
    )


    # --------------------------------------------------
    # Normierte Zeitreihe skalieren
    # --------------------------------------------------

    df_norm["heat_scaled_kw"] = (
        df_norm[heat_col] * peak_load_kw
    )


    # --------------------------------------------------
    # Gesamtwärmebedarf berechnen
    # --------------------------------------------------
    # Bei Stundenwerten:
    # kW * 1 h = kWh
    # Daher entspricht die Summe der Werte dem
    # Jahreswärmebedarf in kWh.

    heat_demand_norm_kwh = (
        df_norm["heat_scaled_kw"].sum()
    )

    heat_demand_spec_kwh = (
        df_spec[heat_col].sum()
    )

    difference_kwh = (
        heat_demand_spec_kwh
        - heat_demand_norm_kwh
    )

    relative_difference_percent = (
        difference_kwh
        / heat_demand_spec_kwh
        * 100
    )


    # --------------------------------------------------
    # Ergebnistext
    # --------------------------------------------------

    results_text = (
        f"Spitzenlast: {peak_load_kw:.2f} kW\n"
        f"\n"
        f"Gesamtwärmebedarf normiertes Profil "
        f"({peak_load_kw:g} kW): "
        f"{heat_demand_norm_kwh:,.1f} kWh\n"
        f"\n"
        f"Gesamtwärmebedarf spezifisches Profil: "
        f"{heat_demand_spec_kwh:,.1f} kWh\n"
        f"\n"
        f"Differenz: "
        f"{difference_kwh:,.1f} kWh\n"
        f"\n"
        f"Relative Abweichung: "
        f"{relative_difference_percent:.2f} %\n"
    )

    print(results_text)


    # --------------------------------------------------
    # Ergebnisse als TXT speichern
    # --------------------------------------------------

    results_file = (
        plot_path / "Auswertung_Lastprofile.txt"
    )

    with open(
        results_file,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(results_text)


    # --------------------------------------------------
    # Vergleichs-DataFrame
    # --------------------------------------------------

    df_compare = pd.DataFrame({
        "datetime": df_spec["datetime"],
        "specific_kw": df_spec[heat_col],
        "normalized_scaled_kw": df_norm["heat_scaled_kw"]
    })

    df_compare["difference_kw"] = (
        df_compare["specific_kw"]
        - df_compare["normalized_scaled_kw"]
    )


    # --------------------------------------------------
    # Plot 1: Vergleich
    # --------------------------------------------------

    plt.figure(figsize=(14, 6))

    plt.plot(
        df_compare["datetime"],
        df_compare["specific_kw"],
        label="Spezifisches Profil"
    )

    plt.plot(
        df_compare["datetime"],
        df_compare["normalized_scaled_kw"],
        label=f"Normiertes Profil × {peak_load_kw:g} kW",
        alpha=0.8
    )

    plt.xlabel("Zeit")
    plt.ylabel("Wärmeleistung [kW]")
    plt.title("Vergleich der Wärme-Lastprofile")

    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        plot_path / "Vergleich_Lastprofile.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()


    # --------------------------------------------------
    # Plot 2: Differenz
    # --------------------------------------------------

    plt.figure(figsize=(14, 5))

    plt.plot(
        df_compare["datetime"],
        df_compare["difference_kw"]
    )

    plt.axhline(
        y=0,
        linewidth=1
    )

    plt.xlabel("Zeit")
    plt.ylabel("Differenz [kW]")
    plt.title(
        "Differenz: spezifisches Profil "
        "- skaliertes normiertes Profil"
    )

    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        plot_path / "Differenz_Lastprofile.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()


    # --------------------------------------------------
    # Interaktiver Vergleichsplot
    # --------------------------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_compare["datetime"],
            y=df_compare["specific_kw"],
            mode="lines",
            name="Spezifisches Profil"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_compare["datetime"],
            y=df_compare["normalized_scaled_kw"],
            mode="lines",
            name=f"Normiertes Profil × {peak_load_kw:g} kW"
        )
    )

    fig.update_layout(
        title="Vergleich der Wärme-Lastprofile",
        xaxis_title="Zeit",
        yaxis_title="Wärmeleistung [kW]",
        hovermode="x unified",
        template="plotly_white"
    )

    fig.update_xaxes(
        rangeslider_visible=True
    )


    # --------------------------------------------------
    # Interaktiven Plot speichern
    # --------------------------------------------------

    interactive_file = (
        plot_path
        / "Vergleich_Lastprofile_interaktiv.html"
    )

    fig.write_html(interactive_file)

    fig.show()


    # --------------------------------------------------
    # Speicherorte ausgeben
    # --------------------------------------------------

    print(
        f"\nErgebnisse gespeichert unter:\n"
        f"{plot_path}"
    )


    # --------------------------------------------------
    # Vergleichs-DataFrame zurückgeben
    # --------------------------------------------------

    return df_compare

data_path = Path("nPro/ID_25")

file_normalized = data_path / "Hotel_1m2_1kW.csv"
file_specific = data_path / "Hotel_225m2_42kW_26072kWh.csv"

compare_heat_profiles(
    file_normalized,
    file_specific,
    42)