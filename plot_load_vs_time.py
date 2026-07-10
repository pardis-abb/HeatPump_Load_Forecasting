"""
Create defensible load-versus-time graphs for the HP/AC model.

The graphs show calculated electrical demand for one representative
dwelling/system. They do not use the placeholder number of installed
heat pumps or claim to represent total Calgary HP/AC demand.

Run this after:
    python load_modifier_full_model.py

Input:
    results/hourly_hp_ac_load_modifier_results.csv

Outputs:
    results/graphs/
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# File paths and study period
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RESULTS_FILE = (
    BASE_DIR
    / "results"
    / "hourly_hp_ac_load_modifier_results.csv"
)

GRAPH_FOLDER = BASE_DIR / "results" / "graphs"
GRAPH_FOLDER.mkdir(parents=True, exist_ok=True)

# Exact period matching the AESO dataset
STUDY_START = pd.Timestamp("2023-11-01 00:00:00")
STUDY_END = pd.Timestamp("2024-12-31 23:00:00")


REQUIRED_COLUMNS = [
    "datetime",
    "outdoor_temp_c",
    "hp_load_kwh_per_unit",
    "ac_load_kwh_per_unit",
    "total_hp_ac_load_kwh_per_unit",
]


# ============================================================
# Read and clean model results
# ============================================================

def load_results():
    """
    Read, validate, clean, and restrict the model output
    to November 2023 through December 2024.
    """

    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            f"Could not find:\n{RESULTS_FILE}\n\n"
            "Run load_modifier_full_model.py first."
        )

    df = pd.read_csv(RESULTS_FILE)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "The results file is missing these columns:\n"
            + "\n".join(missing_columns)
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce"
    )

    numeric_columns = [
        "outdoor_temp_c",
        "hp_load_kwh_per_unit",
        "ac_load_kwh_per_unit",
        "total_hp_ac_load_kwh_per_unit",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Remove invalid timestamps and duplicate hourly rows
    df = (
        df
        .dropna(subset=["datetime"])
        .sort_values("datetime")
        .drop_duplicates(subset=["datetime"], keep="first")
        .reset_index(drop=True)
    )

    # Keep only the period that matches the intended database
    outside_period = (
        (df["datetime"] < STUDY_START)
        | (df["datetime"] > STUDY_END)
    )

    removed_rows = int(outside_period.sum())

    if removed_rows > 0:
        print(
            f"Removed {removed_rows} rows outside the study period "
            f"{STUDY_START.date()} to {STUDY_END.date()}."
        )

    df = df[
        (df["datetime"] >= STUDY_START)
        & (df["datetime"] <= STUDY_END)
    ].copy()

    if df.empty:
        raise ValueError(
            "No data remained after applying the study-period filter."
        )

    print(f"Data start: {df['datetime'].min()}")
    print(f"Data end:   {df['datetime'].max()}")
    print(f"Hourly rows used: {len(df)}")

    return df


# ============================================================
# Save helper
# ============================================================

def save_figure(filename):
    """Save and close the current figure."""

    output_path = GRAPH_FOLDER / filename

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    print(f"Saved: {output_path}")


# ============================================================
# Figure 1: Full-period daily-average load
# ============================================================

def plot_daily_average_load(df):
    """
    Plot daily-average heating, cooling, and total electrical power.

    Since each source value represents energy over one hour,
    its daily average is numerically equivalent to average kW.
    """

    daily = (
        df
        .set_index("datetime")[
            [
                "hp_load_kwh_per_unit",
                "ac_load_kwh_per_unit",
                "total_hp_ac_load_kwh_per_unit",
            ]
        ]
        .resample("D")
        .mean()
        .dropna(how="all")
        .reset_index()
    )

    plt.figure(figsize=(14, 6))

    plt.plot(
        daily["datetime"],
        daily["hp_load_kwh_per_unit"],
        label="Heat pump",
        linewidth=1.0
    )

    plt.plot(
        daily["datetime"],
        daily["ac_load_kwh_per_unit"],
        label="Air conditioner",
        linewidth=1.0
    )

    plt.plot(
        daily["datetime"],
        daily["total_hp_ac_load_kwh_per_unit"],
        label="Total HP/AC",
        linewidth=1.3
    )

    plt.xlim(STUDY_START, STUDY_END)

    plt.title(
        "Daily Average Heat Pump and Air-Conditioner "
        "Electrical Load per Representative Dwelling"
    )

    plt.xlabel("Date")
    plt.ylabel("Average electrical power (kW per dwelling)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_figure(
        "01_daily_average_hp_ac_load_vs_time.png"
    )


# ============================================================
# Figures 2 and 3: Hourly winter and summer weeks
# ============================================================

def plot_hourly_week(
    df,
    start_date,
    season_name,
    filename
):
    """Plot seven days of hourly load data."""

    start = pd.Timestamp(start_date)
    end = start + pd.Timedelta(days=7)

    week = df[
        (df["datetime"] >= start)
        & (df["datetime"] < end)
    ].copy()

    if week.empty:
        print(
            f"Skipped {filename}: no data for {start_date}."
        )
        return

    plt.figure(figsize=(14, 6))

    plt.plot(
        week["datetime"],
        week["hp_load_kwh_per_unit"],
        label="Heat pump",
        linewidth=1.0
    )

    plt.plot(
        week["datetime"],
        week["ac_load_kwh_per_unit"],
        label="Air conditioner",
        linewidth=1.0
    )

    plt.plot(
        week["datetime"],
        week["total_hp_ac_load_kwh_per_unit"],
        label="Total HP/AC",
        linewidth=1.3
    )

    plt.title(
        f"Hourly HP/AC Electrical Load per "
        f"Representative Dwelling — {season_name} Week"
    )

    plt.xlabel("Date and time")
    plt.ylabel("Hourly electrical energy (kWh per dwelling)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_figure(filename)


# ============================================================
# Figures 4, 5, and 6: Representative 24-hour profiles
# ============================================================

def plot_representative_day(
    df,
    date_text,
    season_name,
    filename
):
    """Plot the 24 hourly values for one selected date."""

    selected_date = pd.Timestamp(date_text).date()

    day = df[
        df["datetime"].dt.date == selected_date
    ].copy()

    if day.empty:
        print(
            f"Skipped {filename}: no data for {date_text}."
        )
        return

    day["hour"] = day["datetime"].dt.hour

    plt.figure(figsize=(10, 6))

    plt.plot(
        day["hour"],
        day["hp_load_kwh_per_unit"],
        marker="o",
        label="Heat pump"
    )

    plt.plot(
        day["hour"],
        day["ac_load_kwh_per_unit"],
        marker="o",
        label="Air conditioner"
    )

    plt.plot(
        day["hour"],
        day["total_hp_ac_load_kwh_per_unit"],
        marker="o",
        label="Total HP/AC"
    )

    plt.title(
        f"{season_name} Hourly HP/AC Load Profile "
        f"per Representative Dwelling — {date_text}"
    )

    plt.xlabel("Hour of day")
    plt.ylabel("Hourly electrical energy (kWh per dwelling)")
    plt.xticks(range(0, 24, 2))
    plt.grid(True, alpha=0.3)
    plt.legend()

    save_figure(filename)


# ============================================================
# Figure 7: Load and outdoor temperature
# ============================================================

def plot_load_and_temperature(
    df,
    date_text,
    filename
):
    """
    Compare calculated electrical load and measured outdoor
    temperature for one representative day.
    """

    selected_date = pd.Timestamp(date_text).date()

    day = df[
        df["datetime"].dt.date == selected_date
    ].copy()

    if day.empty:
        print(
            f"Skipped {filename}: no data for {date_text}."
        )
        return

    day["hour"] = day["datetime"].dt.hour

    figure, load_axis = plt.subplots(figsize=(10, 6))

    load_axis.plot(
        day["hour"],
        day["total_hp_ac_load_kwh_per_unit"],
        marker="o",
        label="Total HP/AC electrical load"
    )

    load_axis.set_xlabel("Hour of day")
    load_axis.set_ylabel(
        "Hourly electrical energy (kWh per dwelling)"
    )
    load_axis.set_xticks(range(0, 24, 2))
    load_axis.grid(True, alpha=0.3)

    temperature_axis = load_axis.twinx()

    temperature_axis.plot(
        day["hour"],
        day["outdoor_temp_c"],
        marker="s",
        linestyle="--",
        label="Outdoor temperature"
    )

    temperature_axis.set_ylabel("Outdoor temperature (°C)")

    load_lines, load_labels = (
        load_axis.get_legend_handles_labels()
    )

    temperature_lines, temperature_labels = (
        temperature_axis.get_legend_handles_labels()
    )

    load_axis.legend(
        load_lines + temperature_lines,
        load_labels + temperature_labels,
        loc="upper right"
    )

    plt.title(
        f"Calculated HP/AC Load and Outdoor Temperature "
        f"— {date_text}"
    )

    output_path = GRAPH_FOLDER / filename

    figure.tight_layout()
    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    print(f"Saved: {output_path}")


# ============================================================
# Optional data-quality summary
# ============================================================

def print_quality_summary(df):
    """Print useful checks before creating the figures."""

    expected_hours = int(
        (
            STUDY_END.floor("D")
            - STUDY_START.floor("D")
        ).days
        + 1
    ) * 24

    actual_hours = df["datetime"].nunique()

    print("\nData-quality check")
    print("------------------")
    print(f"Expected hours: {expected_hours}")
    print(f"Available unique hours: {actual_hours}")
    print(f"Missing hours: {expected_hours - actual_hours}")

    coldest_row = df.loc[df["outdoor_temp_c"].idxmin()]

    highest_load_row = df.loc[
        df["total_hp_ac_load_kwh_per_unit"].idxmax()
    ]

    print(
        f"Coldest temperature: "
        f"{coldest_row['outdoor_temp_c']:.1f} °C "
        f"at {coldest_row['datetime']}"
    )

    print(
        f"Highest calculated load: "
        f"{highest_load_row['total_hp_ac_load_kwh_per_unit']:.3f} kWh "
        f"at {highest_load_row['datetime']}"
    )

    print()


# ============================================================
# Run all graphs
# ============================================================

def main():
    print("Creating final load-versus-time figures...\n")

    df = load_results()

    print_quality_summary(df)

    # Full study-period trend
    plot_daily_average_load(df)

    # Selected hourly weeks
    plot_hourly_week(
        df=df,
        start_date="2024-01-15",
        season_name="Winter",
        filename="02_hourly_winter_week.png"
    )

    plot_hourly_week(
        df=df,
        start_date="2024-07-15",
        season_name="Summer",
        filename="03_hourly_summer_week.png"
    )

    # Representative days
    plot_representative_day(
        df=df,
        date_text="2024-01-15",
        season_name="Winter",
        filename="04_representative_winter_day.png"
    )

    plot_representative_day(
        df=df,
        date_text="2024-07-15",
        season_name="Summer",
        filename="05_representative_summer_day.png"
    )

    plot_representative_day(
        df=df,
        date_text="2024-10-15",
        season_name="Shoulder-Season",
        filename="06_representative_shoulder_day.png"
    )

    # Load-temperature comparison
    plot_load_and_temperature(
        df=df,
        date_text="2024-01-15",
        filename="07_winter_load_and_temperature.png"
    )

    print("\nFinished.")
    print(f"Graphs saved in:\n{GRAPH_FOLDER}")


if __name__ == "__main__":
    main()