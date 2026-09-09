from pathlib import Path
import re

import pandas as pd


def make_columns_tag(category_cols):
    """
    Erzeugt einen stabilen Dateinamen-Tag aus den ausgewählten Spalten.

    Beispiele
    ---------
    ["GebTyp"] -> "GebTyp"
    ["GebTyp", "funktion"] -> "GebTyp_funktion"
    ["NutzungArt", "funktion"] -> "NutzungArt_funktion"
    """
    if isinstance(category_cols, str):
        category_cols = [category_cols]

    category_cols = list(category_cols)

    if not category_cols:
        raise ValueError("category_cols darf nicht leer sein.")

    raw = "_".join(str(col) for col in category_cols)
    tag = re.sub(r"[^A-Za-z0-9_-]+", "_", raw)

    return tag.strip("_")


def prepare_category_data(
        gdf,
        category_cols,
        demand_col=None
):
    """
    Bereitet die ausgewählten Klassifikationsspalten vor.

    Wichtige Annahme:
    Innerhalb der ausgewählten Spalten darf pro Gebäude maximal
    eine Spalte befüllt sein. Dadurch wird jedes Gebäude genau
    einmal gezählt und der Wärmebedarf nicht doppelt berücksichtigt.

    Zulässige Varianten im aktuellen Gebäudemodell sind z. B.:
        ["GebTyp"]
        ["GebTyp", "funktion"]
        ["NutzungArt", "funktion"]

    Eine Kombination wie ["GebTyp", "NutzungArt"] ist dagegen
    nicht zulässig, weil beide Spalten bei vielen Gebäuden
    gleichzeitig befüllt sind.
    """
    if isinstance(category_cols, str):
        category_cols = [category_cols]

    category_cols = list(category_cols)

    if not category_cols:
        raise ValueError("category_cols darf nicht leer sein.")

    required_cols = list(category_cols)

    if demand_col is not None:
        required_cols.append(demand_col)

    missing_cols = [
        col for col in required_cols
        if col not in gdf.columns
    ]

    if missing_cols:
        raise KeyError(
            f"Folgende Spalten fehlen im Datensatz: {missing_cols}"
        )

    data = gdf.copy()

    # Leere Strings als fehlende Werte behandeln.
    for col in category_cols:
        data[col] = data[col].replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

    if demand_col is not None:
        data[demand_col] = pd.to_numeric(
            data[demand_col],
            errors="coerce"
        ).fillna(0)

    # ---------------------------------------------------------
    # Sicherheitsprüfung gegen Doppelzählungen
    # ---------------------------------------------------------
    filled_count = data[category_cols].notna().sum(axis=1)

    overlap_mask = filled_count > 1

    if overlap_mask.any():
        examples = (
            data.loc[
                overlap_mask,
                category_cols
            ]
            .head(10)
            .to_string(index=False)
        )

        raise ValueError(
            "\nDie ausgewählten Klassifikationsspalten sind nicht "
            "gegenseitig exklusiv.\n"
            f"Ausgewählte Spalten: {category_cols}\n"
            f"Bei {int(overlap_mask.sum())} Gebäuden sind mehrere dieser "
            "Spalten gleichzeitig befüllt.\n"
            "Dadurch würden Gebäude bzw. Wärmebedarf doppelt gezählt.\n\n"
            "Beispiele:\n"
            f"{examples}"
        )

    # ---------------------------------------------------------
    # Gemeinsame Kategorie + Herkunft erzeugen
    # ---------------------------------------------------------
    data["Kategorie"] = pd.NA
    data["Quellspalte"] = pd.NA

    for col in category_cols:
        mask = (
            data["Kategorie"].isna()
            & data[col].notna()
        )

        data.loc[
            mask,
            "Kategorie"
        ] = data.loc[
            mask,
            col
        ]

        data.loc[
            mask,
            "Quellspalte"
        ] = col

    # Falls keine der ausgewählten Spalten befüllt ist.
    no_category = data["Kategorie"].isna()

    data.loc[
        no_category,
        "Kategorie"
    ] = "Keine Zuordnung"

    data.loc[
        no_category,
        "Quellspalte"
    ] = "Keine Zuordnung"

    return data


def aggregate_categories(
        gdf,
        category_cols,
        demand_col="demand_kwh"
):
    """
    Gemeinsame Aggregationslogik für Diagramm und Tabelle.

    Gruppiert nach:
        Kategorie + Quellspalte

    Dadurch bleiben gleiche Bezeichnungen aus unterschiedlichen
    Quellspalten getrennt.
    """
    data = prepare_category_data(
        gdf=gdf,
        category_cols=category_cols,
        demand_col=demand_col
    )

    result = (
        data
        .groupby(
            ["Kategorie", "Quellspalte"],
            dropna=False
        )
        .agg(
            anzahl_gebaeude=("Kategorie", "size"),
            demand_kwh_sum=(demand_col, "sum")
        )
        .reset_index()
    )

    result["demand_gwh_sum"] = (
        result["demand_kwh_sum"] / 1_000_000
    )

    # Absteigend nach Wärmebedarf sortieren.
    result = (
        result
        .sort_values(
            "demand_kwh_sum",
            ascending=False
        )
        .reset_index(drop=True)
    )

    total_demand = result["demand_kwh_sum"].sum()

    if total_demand <= 0:
        raise ValueError(
            "Der gesamte Wärmebedarf ist kleiner oder gleich 0. "
            "Eine kumulierte Prozent-Auswertung ist nicht möglich."
        )

    result["demand_share_percent"] = (
        result["demand_kwh_sum"]
        / total_demand
        * 100
    )

    result["demand_kwh_cumsum"] = (
        result["demand_kwh_sum"].cumsum()
    )

    result["demand_gwh_cumsum"] = (
        result["demand_kwh_cumsum"]
        / 1_000_000
    )

    result["demand_share_cumsum"] = (
        result["demand_kwh_cumsum"]
        / total_demand
    )

    result["demand_share_cumsum_percent"] = (
        result["demand_share_cumsum"]
        * 100
    )

    return result, total_demand


def add_source_columns(
        result,
        category_cols
):
    """
    Fügt für jede ausgewählte Quellspalte eine Ausgabespalte
    '<Spaltenname> - gdf' hinzu.

    Pro Zeile ist maximal eine dieser Spalten befüllt.
    """
    result = result.copy()

    for col in category_cols:
        out_col = f"{col} - gdf"

        result[out_col] = result["Kategorie"].where(
            result["Quellspalte"] == col,
            pd.NA
        )

    return result
