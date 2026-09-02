from pathlib import Path

import geopandas as gpd


def check_dataframe(path, cols):

    # ==========================================================
    # 1. Gebäudemodell laden
    # ==========================================================

    # Vollständiger Rohdatensatz
    # -> bleibt mit ALLEN Spalten erhalten
    gdf = gpd.read_file(path)

    # ----------------------------------------------------------
    # Prüfen, ob benötigte Spalten vorhanden sind
    # ----------------------------------------------------------

    required_cols = [
        "NutzungArt",
        "funktion",
    ]

    missing_required = [
        col for col in required_cols
        if col not in gdf.columns
    ]

    if missing_required:
        raise KeyError(
            f"Folgende benötigte Spalten fehlen im Gebäudemodell: "
            f"{missing_required}"
        )

    missing_check_cols = [
        col for col in cols
        if col not in gdf.columns
    ]

    if missing_check_cols:
        raise KeyError(
            f"Folgende in 'cols' angegebene Spalten fehlen: "
            f"{missing_check_cols}"
        )

    # ==========================================================
    # 2. Hilfsfunktion:
    #    Prüfen, ob tatsächlich ein Eintrag vorhanden ist
    # ==========================================================

    def has_entry(series):
        """
        True, wenn ein Wert vorhanden ist.

        Berücksichtigt:
        - NaN
        - None
        - ""
        - Strings nur aus Leerzeichen
        """

        return (
            series.notna()
            & series.astype(str).str.strip().ne("")
        )

    # ==========================================================
    # 3. Kategorien definieren
    #
    # WICHTIG:
    # Die Strings entsprechen EXAKT den Werten im DataFrame.
    # Die Zeichen wie "�" werden NICHT korrigiert.
    # ==========================================================

    # ----------------------------------------------------------
    # Mixed-Use-Kategorien
    # ----------------------------------------------------------

    mixed_use = [
        "Geb�ude f�r Handel und Dienstleistung mit Wohnen",
        "Geb�ude f�r Gewerbe und Industrie mit Wohnen",
        "Wohngeb�ude mit Gewerbe und Industrie",
        "Wohngeb�ude mit Handel und Dienstleistungen",
        "Wohn- und Gesch�ftsgeb�ude",
        "Wohngeb�ude mit Gemeinbedarf",
    ]

    # ----------------------------------------------------------
    # Wohn-Kategorien
    # ----------------------------------------------------------

    wohn_kategorien = [
        "Wohnhaus",
        "Wohngeb�ude",
        "Wohnheim",
        "Wochenendhaus",
        "Wohn- und Gesch�ftsgeb�ude",
        "Wohngeb�ude mit Gemeinbedarf",
        "Wohngeb�ude mit Gewerbe und Industrie",
        "Wohngeb�ude mit Handel und Dienstleistungen",
        "Geb�ude f�r Gewerbe und Industrie mit Wohnen",
        "Geb�ude f�r Handel und Dienstleistung mit Wohnen",
    ]

    # ==========================================================
    # 4. Grundlegende Masken
    # ==========================================================

    has_nutzungart = has_entry(
        gdf["NutzungArt"]
    )

    has_funktion = has_entry(
        gdf["funktion"]
    )

    # ==========================================================
    # 5. Alle tatsächlich vorhandenen Kategorien
    # ==========================================================

    # ----------------------------------------------------------
    # NutzungArt
    # ----------------------------------------------------------

    nutzungart_kategorien = sorted(
        gdf.loc[
            has_nutzungart,
            "NutzungArt"
        ]
        .unique()
        .tolist()
    )

    # ----------------------------------------------------------
    # funktion
    # ----------------------------------------------------------

    funktion_kategorien = sorted(
        gdf.loc[
            has_funktion,
            "funktion"
        ]
        .unique()
        .tolist()
    )

    # ==========================================================
    # 6. Nicht-Wohn-Kategorien automatisch bestimmen
    #
    # Alle vorhandenen NutzungArt-Kategorien,
    # die NICHT in wohn_kategorien enthalten sind.
    # ==========================================================

    nicht_wohn_kategorien = sorted(
        [
            category
            for category in nutzungart_kategorien
            if category not in wohn_kategorien
        ]
    )

    # ==========================================================
    # 7. Gebäudemasken
    # ==========================================================

    # Gebäude mit Wohn-Kategorie
    is_wohnen = (
        has_nutzungart
        & gdf["NutzungArt"].isin(
            wohn_kategorien
        )
    )

    # Gebäude mit Nicht-Wohn-Kategorie
    is_nicht_wohnen = (
        has_nutzungart
        & gdf["NutzungArt"].isin(
            nicht_wohn_kategorien
        )
    )

    # Gebäude mit Mixed-Use-Kategorie
    is_mixed = (
        has_nutzungart
        & gdf["NutzungArt"].isin(
            mixed_use
        )
    )

    # ==========================================================
    # 8. DataFrames zum Prüfen
    #
    # gdf bleibt vollständig.
    #
    # Alle folgenden DataFrames werden auf die in "cols"
    # angegebenen Spalten reduziert.
    # ==========================================================

    # Gesamter Datensatz mit Prüfspalten
    gdf_check = gdf.loc[
        :,
        cols
    ].copy()

    # Gebäude mit NutzungArt
    gdf_nutzungart = gdf.loc[
        has_nutzungart,
        cols
    ].copy()

    # Gebäude mit Funktion
    gdf_funktion = gdf.loc[
        has_funktion,
        cols
    ].copy()

    # Wohngebäude
    gdf_wohnen = gdf.loc[
        is_wohnen,
        cols
    ].copy()

    # Nicht-Wohngebäude
    gdf_nicht_wohnen = gdf.loc[
        is_nicht_wohnen,
        cols
    ].copy()

    # Mixed-Use-Gebäude
    gdf_mixed = gdf.loc[
        is_mixed,
        cols
    ].copy()

    # ==========================================================
    # 9. Prüfung funktion / NutzungArt
    # ==========================================================

    # Beide Spalten sind befüllt
    mask_both = (
        has_funktion
        & has_nutzungart
    )

    gdf_both = gdf.loc[
        mask_both,
        cols
    ].copy()

    # Beide Spalten sind leer
    mask_neither = (
        ~has_funktion
        & ~has_nutzungart
    )

    gdf_neither = gdf.loc[
        mask_neither,
        cols
    ].copy()

    # Genau eine der beiden Spalten ist befüllt
    mask_either = (
        has_funktion
        ^ has_nutzungart
    )

    gdf_either = gdf.loc[
        mask_either,
        cols
    ].copy()

    # Prüfen, ob diese Aussage für ALLE Gebäude gilt
    funktion_nutzungart_exklusiv = bool(
        mask_either.all()
    )

    # ==========================================================
    # 10. Anzahl Gebäude
    # ==========================================================

    n_gesamt = len(gdf)

    n_nutzungart = int(
        has_nutzungart.sum()
    )

    n_funktion = int(
        has_funktion.sum()
    )

    n_wohnen = int(
        is_wohnen.sum()
    )

    n_nicht_wohnen = int(
        is_nicht_wohnen.sum()
    )

    n_mixed = int(
        is_mixed.sum()
    )

    n_both = int(
        mask_both.sum()
    )

    n_neither = int(
        mask_neither.sum()
    )

    n_either = int(
        mask_either.sum()
    )

    # ==========================================================
    # 11. Gegencheck:
    #
    # Wohnen + Nicht-Wohnen muss ALLE Gebäude mit NutzungArt
    # ergeben.
    # ==========================================================

    n_wohnen_plus_nicht_wohnen = (
        n_wohnen
        + n_nicht_wohnen
    )

    check_anzahl_nutzungart = (
        n_wohnen_plus_nicht_wohnen
        == n_nutzungart
    )

    # ==========================================================
    # 12. Zusätzlicher Kategorien-Gegencheck
    #
    # Prüfen, ob die aufgelisteten Wohn- und Nicht-Wohn-
    # Kategorien zusammen exakt alle vorhandenen
    # NutzungArt-Kategorien ergeben.
    # ==========================================================

    set_nutzungart = set(
        nutzungart_kategorien
    )

    set_wohnen = set(
        wohn_kategorien
    )

    set_nicht_wohnen = set(
        nicht_wohn_kategorien
    )

    # Nur Wohnkategorien betrachten,
    # die im Datensatz tatsächlich vorkommen
    set_wohnen_vorhanden = (
        set_wohnen
        & set_nutzungart
    )

    # Vereinigung beider Kategoriengruppen
    set_kategorien_gesamt = (
        set_wohnen_vorhanden
        | set_nicht_wohnen
    )

    check_kategorien_vollstaendig = (
        set_kategorien_gesamt
        == set_nutzungart
    )

    # Prüfen, ob eine Kategorie gleichzeitig
    # Wohnen UND Nicht-Wohnen ist
    kategorien_ueberschneidung = (
        set_wohnen_vorhanden
        & set_nicht_wohnen
    )

    check_kategorien_keine_ueberschneidung = (
        len(kategorien_ueberschneidung)
        == 0
    )

    # ==========================================================
    # 13. Mixed-Use-Gegencheck
    #
    # Mixed Use soll Teil der Wohnkategorien sein.
    # ==========================================================

    mixed_use_nicht_in_wohnen = [
        category
        for category in mixed_use
        if category not in wohn_kategorien
    ]

    check_mixed_use_in_wohnen = (
        len(mixed_use_nicht_in_wohnen)
        == 0
    )

    # ==========================================================
    # 14. Anzahl Gebäude je Kategorie
    # ==========================================================

    # ----------------------------------------------------------
    # NutzungArt
    # ----------------------------------------------------------

    nutzungart_counts = (
        gdf.loc[
            has_nutzungart,
            "NutzungArt"
        ]
        .value_counts()
        .sort_index()
    )

    n_nutzungart_aus_kategorien = int(
        nutzungart_counts.sum()
    )

    check_summe_einzelkategorien = (
        n_nutzungart_aus_kategorien
        == n_nutzungart
    )

    # ----------------------------------------------------------
    # funktion
    # ----------------------------------------------------------

    funktion_counts = (
        gdf.loc[
            has_funktion,
            "funktion"
        ]
        .value_counts()
        .sort_index()
    )

    n_funktion_aus_kategorien = int(
        funktion_counts.sum()
    )

    check_summe_funktion_kategorien = (
        n_funktion_aus_kategorien
        == n_funktion
    )

    # ==========================================================
    # 15. Prozent-Hilfsfunktion
    # ==========================================================

    def prozent(anzahl, gesamt):

        if gesamt == 0:
            return 0.0

        return (
            anzahl
            / gesamt
            * 100
        )

    # ==========================================================
    # 16. Textbericht speichern
    # ==========================================================

    report_path = Path(path).with_name(
        Path(path).stem
        + "_dataframe_check.txt"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        # ======================================================
        # Überschrift
        # ======================================================

        file.write(
            "CHECK GEBÄUDEMODELL\n"
        )

        file.write(
            "=" * 80
            + "\n\n"
        )

        file.write(
            f"Quelldatei:\n"
            f"{path}\n\n"
        )

        # ======================================================
        # 1. Gebäudestatistik
        # ======================================================

        file.write(
            "1. GEBÄUDESTATISTIK\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        file.write(
            f"Gesamtzahl Gebäude: "
            f"{n_gesamt}\n\n"
        )

        # ------------------------------------------------------
        # NutzungArt
        # ------------------------------------------------------

        file.write(
            f"Gebäude mit NutzungArt: "
            f"{n_nutzungart}\n"
        )

        file.write(
            f"Anteil an Gesamtgebäuden: "
            f"{prozent(n_nutzungart, n_gesamt):.2f} %\n\n"
        )

        # ------------------------------------------------------
        # Funktion
        # ------------------------------------------------------

        file.write(
            f"Gebäude mit Funktion: "
            f"{n_funktion}\n"
        )

        file.write(
            f"Anteil an Gesamtgebäuden: "
            f"{prozent(n_funktion, n_gesamt):.2f} %\n\n"
        )

        # ------------------------------------------------------
        # Wohnen
        # ------------------------------------------------------

        file.write(
            f"Gebäude mit Wohn-Kategorie: "
            f"{n_wohnen}\n"
        )

        file.write(
            f"Anteil an Gesamtgebäuden: "
            f"{prozent(n_wohnen, n_gesamt):.2f} %\n"
        )

        file.write(
            f"Anteil an Gebäuden mit NutzungArt: "
            f"{prozent(n_wohnen, n_nutzungart):.2f} %\n\n"
        )

        # ------------------------------------------------------
        # Nicht-Wohnen
        # ------------------------------------------------------

        file.write(
            f"Gebäude mit Nicht-Wohn-Kategorie: "
            f"{n_nicht_wohnen}\n"
        )

        file.write(
            f"Anteil an Gesamtgebäuden: "
            f"{prozent(n_nicht_wohnen, n_gesamt):.2f} %\n"
        )

        file.write(
            f"Anteil an Gebäuden mit NutzungArt: "
            f"{prozent(n_nicht_wohnen, n_nutzungart):.2f} %\n\n"
        )

        # ------------------------------------------------------
        # Mixed Use
        # ------------------------------------------------------

        file.write(
            f"Gebäude mit Mixed-Use-Kategorie: "
            f"{n_mixed}\n"
        )

        file.write(
            f"Anteil an Gesamtgebäuden: "
            f"{prozent(n_mixed, n_gesamt):.2f} %\n"
        )

        file.write(
            f"Anteil an Gebäuden mit NutzungArt: "
            f"{prozent(n_mixed, n_nutzungart):.2f} %\n\n"
        )

        # ======================================================
        # 2. Prüfung funktion / NutzungArt
        # ======================================================

        file.write(
            "\n2. PRÜFUNG FUNKTION / NUTZUNGART\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        file.write(
            f"Gebäude mit genau einem Eintrag "
            f"(funktion ODER NutzungArt): "
            f"{n_either}\n"
        )

        file.write(
            f"Gebäude mit Eintrag in beiden Spalten: "
            f"{n_both}\n"
        )

        file.write(
            f"Gebäude ohne Eintrag in beiden Spalten: "
            f"{n_neither}\n\n"
        )

        file.write(
            "Aussage:\n"
            "'Jedes Gebäude hat entweder funktion oder "
            "NutzungArt, aber nicht beides.'\n"
        )

        file.write(
            f"Ergebnis: "
            f"{funktion_nutzungart_exklusiv}\n"
        )

        # ======================================================
        # 3. Gegenchecks
        # ======================================================

        file.write(
            "\n\n3. GEGENCHECKS\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        # ------------------------------------------------------
        # Wohnen / Nicht-Wohnen
        # ------------------------------------------------------

        file.write(
            "3.1 Wohnen / Nicht-Wohnen\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        file.write(
            f"Gebäude mit Wohn-Kategorie: "
            f"{n_wohnen}\n"
        )

        file.write(
            f"Gebäude mit Nicht-Wohn-Kategorie: "
            f"{n_nicht_wohnen}\n"
        )

        file.write(
            f"Summe Wohnen + Nicht-Wohnen: "
            f"{n_wohnen_plus_nicht_wohnen}\n"
        )

        file.write(
            f"Gesamtzahl Gebäude mit NutzungArt: "
            f"{n_nutzungart}\n\n"
        )

        file.write(
            "Prüfung:\n"
            "Wohnen + Nicht-Wohnen "
            "== Gebäude mit NutzungArt\n"
        )

        file.write(
            f"Ergebnis: "
            f"{check_anzahl_nutzungart}\n\n"
        )

        # ------------------------------------------------------
        # Kategoriencheck NutzungArt
        # ------------------------------------------------------

        file.write(
            "3.2 Kategorienlisten NutzungArt\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        file.write(
            "Wohn-Kategorien + Nicht-Wohn-Kategorien "
            "decken alle vorhandenen NutzungArt-Kategorien ab:\n"
        )

        file.write(
            f"Ergebnis: "
            f"{check_kategorien_vollstaendig}\n\n"
        )

        file.write(
            "Keine Überschneidung zwischen "
            "Wohn- und Nicht-Wohn-Kategorien:\n"
        )

        file.write(
            f"Ergebnis: "
            f"{check_kategorien_keine_ueberschneidung}\n"
        )

        if kategorien_ueberschneidung:

            file.write(
                "Überschneidende Kategorien:\n"
            )

            for category in sorted(
                kategorien_ueberschneidung
            ):

                file.write(
                    f"- {category}\n"
                )

        file.write(
            "\nMixed-Use-Kategorien sind vollständig "
            "in den Wohn-Kategorien enthalten:\n"
        )

        file.write(
            f"Ergebnis: "
            f"{check_mixed_use_in_wohnen}\n"
        )

        if mixed_use_nicht_in_wohnen:

            file.write(
                "Fehlende Mixed-Use-Kategorien:\n"
            )

            for category in mixed_use_nicht_in_wohnen:

                file.write(
                    f"- {category}\n"
                )

        # ------------------------------------------------------
        # Summencheck NutzungArt
        # ------------------------------------------------------

        file.write(
            "\n\n3.3 Summencheck NutzungArt-Kategorien\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        file.write(
            "Summe Gebäude aus allen einzelnen "
            "NutzungArt-Kategorien:\n"
        )

        file.write(
            f"{n_nutzungart_aus_kategorien}\n"
        )

        file.write(
            "Gesamtzahl Gebäude mit NutzungArt:\n"
        )

        file.write(
            f"{n_nutzungart}\n"
        )

        file.write(
            "Ergebnis: "
            f"{check_summe_einzelkategorien}\n"
        )

        # ------------------------------------------------------
        # Summencheck funktion
        # ------------------------------------------------------

        file.write(
            "\n\n3.4 Summencheck funktion-Kategorien\n"
        )

        file.write(
            "-" * 80
            + "\n\n"
        )

        file.write(
            "Summe Gebäude aus allen einzelnen "
            "funktion-Kategorien:\n"
        )

        file.write(
            f"{n_funktion_aus_kategorien}\n"
        )

        file.write(
            "Gesamtzahl Gebäude mit funktion:\n"
        )

        file.write(
            f"{n_funktion}\n"
        )

        file.write(
            "Ergebnis: "
            f"{check_summe_funktion_kategorien}\n"
        )

        # ======================================================
        # 4. Kategorien
        # ======================================================

        file.write(
            "\n\n4. KATEGORIEN\n"
        )

        file.write(
            "=" * 80
            + "\n\n"
        )

        # ------------------------------------------------------
        # Alle funktion-Kategorien
        # ------------------------------------------------------

        file.write(
            "Alle vorhandenen funktion-Kategorien:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category in funktion_kategorien:

            file.write(
                f"- {category}\n"
            )

        # ------------------------------------------------------
        # Alle NutzungArt-Kategorien
        # ------------------------------------------------------

        file.write(
            "\n\nAlle vorhandenen NutzungArt-Kategorien:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category in nutzungart_kategorien:

            file.write(
                f"- {category}\n"
            )

        # ------------------------------------------------------
        # Wohn-Kategorien
        # ------------------------------------------------------

        file.write(
            "\n\nWohn-Kategorien:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category in wohn_kategorien:

            file.write(
                f"- {category}\n"
            )

        # ------------------------------------------------------
        # Mixed-Use-Kategorien
        # ------------------------------------------------------

        file.write(
            "\n\nMixed-Use-Kategorien:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category in mixed_use:

            file.write(
                f"- {category}\n"
            )

        # ------------------------------------------------------
        # Nicht-Wohn-Kategorien
        # ------------------------------------------------------

        file.write(
            "\n\nNicht-Wohn-Kategorien:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category in nicht_wohn_kategorien:

            file.write(
                f"- {category}\n"
            )

        # ======================================================
        # 5. Anzahl Gebäude je Kategorie
        # ======================================================

        file.write(
            "\n\n5. ANZAHL GEBÄUDE JE KATEGORIE\n"
        )

        file.write(
            "=" * 80
            + "\n\n"
        )

        # ------------------------------------------------------
        # funktion
        # ------------------------------------------------------

        file.write(
            "Anzahl Gebäude je funktion:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category, count in funktion_counts.items():

            file.write(
                f"- {category}: "
                f"{count}\n"
            )

        file.write(
            "\nSumme Gebäude aus allen funktion-Kategorien: "
            f"{n_funktion_aus_kategorien}\n"
        )

        file.write(
            "Gesamtzahl Gebäude mit funktion: "
            f"{n_funktion}\n"
        )

        file.write(
            "Ergebnis: "
            f"{check_summe_funktion_kategorien}\n"
        )

        # ------------------------------------------------------
        # NutzungArt
        # ------------------------------------------------------

        file.write(
            "\n\nAnzahl Gebäude je NutzungArt:\n"
        )

        file.write(
            "-" * 80
            + "\n"
        )

        for category, count in nutzungart_counts.items():

            file.write(
                f"- {category}: "
                f"{count}\n"
            )

        file.write(
            "\nSumme Gebäude aus allen NutzungArt-Kategorien: "
            f"{n_nutzungart_aus_kategorien}\n"
        )

        file.write(
            "Gesamtzahl Gebäude mit NutzungArt: "
            f"{n_nutzungart}\n"
        )

        file.write(
            "Ergebnis: "
            f"{check_summe_einzelkategorien}\n"
        )

    # ==========================================================
    # 17. Konsolenausgabe
    # ==========================================================

    print(
        f"Check gespeichert unter:\n"
        f"{report_path}"
    )

    print()

    print(
        "Gegencheck Wohnen + Nicht-Wohnen "
        f"= NutzungArt: {check_anzahl_nutzungart}"
    )

    print(
        "Kategorien vollständig: "
        f"{check_kategorien_vollstaendig}"
    )

    print(
        "Keine Überschneidung Wohnen/Nicht-Wohnen: "
        f"{check_kategorien_keine_ueberschneidung}"
    )

    print(
        "Summe NutzungArt-Kategorien korrekt: "
        f"{check_summe_einzelkategorien}"
    )

    print(
        "Summe funktion-Kategorien korrekt: "
        f"{check_summe_funktion_kategorien}"
    )

    # ==========================================================
    # 18. Rückgabe für Debug-Modus
    # ==========================================================

    return {

        # ------------------------------------------------------
        # vollständiger Rohdatensatz
        # ------------------------------------------------------

        "gdf": gdf,

        # ------------------------------------------------------
        # reduzierte Prüf-DataFrames
        # ------------------------------------------------------

        "gdf_check": gdf_check,
        "gdf_nutzungart": gdf_nutzungart,
        "gdf_funktion": gdf_funktion,
        "gdf_wohnen": gdf_wohnen,
        "gdf_nicht_wohnen": gdf_nicht_wohnen,
        "gdf_mixed": gdf_mixed,

        # ------------------------------------------------------
        # funktion / NutzungArt
        # ------------------------------------------------------

        "gdf_both": gdf_both,
        "gdf_neither": gdf_neither,
        "gdf_either": gdf_either,

        "funktion_nutzungart_exklusiv":
            funktion_nutzungart_exklusiv,

        # ------------------------------------------------------
        # Kategorien
        # ------------------------------------------------------

        "nutzungart_kategorien":
            nutzungart_kategorien,

        "funktion_kategorien":
            funktion_kategorien,

        "wohn_kategorien":
            wohn_kategorien,

        "mixed_use":
            mixed_use,

        "nicht_wohn_kategorien":
            nicht_wohn_kategorien,

        "nutzungart_counts":
            nutzungart_counts,

        "funktion_counts":
            funktion_counts,

        # ------------------------------------------------------
        # Gegenchecks
        # ------------------------------------------------------

        "check_anzahl_nutzungart":
            check_anzahl_nutzungart,

        "check_kategorien_vollstaendig":
            check_kategorien_vollstaendig,

        "check_kategorien_keine_ueberschneidung":
            check_kategorien_keine_ueberschneidung,

        "check_mixed_use_in_wohnen":
            check_mixed_use_in_wohnen,

        "check_summe_einzelkategorien":
            check_summe_einzelkategorien,

        "check_summe_funktion_kategorien":
            check_summe_funktion_kategorien,

        # ------------------------------------------------------
        # Bericht
        # ------------------------------------------------------

        "report_path":
            report_path,
    }


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
    "demand_spec",
    "demand_spec_san",
]


# ==============================================================
# Gebäudemodell prüfen
# ==============================================================

data = check_dataframe(
    path,
    cols
)

gdf_nicht_wohnen = data["gdf_nicht_wohnen"]

gdf_hotel = gdf_nicht_wohnen[
    gdf_nicht_wohnen["NutzungArt"] == "Hotel, Motel, Pension"
].copy()

gdf_buero = gdf_nicht_wohnen[
    gdf_nicht_wohnen["NutzungArt"] == "B�rogeb�ude"
].copy()


print("check")

print("DEBUG")