from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from gebaeudetypen_common import (
    aggregate_categories,
    make_columns_tag,
)


def plot_gebaeudetypen(
        path,
        category_cols,
        output_dir,
        layer=None,
        demand_col="demand_kwh",
        thresholds=(0.90, 0.95, 0.98),
        bar_gap=0.20
):
    """
    Erstellt das Gebäudetypen-Diagramm für frei wählbare
    Klassifikationsspalten.

    Der übergebene output_dir ist bereits der Plot-Ordner der
    jeweiligen Variante. Die Funktion erzeugt deshalb KEINEN
    zusätzlichen Varianten-Unterordner mehr.
    """
    path = Path(path)
    output_dir = Path(output_dir)

    if isinstance(category_cols, str):
        category_cols = [category_cols]

    category_cols = list(category_cols)

    tag = make_columns_tag(
        category_cols
    )

    output_dir.mkdir(
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
    # X-Achsen-Beschriftung mit Quellspalte
    # ---------------------------------------------------------
    #
    # Bei Varianten mit mehr als einer Quellspalte wird hinter
    # JEDEM Eintrag die Quellspalte als Abkürzung angegeben:
    #
    #   NutzungArt -> [NArt]
    #   funktion   -> [F]
    #   GebTyp     -> [GTyp]
    #
    # Bei der Einspalten-Variante ["GebTyp"] wird keine
    # Quellenangabe ergänzt.
    # ---------------------------------------------------------
    source_abbreviations = {
        "NutzungArt": "NArt",
        "funktion": "F",
        "GebTyp": "GTyp",
    }

    if len(category_cols) > 1:
        result["Plot_Label"] = result.apply(
            lambda row: (
                f"{row['Kategorie']} "
                f"[{source_abbreviations.get(row['Quellspalte'], row['Quellspalte'])}]"
            ),
            axis=1
        )
    else:
        result["Plot_Label"] = (
            result["Kategorie"].astype(str)
        )

    # ---------------------------------------------------------
    # Schwellenpositionen
    # ---------------------------------------------------------
    threshold_positions = {}

    for threshold in thresholds:
        reached = result.index[
            result["demand_share_cumsum"]
            >= threshold
        ]

        if len(reached) > 0:
            threshold_positions[
                threshold
            ] = reached[0]

    # ---------------------------------------------------------
    # Plot
    # ---------------------------------------------------------
    x = np.arange(
        len(result)
    )

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

    ax1.set_xlabel(
        "Gebäudetyp"
    )

    ax1.set_ylabel(
        "Anzahl Gebäude"
    )

    ax2.set_ylabel(
        "Summierter Wärmebedarf [GWh/a]"
    )

    ax1.set_xticks(
        x
    )

    ax1.set_xticklabels(
        result["Plot_Label"],
        rotation=45,
        ha="right"
    )

    ax1.set_title(
        "Gebäudetypen – Anzahl Gebäude und summierter Wärmebedarf\n"
        f"Spalten: {', '.join(category_cols)}"
    )

    ax1.grid(
        axis="y",
        alpha=0.3
    )

    # ---------------------------------------------------------
    # Zahlen über den Säulen
    # ---------------------------------------------------------
    ax1.bar_label(
        bars_count,
        labels=[
            f"{value:,.0f}"
            for value
            in result["anzahl_gebaeude"]
        ],
        padding=3,
        rotation=90,
        fontsize=8
    )

    ax2.bar_label(
        bars_demand,
        labels=[
            f"{value:.2f}"
            for value
            in result["demand_gwh_sum"]
        ],
        padding=3,
        rotation=90,
        fontsize=8
    )

    # ---------------------------------------------------------
    # Kumulierte Markierungen
    # ---------------------------------------------------------
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
            result.loc[
                idx,
                "demand_share_cumsum_percent"
            ]
        )

        cumulative_demand_gwh = (
            result.loc[
                idx,
                "demand_gwh_cumsum"
            ]
        )

        ax1.text(
            line_x,
            y_top * 0.98,
            f"{threshold * 100:.0f} %\n"
            f"erreicht: {actual_share:.1f} %\n"
            f"kumuliert: "
            f"{cumulative_demand_gwh:.2f} GWh/a",
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

    # ---------------------------------------------------------
    # Legende
    # ---------------------------------------------------------
    handles1, labels1 = (
        ax1.get_legend_handles_labels()
    )

    handles2, labels2 = (
        ax2.get_legend_handles_labels()
    )

    ax1.legend(
        handles1 + handles2,
        labels1 + labels2,
        loc="upper right",
        bbox_to_anchor=(0.90, 1.0)
    )

    plt.tight_layout()

    # ---------------------------------------------------------
    # Speichern
    # ---------------------------------------------------------
    output_file = (
        output_dir
        / (
            "gebaeudetypen_anzahl_"
            f"waermebedarf_kumuliert_{tag}.png"
        )
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    # ---------------------------------------------------------
    # Terminal-Ausgabe
    # ---------------------------------------------------------
    print("\nSchwellenwerte:")

    for threshold, idx in threshold_positions.items():

        print(
            f"{threshold * 100:.0f} % des Gesamtwärmebedarfs "
            f"werden nach {idx + 1} Gebäudetypen erreicht "
            f"(kumuliert: "
            f"{result.loc[idx, 'demand_share_cumsum_percent']:.1f} %, "
            f"{result.loc[idx, 'demand_gwh_cumsum']:.2f} GWh/a)."
        )

    print(
        f"\nGesamtwärmebedarf: "
        f"{total_demand / 1_000_000:.2f} GWh/a"
    )

    print(
        f"\nPlot gespeichert unter:\n"
        f"{output_file}"
    )

    return result
