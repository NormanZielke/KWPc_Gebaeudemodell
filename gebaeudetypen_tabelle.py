import geopandas as gpd
import pandas as pd
from pathlib import Path


def create_gebaeudetypen_table(
        path,
        mapping_path,
        output_path="gebaeudetypen_auswertung.xlsx",
        layer=None,
        demand_col="demand_kwh",
        nutzung_col="NutzungArt",
        funktion_col="funktion",
        thresholds=(0.90, 0.95, 0.98)
):
    """
    Erstellt eine Excel-Tabelle analog zur nPro-Mapping-Tabelle.

    Die Tabelle enthält:
        - NutzungArt - gdf
        - Funktion - gdf
        - Anzahl - gdf
        - npro_type
        - Wärmebedarf [kWh/a]
        - Wärmebedarf [GWh/a]
        - Anteil Wärmebedarf [%]
        - Wärmebedarf_kumuliert [GWh/a]
        - Kumulierter Anteil Wärmebedarf [%]
        - Markierung

    Die Sortierung entspricht dem Diagramm:
        absteigend nach summiertem Wärmebedarf.

    Die Markierung zeigt die Zeile, bei der ein Schwellenwert
    (z. B. 90 %, 95 %, 98 %) erstmals erreicht bzw. überschritten wird.
    """

    path = Path(path)
    mapping_path = Path(mapping_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # Gebäudemodell einlesen
    # ---------------------------------------------------------
    if layer is None:
        gdf = gpd.read_file(path)
    else:
        gdf = gpd.read_file(
            path,
            layer=layer
        )

    required_cols = [
        nutzung_col,
        funktion_col,
        demand_col
    ]

    missing_cols = [
        col for col in required_cols
        if col not in gdf.columns
    ]

    if missing_cols:
        raise KeyError(
            f"Folgende Spalten fehlen im Gebäudemodell: "
            f"{missing_cols}"
        )

    # ---------------------------------------------------------
    # Daten vorbereiten
    # ---------------------------------------------------------
    gdf[demand_col] = pd.to_numeric(
        gdf[demand_col],
        errors="coerce"
    ).fillna(0)

    for col in [nutzung_col, funktion_col]:
        gdf[col] = gdf[col].replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

    # Genau dieselbe Logik wie im Diagramm:
    # NutzungArt hat Vorrang, ansonsten funktion.
    gdf["Gebaeudetyp"] = (
        gdf[nutzung_col]
        .fillna(gdf[funktion_col])
        .fillna("Keine Zuordnung")
    )

    # Merken, in welcher Originalspalte ein Typ vorkommt.
    nutzung_types = set(
        gdf[nutzung_col]
        .dropna()
        .astype(str)
        .unique()
    )

    funktion_types = set(
        gdf[funktion_col]
        .dropna()
        .astype(str)
        .unique()
    )

    # ---------------------------------------------------------
    # Aggregation analog zum Diagramm
    # ---------------------------------------------------------
    result = (
        gdf
        .groupby("Gebaeudetyp", dropna=False)
        .agg(
            anzahl_gebaeude=("Gebaeudetyp", "size"),
            demand_kwh_sum=(demand_col, "sum")
        )
        .reset_index()
    )

    result["demand_gwh_sum"] = (
        result["demand_kwh_sum"] / 1_000_000
    )

    result = (
        result
        .sort_values(
            "demand_kwh_sum",
            ascending=False
        )
        .reset_index(drop=True)
    )

    # ---------------------------------------------------------
    # Anteile und kumulierte Werte
    # ---------------------------------------------------------
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

    result["demand_share_cumsum_percent"] = (
        result["demand_kwh_cumsum"]
        / total_demand
        * 100
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
            result["demand_share_cumsum_percent"]
            >= threshold * 100
        ]

        if len(reached) == 0:
            continue

        idx = reached[0]

        threshold_labels[idx].append(
            f"{threshold * 100:.0f} %"
        )

    result["Markierung"] = [
        ", ".join(threshold_labels[idx])
        if threshold_labels[idx]
        else ""
        for idx in result.index
    ]

    # ---------------------------------------------------------
    # nPro-Mapping einlesen
    # ---------------------------------------------------------
    mapping = pd.read_excel(mapping_path)

    required_mapping_cols = [
        "NutzungArt - gdf",
        "Funktion - gdf",
        "npro_type"
    ]

    missing_mapping_cols = [
        col for col in required_mapping_cols
        if col not in mapping.columns
    ]

    if missing_mapping_cols:
        raise KeyError(
            f"Folgende Spalten fehlen in der Mapping-Datei: "
            f"{missing_mapping_cols}"
        )

    # Mapping beider Quellspalten zu einer gemeinsamen
    # Lookup-Tabelle zusammenführen.
    mapping_nutzung = (
        mapping[
            ["NutzungArt - gdf", "npro_type"]
        ]
        .dropna(subset=["NutzungArt - gdf"])
        .rename(
            columns={
                "NutzungArt - gdf": "Gebaeudetyp"
            }
        )
    )

    mapping_funktion = (
        mapping[
            ["Funktion - gdf", "npro_type"]
        ]
        .dropna(subset=["Funktion - gdf"])
        .rename(
            columns={
                "Funktion - gdf": "Gebaeudetyp"
            }
        )
    )

    mapping_long = pd.concat(
        [
            mapping_nutzung,
            mapping_funktion
        ],
        ignore_index=True
    )

    # Prüfen, ob derselbe Gebäudetyp mehreren npro_types
    # zugeordnet wurde.
    conflicts = (
        mapping_long
        .dropna(subset=["npro_type"])
        .groupby("Gebaeudetyp")["npro_type"]
        .nunique()
    )

    conflicts = conflicts[
        conflicts > 1
    ]

    if not conflicts.empty:
        raise ValueError(
            "In der Mapping-Datei existieren widersprüchliche "
            "npro_type-Zuordnungen für folgende Gebäudetypen:\n"
            + "\n".join(conflicts.index.astype(str))
        )

    mapping_lookup = (
        mapping_long
        .drop_duplicates(
            subset=["Gebaeudetyp"]
        )
        .set_index("Gebaeudetyp")["npro_type"]
    )

    result["npro_type"] = (
        result["Gebaeudetyp"]
        .map(mapping_lookup)
    )

    # ---------------------------------------------------------
    # Originalspalten analog zur Mapping-Tabelle erzeugen
    # ---------------------------------------------------------
    result["NutzungArt - gdf"] = result["Gebaeudetyp"].apply(
        lambda value:
        value
        if value in nutzung_types
        else pd.NA
    )

    result["Funktion - gdf"] = result["Gebaeudetyp"].apply(
        lambda value:
        value
        if value in funktion_types
        else pd.NA
    )

    # Falls keine der beiden Quellspalten belegt war.
    no_source = (
        result["NutzungArt - gdf"].isna()
        & result["Funktion - gdf"].isna()
    )

    result.loc[
        no_source,
        "NutzungArt - gdf"
    ] = result.loc[
        no_source,
        "Gebaeudetyp"
    ]

    # ---------------------------------------------------------
    # Ausgabetabelle
    # ---------------------------------------------------------
    output = pd.DataFrame({
        "NutzungArt - gdf":
            result["NutzungArt - gdf"],

        "Funktion - gdf":
            result["Funktion - gdf"],

        "Anzahl - gdf":
            result["anzahl_gebaeude"],

        "npro_type":
            result["npro_type"],

        "Wärmebedarf [kWh/a]":
            result["demand_kwh_sum"],

        "Wärmebedarf [GWh/a]":
            result["demand_gwh_sum"],

        "Anteil Wärmebedarf [%]":
            result["demand_share_percent"],

        "Wärmebedarf_kumuliert [GWh/a]":
            result["demand_gwh_cumsum"],

        "Kumulierter Anteil Wärmebedarf [%]":
            result["demand_share_cumsum_percent"],

        "Markierung":
            result["Markierung"]
    })

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

    missing_mapping = output[
        output["npro_type"].isna()
    ]

    if not missing_mapping.empty:

        print(
            "\nWARNUNG: Für folgende Gebäudetypen wurde "
            "kein npro_type gefunden:"
        )

        for _, row in missing_mapping.iterrows():

            typ = (
                row["NutzungArt - gdf"]
                if pd.notna(row["NutzungArt - gdf"])
                else row["Funktion - gdf"]
            )

            print(
                f"  - {typ}"
            )

    print(
        f"\nTabelle gespeichert unter:\n{output_path}"
    )

    return output
