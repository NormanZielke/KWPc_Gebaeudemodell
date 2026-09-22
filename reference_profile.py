from pathlib import Path
import re

import numpy as np
import pandas as pd


TIME_COL = "Zeit (TT-MM hh:mm)"
POWER_COL = "Wärme gesamt (kW)"


FILENAME_PATTERN = re.compile(
    r"^Lastprofil_Waerme_"
    r"(?P<npro_type>.+?)_"
    r"(?P<area_m2>\d+(?:[.,]\d+)?)m2_"
    r"(?P<annual_demand_mwh>\d+(?:[.,]\d+)?)MWh_"
    r"(?P<peak_kw>\d+(?:[.,]\d+)?)kW"
    r"\.csv$"
)


def _to_float(value):
    return float(str(value).replace(",", "."))


def parse_npro_filename(file_path):
    """
    Extrahiert nPro-Typ, Fläche, Jahresbedarf und Peak
    aus dem Dateinamen.
    """
    file_path = Path(file_path)

    match = FILENAME_PATTERN.match(file_path.name)

    if match is None:
        raise ValueError(
            "Dateiname entspricht nicht dem erwarteten Muster:\n"
            f"{file_path.name}\n\n"
            "Erwartet wird z. B.:\n"
            "Lastprofil_Waerme_Einzelhandel_63m2_59MWh_39kW.csv"
        )

    metadata = match.groupdict()

    area_m2 = _to_float(metadata["area_m2"])
    annual_demand_mwh = _to_float(metadata["annual_demand_mwh"])
    peak_kw = _to_float(metadata["peak_kw"])

    return {
        "npro_type": metadata["npro_type"],
        "area_m2": area_m2,
        "annual_demand_mwh": annual_demand_mwh,
        "annual_demand_kwh": annual_demand_mwh * 1000,
        "peak_kw": peak_kw,
    }


def infer_dt_hours(df, time_col=TIME_COL):
    """
    Ermittelt die typische Zeitschrittweite aus der Zeitspalte.
    """
    if time_col not in df.columns:
        raise KeyError(f"Zeitspalte '{time_col}' fehlt.")

    datetime = pd.to_datetime(
        "2025-" + df[time_col].astype(str),
        format="%Y-%d-%m %H:%M",
        errors="raise",
    )

    if len(datetime) < 2:
        raise ValueError(
            "Für die Ermittlung der Zeitschrittweite "
            "werden mindestens zwei Zeitschritte benötigt."
        )

    differences = (
        datetime.diff().dropna().dt.total_seconds() / 3600
    )

    differences = differences[differences > 0]

    if differences.empty:
        raise ValueError(
            "Zeitschrittweite konnte nicht ermittelt werden."
        )

    dt_hours = float(differences.median())

    if dt_hours <= 0:
        raise ValueError(
            f"Ungültige Zeitschrittweite: {dt_hours} h"
        )

    regular = np.isclose(
        differences,
        dt_hours,
        rtol=1e-8,
        atol=1e-10,
    )

    if regular.mean() < 0.99:
        raise ValueError(
            "Die Zeitreihe ist nicht ausreichend äquidistant. "
            f"Ermittelte typische Zeitschrittweite: {dt_hours} h"
        )

    return dt_hours


def create_reference_profile(
    input_csv,
    output_csv,
    time_col=TIME_COL,
    power_col=POWER_COL,
):
    """
    Erstellt aus genau einem nPro-Lastprofil ein über den
    Jahreswärmebedarf normiertes Referenzprofil.

    profile_share[t] = P[t] * dt / E_year

    Damit gilt:
        sum(profile_share) = 1
    """
    input_csv = Path(input_csv).resolve()
    output_csv = Path(output_csv).resolve()

    metadata = parse_npro_filename(input_csv)

    df = pd.read_csv(input_csv)

    required_cols = [time_col, power_col]
    missing_cols = [
        col for col in required_cols
        if col not in df.columns
    ]

    if missing_cols:
        raise KeyError(
            f"In {input_csv.name} fehlen folgende Spalten:\n"
            f"{missing_cols}\n\n"
            f"Vorhandene Spalten:\n{list(df.columns)}"
        )

    df[power_col] = pd.to_numeric(
        df[power_col],
        errors="coerce",
    )

    if df[power_col].isna().any():
        raise ValueError(
            f"In {input_csv.name} enthält '{power_col}' "
            "nicht numerische oder fehlende Werte."
        )

    dt_hours = infer_dt_hours(
        df=df,
        time_col=time_col,
    )

    annual_energy_kwh = (
        df[power_col] * dt_hours
    ).sum()

    if annual_energy_kwh <= 0:
        raise ValueError(
            f"Jahreswärmebedarf ist <= 0 in:\n{input_csv}"
        )

    actual_peak_kw = df[power_col].max()

    profile_share = (
        df[power_col] * dt_hours / annual_energy_kwh
    )

    reference_df = pd.DataFrame({
        time_col: df[time_col],
        "profile_share": profile_share,
    })

    output_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    reference_df.to_csv(
        output_csv,
        index=False,
    )

    annual_filename_kwh = metadata["annual_demand_kwh"]
    peak_filename_kw = metadata["peak_kw"]

    annual_difference_kwh = (
        annual_energy_kwh - annual_filename_kwh
    )

    annual_difference_percent = (
        annual_difference_kwh
        / annual_filename_kwh
        * 100
        if annual_filename_kwh != 0
        else np.nan
    )

    peak_difference_kw = (
        actual_peak_kw - peak_filename_kw
    )

    peak_difference_percent = (
        peak_difference_kw
        / peak_filename_kw
        * 100
        if peak_filename_kw != 0
        else np.nan
    )

    return {
        "npro_type": metadata["npro_type"],
        "source_file": input_csv.name,
        "area_m2": metadata["area_m2"],
        "annual_demand_filename_mwh":
            metadata["annual_demand_mwh"],
        "annual_demand_timeseries_mwh":
            annual_energy_kwh / 1000,
        "annual_difference_percent":
            annual_difference_percent,
        "peak_filename_kw":
            peak_filename_kw,
        "peak_timeseries_kw":
            actual_peak_kw,
        "peak_difference_percent":
            peak_difference_percent,
        "dt_hours":
            dt_hours,
        "profile_share_sum":
            profile_share.sum(),
        "output_file":
            str(output_csv),
    }


