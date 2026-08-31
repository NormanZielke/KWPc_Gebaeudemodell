from pathlib import Path

import pandas as pd


def normalize_heat_profile(file_path, peak_load_kw):
    """
    Normalisiert ein Wärme-Lastprofil anhand der Spitzenlast.

    Parameters
    ----------
    file_path : str | Path
        Pfad zur CSV-Datei mit dem Lastprofil.

    peak_load_kw : float
        Spitzenlast des Gebäudes in kW.

    Returns
    -------
    pd.DataFrame
        DataFrame mit der normierten Zeitreihe.
    """

    file_path = Path(file_path)

    heat_col = "Wärme gesamt (kW)"
    time_col = "Zeit (TT-MM hh:mm)"

    # --------------------------------------------------
    # Datei einlesen
    # --------------------------------------------------

    df = pd.read_csv(file_path)

    # --------------------------------------------------
    # Eingaben prüfen
    # --------------------------------------------------

    if heat_col not in df.columns:
        raise ValueError(
            f"Spalte '{heat_col}' wurde nicht gefunden."
        )

    if time_col not in df.columns:
        raise ValueError(
            f"Spalte '{time_col}' wurde nicht gefunden."
        )

    if peak_load_kw <= 0:
        raise ValueError(
            "Die Spitzenlast muss größer als 0 kW sein."
        )

    # --------------------------------------------------
    # Zeitreihe normalisieren
    # --------------------------------------------------

    df_normalized = pd.DataFrame({
        time_col: df[time_col],
        "Wärme gesamt normiert (-)": df[heat_col] / peak_load_kw
    })

    # --------------------------------------------------
    # Plausibilitätsprüfung
    # --------------------------------------------------

    max_normalized = df_normalized[
        "Wärme gesamt normiert (-)"
    ].max()

    print(f"Angegebene Spitzenlast: {peak_load_kw:.2f} kW")
    print(f"Maximalwert des Originalprofils: {df[heat_col].max():.2f} kW")
    print(f"Maximum des normierten Profils: {max_normalized:.4f}")

    # --------------------------------------------------
    # Ausgabepfad
    # --------------------------------------------------

    output_path = (
        file_path.parent
        / f"{file_path.stem}_normiert.csv"
    )

    # --------------------------------------------------
    # CSV speichern
    # --------------------------------------------------

    df_normalized.to_csv(
        output_path,
        index=False
    )

    print(f"Normiertes Lastprofil gespeichert unter:\n{output_path}")

    return df_normalized

data_path = Path("nPro/ID_25")
file_specific = data_path / "Hotel_225m2_42kW_26072kWh.csv"

df = normalize_heat_profile(file_specific,42)
