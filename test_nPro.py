from pathlib import Path

from test_scripts.test_nPro_peak import run_peak_test
from test_scripts.test_nPro_demand_kWh import run_demand_test


# =============================================================
# HIER DIE INPUT-PFADE EINSTELLEN
# =============================================================

# test_nPro.py liegt direkt im Projekt-Hauptverzeichnis.
PROJECT_ROOT = Path(__file__).resolve().parent


FILES = {
    "59 MWh / 39 kW": (
        PROJECT_ROOT
        / "nPro"
        / "ID_1"
        / "Lastprofile_Waerme_Einzelhandel_63m2_59MWh_39kW.csv"
    ),

    "100 MWh / 67 kW": (
        PROJECT_ROOT
        / "nPro"
        / "ID_1"
        / "Lastprofile_Waerme_Einzelhandel_63m2_100MWh_67kW.csv"
    ),

    "500 MWh / 334 kW": (
        PROJECT_ROOT
        / "nPro"
        / "ID_1"
        / "Lastprofile_Waerme_Einzelhandel_63m2_500MWh_334kW.csv"
    ),
}


# Optional: Peaks aus den Dateinamen nur zur Kontrolle.
# Die Peak-Normierung selbst verwendet immer das tatsächliche Maximum
# der jeweiligen CSV-Zeitreihe.
PEAK_FROM_FILENAME = {
    "59 MWh / 39 kW": 39,
    "100 MWh / 67 kW": 67,
    "500 MWh / 334 kW": 334,
}


TIME_COL = "Zeit (TT-MM hh:mm)"
HEAT_COL = "Wärme gesamt (kW)"

# Stündliche Profile
DT_HOURS = 1.0


# =============================================================
# OUTPUT
# =============================================================

OUTPUT_ROOT = (
    PROJECT_ROOT
    / "outputs"
    / "test_nPro"
)

OUTPUT_PEAK = (
    OUTPUT_ROOT
    / "peak"
)

OUTPUT_DEMAND = (
    OUTPUT_ROOT
    / "demand_kWh"
)


# HTML wird unabhängig davon gespeichert.
# True öffnet den Plot zusätzlich im Browser / Plotly-Renderer.
SHOW_PLOTS = True


# =============================================================
# Hilfsfunktionen
# =============================================================

def check_input_files():
    """Prüft alle Eingabedateien vor dem Start."""

    missing_files = []

    print("\n" + "=" * 80)
    print("EINGABEDATEIEN")
    print("=" * 80)

    for name, file_path in FILES.items():
        file_path = Path(file_path).resolve()

        print(f"\n{name}")
        print(f"  {file_path}")

        if file_path.exists():
            print("  -> gefunden")
        else:
            print("  -> NICHT GEFUNDEN")
            missing_files.append(file_path)

    if missing_files:
        missing_text = "\n".join(
            f"  - {file_path}"
            for file_path in missing_files
        )

        raise FileNotFoundError(
            "\nFolgende Eingabedateien fehlen:\n"
            f"{missing_text}"
        )


def check_created_files(result, test_name):
    """
    Prüft nach einem Test explizit, ob die erwarteten Dateien
    tatsächlich geschrieben wurden.
    """

    expected_keys = [
        "comparison_file",
        "normalized_profiles_file",
        "interactive_file",
    ]

    missing = []

    for key in expected_keys:
        file_path = Path(result[key]).resolve()

        if not file_path.exists():
            missing.append(file_path)

    if missing:
        missing_text = "\n".join(
            f"  - {file_path}"
            for file_path in missing
        )

        raise AssertionError(
            f"{test_name}: Folgende Ausgabedateien "
            f"wurden nicht erzeugt:\n{missing_text}"
        )


# =============================================================
# Pytest-Test 1
#
# Weil die Datei "test_nPro.py" heißt, startet PyCharm sie bei dir
# als pytest-Datei. Diese Funktion wird deshalb von pytest erkannt.
# =============================================================

def test_peak_normierung():

    check_input_files()

    OUTPUT_PEAK.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = run_peak_test(
        files=FILES,
        output_dir=OUTPUT_PEAK,
        peak_from_filename=PEAK_FROM_FILENAME,
        time_col=TIME_COL,
        heat_col=HEAT_COL,
        show_plot=SHOW_PLOTS,
    )

    check_created_files(
        result=result,
        test_name="Peak-Normierung",
    )


# =============================================================
# Pytest-Test 2
# =============================================================

def test_jahresbedarf_normierung():

    check_input_files()

    OUTPUT_DEMAND.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = run_demand_test(
        files=FILES,
        output_dir=OUTPUT_DEMAND,
        dt_hours=DT_HOURS,
        time_col=TIME_COL,
        heat_col=HEAT_COL,
        show_plot=SHOW_PLOTS,
    )

    check_created_files(
        result=result,
        test_name="Jahresbedarfs-Normierung",
    )


# =============================================================
# Optional: normales Starten als Python-Skript
#
# Wenn du test_nPro.py über "Run as Python" startest,
# werden ebenfalls beide Tests nacheinander ausgeführt.
# =============================================================

def main():

    print("\n" + "=" * 80)
    print("nPro Lastprofil-Tests")
    print("=" * 80)

    print(
        f"\nProjekt-Hauptverzeichnis:\n"
        f"{PROJECT_ROOT}"
    )

    print(
        f"\nAusgabe-Hauptverzeichnis:\n"
        f"{OUTPUT_ROOT.resolve()}"
    )

    print("\n" + "#" * 80)
    print("# TEST 1: PEAK-NORMIERUNG")
    print("#" * 80)

    test_peak_normierung()

    print("\n" + "#" * 80)
    print("# TEST 2: NORMIERUNG ÜBER JAHRESWÄRMEBEDARF")
    print("#" * 80)

    test_jahresbedarf_normierung()

    print("\n" + "=" * 80)
    print("ALLE nPro-TESTS ERFOLGREICH ABGESCHLOSSEN")
    print("=" * 80)

    print(
        f"\nPeak-Ausgaben:\n"
        f"{OUTPUT_PEAK.resolve()}"
    )

    print(
        f"\nJahresbedarfs-Ausgaben:\n"
        f"{OUTPUT_DEMAND.resolve()}"
    )


if __name__ == "__main__":
    main()
