import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# --------------------------------------------------
# Pfade
# --------------------------------------------------

data_path = Path("nPro/ID_25")

file_normalized = data_path / "Hotel_1m2_1kW.csv"
file_specific = data_path / "Hotel_225m2_42kW_26072kWh.csv"

# Ausgabeordner anlegen
plot_path = data_path / "plots"
plot_path.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Dateien einlesen
# --------------------------------------------------

df_norm = pd.read_csv(file_normalized)
df_spec = pd.read_csv(file_specific)


# --------------------------------------------------
# Relevante Spalten
# --------------------------------------------------

time_col = "Zeit (TT-MM hh:mm)"
heat_col = "Wärme gesamt (kW)"


# --------------------------------------------------
# Zeitachse erzeugen
# --------------------------------------------------

df_norm["datetime"] = pd.to_datetime(
    "2025-" + df_norm[time_col],
    format="%Y-%d-%m %H:%M"
)

df_spec["datetime"] = pd.to_datetime(
    "2025-" + df_spec[time_col],
    format="%Y-%d-%m %H:%M"
)


# --------------------------------------------------
# Normiertes Profil auf 42 kW skalieren
# --------------------------------------------------

peak_load_kw = 42

df_norm["heat_scaled_kw"] = (
    df_norm[heat_col] * peak_load_kw
)


# --------------------------------------------------
# Zeitreihen prüfen
# --------------------------------------------------

if len(df_norm) != len(df_spec):
    raise ValueError(
        "Die beiden Lastprofile haben unterschiedlich viele Zeitschritte."
    )

if not df_norm[time_col].equals(df_spec[time_col]):
    raise ValueError(
        "Die Zeitachsen der beiden Lastprofile stimmen nicht überein."
    )


# --------------------------------------------------
# Gesamtwärmebedarf berechnen
# --------------------------------------------------

# Bei stündlichen Werten gilt:
# kW * 1 h = kWh

heat_demand_norm_kwh = df_norm["heat_scaled_kw"].sum()
heat_demand_spec_kwh = df_spec[heat_col].sum()

difference_kwh = (
    heat_demand_spec_kwh
    - heat_demand_norm_kwh
)

relative_difference_percent = (
    difference_kwh
    / heat_demand_spec_kwh
    * 100
)


# --------------------------------------------------
# Ergebnisse ausgeben
# --------------------------------------------------

results_text = (
    f"Gesamtwärmebedarf normiertes Profil (42 kW): "
    f"{heat_demand_norm_kwh:,.1f} kWh\n"
    f"Gesamtwärmebedarf spezifisches Profil: "
    f"{heat_demand_spec_kwh:,.1f} kWh\n"
    f"Differenz: "
    f"{difference_kwh:,.1f} kWh\n"
    f"Relative Abweichung: "
    f"{relative_difference_percent:.2f} %\n"
)

print(results_text)


# --------------------------------------------------
# Ergebnisse als TXT speichern
# --------------------------------------------------

results_file = plot_path / "Auswertung_Lastprofile.txt"

with open(results_file, "w", encoding="utf-8") as file:
    file.write(results_text)


# --------------------------------------------------
# Vergleichs-DataFrame
# --------------------------------------------------

df_compare = pd.DataFrame({
    "datetime": df_spec["datetime"],
    "specific_kw": df_spec[heat_col],
    "normalized_42kw": df_norm["heat_scaled_kw"]
})

df_compare["difference_kw"] = (
    df_compare["specific_kw"]
    - df_compare["normalized_42kw"]
)


# --------------------------------------------------
# Plot 1: beide Lastprofile
# --------------------------------------------------

plt.figure(figsize=(14, 6))

plt.plot(
    df_compare["datetime"],
    df_compare["specific_kw"],
    label="Spezifisches Profil (225 m², 42 kW)"
)

plt.plot(
    df_compare["datetime"],
    df_compare["normalized_42kw"],
    label="Normiertes Profil × 42 kW",
    alpha=0.8
)

plt.xlabel("Zeit")
plt.ylabel("Wärmeleistung [kW]")
plt.title("Vergleich der Wärme-Lastprofile")

plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

# speichern
plt.savefig(
    plot_path / "Vergleich_Lastprofile.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


# --------------------------------------------------
# Plot 2: Differenz
# --------------------------------------------------

plt.figure(figsize=(14, 5))

plt.plot(
    df_compare["datetime"],
    df_compare["difference_kw"]
)

plt.axhline(
    y=0,
    linewidth=1
)

plt.xlabel("Zeit")
plt.ylabel("Differenz [kW]")
plt.title(
    "Differenz: spezifisches Profil - normiertes Profil × 42 kW"
)

plt.grid(alpha=0.3)
plt.tight_layout()

# speichern
plt.savefig(
    plot_path / "Differenz_Lastprofile.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()


# --------------------------------------------------
# Speicherorte ausgeben
# --------------------------------------------------

print(f"\nErgebnisse gespeichert unter: {plot_path}")


import plotly.graph_objects as go


# --------------------------------------------------
# Interaktiver Vergleichsplot
# --------------------------------------------------

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df_compare["datetime"],
        y=df_compare["specific_kw"],
        mode="lines",
        name="Spezifisches Profil (225 m², 42 kW)"
    )
)

fig.add_trace(
    go.Scatter(
        x=df_compare["datetime"],
        y=df_compare["normalized_42kw"],
        mode="lines",
        name="Normiertes Profil × 42 kW"
    )
)


fig.update_layout(
    title="Vergleich der Wärme-Lastprofile",
    xaxis_title="Zeit",
    yaxis_title="Wärmeleistung [kW]",
    hovermode="x unified",
    template="plotly_white"
)


# zusätzliche Navigationsleiste unter dem Plot
fig.update_xaxes(
    rangeslider_visible=True
)


# --------------------------------------------------
# Als interaktive HTML-Datei speichern
# --------------------------------------------------

interactive_file = plot_path / "Vergleich_Lastprofile_interaktiv.html"

fig.write_html(interactive_file)


# Plot öffnen
fig.show()

print(
    f"Interaktiver Vergleichsplot gespeichert unter: "
    f"{interactive_file}"
)