def create_reference_profiles(
    input_dir,
    output_dir,
    time_col=TIME_COL,
    power_col=POWER_COL,
):
    """
    Erstellt automatisiert Referenzprofile aus allen passenden
    nPro-CSV-Dateien eines Ordners.

    Erwartetes Schema:
        Lastprofil_Waerme_<npro_type>_<flaeche>m2_
        <jahresbedarf>MWh_<peak>kW.csv

    Ausgabe je nPro-Typ:
        Referenzprofil_Waerme_<npro_type>.csv

    Zusätzlich:
        reference_profiles_summary.csv
    """
    input_dir = Path(input_dir).resolve()
    output_dir = Path(output_dir).resolve()

    if not input_dir.exists():
        raise FileNotFoundError(
            f"Input-Ordner nicht gefunden:\n{input_dir}"
        )

    if not input_dir.is_dir():
        raise NotADirectoryError(
            f"Input-Pfad ist kein Ordner:\n{input_dir}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_files = sorted(
        input_dir.glob("Lastprofil_Waerme_*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            "Im Input-Ordner wurden keine passenden "
            "nPro-CSV-Dateien gefunden:\n"
            f"{input_dir}"
        )

    print("\n" + "=" * 80)
    print("Erstellung nPro-Referenzprofile")
    print("=" * 80)
    print(f"\nInput-Ordner:\n{input_dir}")
    print(f"\nOutput-Ordner:\n{output_dir}")
    print(f"\nGefundene Profile: {len(csv_files)}")

    summary_rows = []
    seen_npro_types = {}

    for input_csv in csv_files:
        metadata = parse_npro_filename(input_csv)
        npro_type = metadata["npro_type"]

        if npro_type in seen_npro_types:
            raise ValueError(
                "Für denselben nPro-Typ wurden mehrere "
                "Beispielprofile gefunden.\n\n"
                f"nPro-Typ: {npro_type}\n"
                f"1. Datei: {seen_npro_types[npro_type]}\n"
                f"2. Datei: {input_csv.name}\n\n"
                "Für die automatische Erstellung wird aktuell "
                "genau ein Beispielprofil pro nPro-Typ erwartet."
            )

        seen_npro_types[npro_type] = input_csv.name

        output_csv = (
            output_dir
            / f"Referenzprofil_Waerme_{npro_type}.csv"
        )

        print("\n" + "-" * 80)
        print(f"nPro-Typ: {npro_type}")
        print(f"Input:\n{input_csv.name}")
        print(f"Output:\n{output_csv.name}")

        result = create_reference_profile(
            input_csv=input_csv,
            output_csv=output_csv,
            time_col=time_col,
            power_col=power_col,
        )

        summary_rows.append(result)

        print(f"  Fläche: {result['area_m2']:.2f} m²")
        print(
            f"  Jahresbedarf Dateiname: "
            f"{result['annual_demand_filename_mwh']:.3f} MWh/a"
        )
        print(
            f"  Jahresbedarf Zeitreihe: "
            f"{result['annual_demand_timeseries_mwh']:.3f} MWh/a"
        )
        print(
            f"  Peak Dateiname: "
            f"{result['peak_filename_kw']:.3f} kW"
        )
        print(
            f"  Peak Zeitreihe: "
            f"{result['peak_timeseries_kw']:.3f} kW"
        )
        print(
            f"  Zeitschrittweite: "
            f"{result['dt_hours']:.4f} h"
        )
        print(
            f"  Summe profile_share: "
            f"{result['profile_share_sum']:.12f}"
        )

    summary_df = pd.DataFrame(summary_rows)

    summary_file = (
        output_dir
        / "reference_profiles_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False,
    )

    print("\n" + "=" * 80)
    print(f"{len(summary_df)} Referenzprofile erstellt.")
    print(f"\nZusammenfassung:\n{summary_file}")
    print("=" * 80)

    return summary_df


if __name__ == "__main__":

    # =========================================================
    # HIER NUR DIE BEIDEN ORDNER ANGEBEN
    # =========================================================

    INPUT_DIR = (
        "nPro/reference_profile_inputs"
    )

    OUTPUT_DIR = (
        "outputs/reference_profiles"
    )

    create_reference_profiles(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
    )
