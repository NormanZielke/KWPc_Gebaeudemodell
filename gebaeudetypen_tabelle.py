from pathlib import Path

import geopandas as gpd
import pandas as pd

from gebaeudetypen_common import (
    add_source_columns,
    aggregate_categories,
)


def _create_mapping_lookup(
        mapping,
        category_cols
):
    """
    Baut einen Lookup:
        (Quellspalte, Kategorie) -> npro_type
    """
    records = []

    for col in category_cols:
        mapping_col = (
            f"{col} - gdf"
        )

        if mapping_col not in mapping.columns:
            raise KeyError(
                f"Spalte '{mapping_col}' fehlt "
                "in der Mapping-Datei."
            )

        temp = mapping[
            [
                mapping_col,
                "npro_type"
            ]
        ].dropna(
            subset=[mapping_col]
        )

        for _, row in temp.iterrows():
            records.append(
                {
                    "Quellspalte": col,
                    "Kategorie": row[mapping_col],
                    "npro_type": row["npro_type"],
                }
            )

    lookup = pd.DataFrame(
        records
    )

    if lookup.empty:
        return {}

    conflicts = (
        lookup
        .dropna(
            subset=["npro_type"]
        )
        .groupby(
            [
                "Quellspalte",
                "Kategorie"
            ]
        )["npro_type"]
        .nunique()
    )

    conflicts = conflicts[
        conflicts > 1
    ]

    if not conflicts.empty:
        raise ValueError(
            "Widersprüchliche npro_type-Zuordnungen "
            "in der Mapping-Datei:\n"
            + "\n".join(
                f"{source}: {category}"
                for source, category
                in conflicts.index
            )
        )

    lookup = lookup.drop_duplicates(
        subset=[
            "Quellspalte",
            "Kategorie"
        ]
    )

    return {
        (
            row["Quellspalte"],
            row["Kategorie"]
        ): row["npro_type"]
        for _, row
        in lookup.iterrows()
    }


def create_gebaeudetypen_table(
        path,
        category_cols,
        mapping_path,
        output_path,
        layer=None,
        demand_col="demand_kwh",
        thresholds=(0.90, 0.95, 0.98)
):
    """
    Erstellt die kumulierte Gebäudetypen-Tabelle.

    Die Spalten der Ausgabe passen sich automatisch an
    category_cols an.

    Beispiele
    ---------
    ["GebTyp"]:
        GebTyp - gdf

    ["GebTyp", "funktion"]:
        GebTyp - gdf
        funktion - gdf

    ["NutzungArt", "funktion"]:
        NutzungArt - gdf
        funktion - gdf
    """
    path = Path(path)
    mapping_path = Path(mapping_path)
    output_path = Path(output_path)

    if isinstance(category_cols, str):
        category_cols = [category_cols]

    category_cols = list(
        category_cols
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # GeoPackage einlesen
    # ---------------------------------------------------------
    if layer is None:
        gdf = gpd.read_file(
            path
        )
    else:
        gdf = gpd.read_file(
            path,
            layer=layer
        )

    # ---------------------------------------------------------
    # Aggregation
    # ---------------------------------------------------------
    result, total_demand = aggregate_categories(
        gdf=gdf,
        category_cols=category_cols,
        demand_col=demand_col
    )

    # ---------------------------------------------------------
    # Schwellenwerte markieren
    # ---------------------------------------------------------
    threshold_labels = {
        idx: []
        for idx in result.index
    }

    for threshold in thresholds:
        reached = result.index[
            result[
                "demand_share_cumsum_percent"
            ] >= threshold * 100
        ]

        if len(reached) == 0:
            continue

        idx = reached[0]

        threshold_labels[
            idx
        ].append(
            f"{threshold * 100:.0f} %"
        )

    result["Markierung"] = [
        ", ".join(
            threshold_labels[idx]
        )
        if threshold_labels[idx]
        else ""
        for idx in result.index
    ]

    # ---------------------------------------------------------
    # Dynamische Quellspalten
    # ---------------------------------------------------------
    result = add_source_columns(
        result=result,
        category_cols=category_cols
    )

    # ---------------------------------------------------------
    # nPro-Mapping laden
    # ---------------------------------------------------------
    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Mapping-Datei nicht gefunden:\n"
            f"{mapping_path}"
        )

    mapping = pd.read_excel(
        mapping_path
    )

    if "npro_type" not in mapping.columns:
        raise KeyError(
            "Die Mapping-Datei enthält keine "
            "Spalte 'npro_type'."
        )

    lookup = _create_mapping_lookup(
        mapping=mapping,
        category_cols=category_cols
    )

    result["npro_type"] = result.apply(
        lambda row: lookup.get(
            (
                row["Quellspalte"],
                row["Kategorie"]
            ),
            pd.NA
        ),
        axis=1
    )

    # ---------------------------------------------------------
    # Ausgabetabelle
    # ---------------------------------------------------------
    source_output_cols = [
        f"{col} - gdf"
        for col in category_cols
    ]

    output = result[
        source_output_cols
    ].copy()

    output["Anzahl - gdf"] = (
        result["anzahl_gebaeude"]
    )

    output["npro_type"] = (
        result["npro_type"]
    )

    output["Wärmebedarf [kWh/a]"] = (
        result["demand_kwh_sum"]
    )

    output["Wärmebedarf [GWh/a]"] = (
        result["demand_gwh_sum"]
    )

    output["Anteil Wärmebedarf [%]"] = (
        result["demand_share_percent"]
    )

    output[
        "Wärmebedarf_kumuliert [GWh/a]"
    ] = (
        result["demand_gwh_cumsum"]
    )

    output[
        "Kumulierter Anteil Wärmebedarf [%]"
    ] = (
        result[
            "demand_share_cumsum_percent"
        ]
    )

    output["Markierung"] = (
        result["Markierung"]
    )

    # ---------------------------------------------------------
    # Sicherheitsprüfung
    # ---------------------------------------------------------
    filled_source_cols = (
        output[
            source_output_cols
        ]
        .notna()
        .sum(axis=1)
    )

    if (
        filled_source_cols > 1
    ).any():
        raise RuntimeError(
            "Interner Fehler: In mindestens einer "
            "Ausgabezeile sind mehrere Quellspalten "
            "gleichzeitig befüllt."
        )

    # ---------------------------------------------------------
    # Excel speichern
    # ---------------------------------------------------------
    output.to_excel(
        output_path,
        index=False
    )

    # ---------------------------------------------------------
    # Terminal-Ausgabe
    # ---------------------------------------------------------
    print(
        f"\nGesamtwärmebedarf: "
        f"{total_demand / 1_000_000:.2f} GWh/a"
    )

    print("\nSchwellenwerte:")

    for threshold in thresholds:
        reached = output.index[
            output[
                "Kumulierter Anteil Wärmebedarf [%]"
            ] >= threshold * 100
        ]

        if len(reached) == 0:
            continue

        idx = reached[0]

        print(
            f"{threshold * 100:.0f} % werden nach "
            f"{idx + 1} Gebäudetypen erreicht: "
            f"{output.loc[idx, 'Wärmebedarf_kumuliert [GWh/a]']:.2f} "
            f"GWh/a "
            f"({output.loc[idx, 'Kumulierter Anteil Wärmebedarf [%]']:.1f} %)."
        )

    print(
        f"\nTabelle gespeichert unter:\n"
        f"{output_path}"
    )

    return output
