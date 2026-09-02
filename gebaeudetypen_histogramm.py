import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def plot_gebaeudetypen(
        path,
        output_dir="plots",
        layer=None,
        demand_col="demand_kwh",
        nutzung_col="NutzungArt",
        funktion_col="funktion",
        thresholds=(0.90, 0.95, 0.98),
        bar_gap=0.20
):
    """
    Erstellt ein Balkendiagramm über alle Gebäudetypen.

    Gebäudetyp:
        1. NutzungArt, falls vorhanden
        2. ansonsten funktion

    Darstellung:
        - Säule 1: Anzahl Gebäude
        - Säule 2: summierter Wärmebedarf [GWh/a]
        - Markierungen an den vorgegebenen kumulierten Schwellenwerten

    Die Gebäudetypen werden absteigend nach dem summierten
    Wärmebedarf sortiert.
    """

    path = Path(path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if layer is None:
        gdf = gpd.read_file(path)
    else:
        gdf = gpd.read_file(path, layer=layer)

    required_cols = [nutzung_col, funktion_col, demand_col]
    missing_cols = [col for col in required_cols if col not in gdf.columns]

    if missing_cols:
        raise KeyError(
            f"Folgende Spalten fehlen im Datensatz: {missing_cols}"
        )

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

    gdf["Gebaeudetyp"] = (
        gdf[nutzung_col]
        .fillna(gdf[funktion_col])
        .fillna("Keine Zuordnung")
    )

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

    total_demand = result["demand_kwh_sum"].sum()

    if total_demand <= 0:
        raise ValueError(
            "Der gesamte Wärmebedarf ist kleiner oder gleich 0. "
            "Eine kumulierte Prozent-Auswertung ist nicht möglich."
        )

    result["demand_kwh_cumsum"] = (
        result["demand_kwh_sum"].cumsum()
    )

    result["demand_share_cumsum"] = (
        result["demand_kwh_cumsum"] / total_demand
    )

    threshold_positions = {}

    for threshold in thresholds:
        reached = result.index[
            result["demand_share_cumsum"] >= threshold
        ]

        if len(reached) > 0:
            threshold_positions[threshold] = reached[0]

    x = np.arange(len(result))
    width = 0.36

    fig, ax1 = plt.subplots(
        figsize=(22, 11)
    )

    ax2 = ax1.twinx()

    bars_count = ax1.bar(
        x - (width + bar_gap) / 2,
        result["anzahl_gebaeude"],
        width=width,
        label="Anzahl Gebäude"
    )

    bars_demand = ax2.bar(
        x + (width + bar_gap) / 2,
        result["demand_gwh_sum"],
        width=width,
        alpha=0.65,
        label="Wärmebedarf [GWh/a]"
    )

    ax1.set_xlabel("Gebäudetyp")
    ax1.set_ylabel("Anzahl Gebäude")
    ax2.set_ylabel("Summierter Wärmebedarf [GWh/a]")

    ax1.set_xticks(x)
    ax1.set_xticklabels(
        result["Gebaeudetyp"],
        rotation=45,
        ha="right"
    )

    ax1.set_title(
        "Gebäudetypen – Anzahl Gebäude und summierter Wärmebedarf\n"
        "Sortiert nach Wärmebedarf mit kumulierten %-Markierungen"
    )

    ax1.grid(
        axis="y",
        alpha=0.3
    )

    ax1.bar_label(
        bars_count,
        labels=[
            f"{value:,.0f}"
            for value in result["anzahl_gebaeude"]
        ],
        padding=3,
        rotation=90,
        fontsize=8
    )

    ax2.bar_label(
        bars_demand,
        labels=[
            f"{value:.2f}"
            for value in result["demand_gwh_sum"]
        ],
        padding=3,
        rotation=90,
        fontsize=8
    )

    y_top = ax1.get_ylim()[1]

    for threshold, idx in threshold_positions.items():

        line_x = idx + 0.5

        ax1.axvline(
            x=line_x,
            linestyle="--",
            linewidth=1.5,
            alpha=0.8
        )

        actual_share = (
            result.loc[idx, "demand_share_cumsum"] * 100
        )

        cumulative_demand_gwh = (
            result.loc[idx, "demand_kwh_cumsum"] / 1_000_000
        )

        ax1.text(
            line_x,
            y_top * 0.98,
            f"{threshold * 100:.0f} %\n"
            f"erreicht: {actual_share:.1f} %\n"
            f"kumuliert: {cumulative_demand_gwh:.2f} GWh/a",
            rotation=90,
            va="top",
            ha="right",
            fontsize=9,
            bbox=dict(
                boxstyle="round,pad=0.25",
                facecolor="white",
                alpha=0.8
            )
        )

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        handles1 + handles2,
        labels1 + labels2,
        loc="upper right",
        bbox_to_anchor=(0.90, 1.0)
    )

    plt.tight_layout()

    output_file = (
        output_dir /
        "gebaeudetypen_anzahl_waermebedarf_kumuliert.png"
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    result["demand_share_cumsum_percent"] = (
        result["demand_share_cumsum"] * 100
    )

    print("\nSchwellenwerte:")

    for threshold, idx in threshold_positions.items():

        cumulative_demand_gwh = (
            result.loc[idx, "demand_kwh_cumsum"] / 1_000_000
        )

        print(
            f"{threshold * 100:.0f} % des Gesamtwärmebedarfs "
            f"werden nach {idx + 1} Gebäudetypen erreicht "
            f"(kumuliert: "
            f"{result.loc[idx, 'demand_share_cumsum_percent']:.1f} %, "
            f"{cumulative_demand_gwh:.2f} GWh/a)."
        )

    print(
        f"\nGesamtwärmebedarf: "
        f"{total_demand / 1_000_000:.2f} GWh/a"
    )

    print(
        f"\nPlot gespeichert unter:\n{output_file}"
    )

    return result
