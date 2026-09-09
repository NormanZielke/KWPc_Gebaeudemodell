import pandas as pd


def create_annual_normalized_profile(
    input_csv,
    output_csv,
    power_col="Waermebedarf [kW]",
    dt_hours=1.0,
):
    """
    Erstellt aus einem nPro-Lastprofil ein auf den Jahresbedarf
    normiertes Referenzprofil.

    Summe von profile_share = 1.
    """

    df = pd.read_csv(input_csv)

    df[power_col] = pd.to_numeric(
        df[power_col],
        errors="raise"
    )

    # Jahresenergie der Referenzzeitreihe [kWh]
    annual_energy_kwh = (
        df[power_col] * dt_hours
    ).sum()

    # Anteil jedes Zeitschritts am Jahresbedarf
    df["profile_share"] = (
        df[power_col] * dt_hours
        / annual_energy_kwh
    )

    df.to_csv(
        output_csv,
        index=False
    )

    print(
        f"Referenz-Jahresbedarf: "
        f"{annual_energy_kwh:.2f} kWh/a"
    )

    print(
        f"Summe normiertes Profil: "
        f"{df['profile_share'].sum():.10f}"
    )

    return df