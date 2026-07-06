from pathlib import Path
import pandas as pd
import numpy as np

# -----------------------------
# Assumptions from paper / HOT2000
# -----------------------------

T_BASE_C = 18.0

UAH = 0.125   # kW/°C, from 125 W/°C
UAC = 0.163   # kW/°C, from 163 W/°C

ETA_R = 0.8

# HOT2000 report values
RATED_HEATING_COP = 3.84
RATED_COOLING_COP = 4.303

# Installed units placeholder
# Change these when you find real HP/AC adoption numbers
INSTALLED_HEAT_PUMPS = 1
INSTALLED_AIR_CONDITIONERS = 1

BASE_DIR = Path(__file__).resolve().parent
WEATHER_FOLDER = BASE_DIR / "datasets" / "weather_data"
ELECTRICITY_FOLDER = BASE_DIR / "datasets" / "electricity_load"
RESULTS_FOLDER = BASE_DIR / "results"
RESULTS_FOLDER.mkdir(exist_ok=True)


# -----------------------------
# Read weather data
# -----------------------------

def read_weather():
    files = list(WEATHER_FOLDER.glob("*.csv"))

    if not files:
        raise FileNotFoundError("No weather CSV files found.")

    all_data = []

    for file in files:
        print(f"Reading weather file: {file.name}")
        df = pd.read_csv(file)

        temp_col = None
        for col in df.columns:
            if "temp" in col.lower() and "dew" not in col.lower():
                temp_col = col
                break

        if temp_col is None:
            raise ValueError("Could not find temperature column.")

        date_col = None
        for col in df.columns:
            if "date/time" in col.lower() or col.lower() in ["datetime", "date"]:
                date_col = col
                break

        if date_col is None:
            raise ValueError("Could not find date/time column.")

        clean = pd.DataFrame()
        clean["datetime"] = pd.to_datetime(df[date_col], errors="coerce")
        clean["outdoor_temp_c"] = pd.to_numeric(df[temp_col], errors="coerce")
        clean["weather_source_file"] = file.name

        clean = clean.dropna(subset=["datetime", "outdoor_temp_c"])
        all_data.append(clean)

    return pd.concat(all_data, ignore_index=True)


# -----------------------------
# Read AESO load data
# -----------------------------

def read_aeso_load():
    files = list(ELECTRICITY_FOLDER.glob("*.xlsx"))

    if not files:
        print("No AESO Excel file found. Skipping AESO comparison.")
        return None

    file = files[0]
    print(f"Reading AESO file: {file.name}")

    df = pd.read_excel(file)

    datetime_col = None
    for col in df.columns:
        if "dt" in col.lower() or "date" in col.lower() or "time" in col.lower():
            datetime_col = col
            break

    calgary_col = None
    for col in df.columns:
        if "calgary" in col.lower():
            calgary_col = col
            break

    if datetime_col is None or calgary_col is None:
        print("Could not find datetime or Calgary load column in AESO file.")
        return None

    load = pd.DataFrame()
    load["datetime"] = pd.to_datetime(df[datetime_col], errors="coerce")
    load["calgary_aeso_load_mw"] = pd.to_numeric(df[calgary_col], errors="coerce")

    load = load.dropna(subset=["datetime", "calgary_aeso_load_mw"])

    return load


# -----------------------------
# COP model
# -----------------------------

def heating_cop(temp_c):
    """
    More realistic temperature-adjusted COP.
    Uses HOT2000 rated COP as the base.
    COP decreases in colder weather.
    """

    cop = RATED_HEATING_COP - 0.04 * (8.3 - temp_c)

    return max(1.5, min(cop, 5.0))


def cooling_cop(temp_c):
    """
    More realistic cooling COP.
    Uses HOT2000 AC rated COP as the base.
    COP decreases when outdoor temperature gets hotter.
    """

    cop = RATED_COOLING_COP - 0.03 * (temp_c - 25.0)

    return max(2.0, min(cop, 5.0))


# -----------------------------
# Main calculations
# -----------------------------

def calculate_hp_ac_load(weather):
    df = weather.copy()

    df["q_heat_kw"] = UAH * np.maximum(T_BASE_C - df["outdoor_temp_c"], 0)
    df["q_cool_kw"] = UAC * np.maximum(df["outdoor_temp_c"] - T_BASE_C, 0)

    df["cop_heating"] = df["outdoor_temp_c"].apply(heating_cop)
    df["cop_cooling"] = df["outdoor_temp_c"].apply(cooling_cop)

    df["hp_load_kwh_per_unit"] = np.where(
        df["q_heat_kw"] > 0,
        df["q_heat_kw"] / (ETA_R * df["cop_heating"]),
        0
    )

    df["ac_load_kwh_per_unit"] = np.where(
        df["q_cool_kw"] > 0,
        df["q_cool_kw"] / (ETA_R * df["cop_cooling"]),
        0
    )

    df["total_hp_ac_load_kwh_per_unit"] = (
        df["hp_load_kwh_per_unit"] + df["ac_load_kwh_per_unit"]
    )

    df["installed_heat_pumps"] = INSTALLED_HEAT_PUMPS
    df["installed_air_conditioners"] = INSTALLED_AIR_CONDITIONERS

    df["city_hp_load_mwh"] = (
        df["hp_load_kwh_per_unit"] * INSTALLED_HEAT_PUMPS / 1000
    )

    df["city_ac_load_mwh"] = (
        df["ac_load_kwh_per_unit"] * INSTALLED_AIR_CONDITIONERS / 1000
    )

    df["city_total_hp_ac_load_mwh"] = (
        df["city_hp_load_mwh"] + df["city_ac_load_mwh"]
    )

    return df


# -----------------------------
# Merge with AESO
# -----------------------------

def merge_with_aeso(model, aeso):
    if aeso is None:
        model["calgary_aeso_load_mw"] = np.nan
        model["load_modifier_percent"] = np.nan
        return model

    model = model.copy()
    aeso = aeso.copy()

    model["datetime_hour"] = model["datetime"].dt.floor("h")
    aeso["datetime_hour"] = aeso["datetime"].dt.floor("h")

    merged = model.merge(
        aeso[["datetime_hour", "calgary_aeso_load_mw"]],
        on="datetime_hour",
        how="left"
    )

    merged["load_modifier_percent"] = np.where(
        merged["calgary_aeso_load_mw"] > 0,
        merged["city_total_hp_ac_load_mwh"] / merged["calgary_aeso_load_mw"] * 100,
        np.nan
    )

    return merged


# -----------------------------
# Monthly summary
# -----------------------------

def monthly_summary(results):
    df = results.copy()
    df["month"] = df["datetime"].dt.to_period("M").astype(str)

    summary = df.groupby("month").agg(
        avg_temp_c=("outdoor_temp_c", "mean"),
        avg_heating_cop=("cop_heating", "mean"),
        avg_cooling_cop=("cop_cooling", "mean"),
        total_hp_load_mwh=("city_hp_load_mwh", "sum"),
        total_ac_load_mwh=("city_ac_load_mwh", "sum"),
        total_hp_ac_load_mwh=("city_total_hp_ac_load_mwh", "sum"),
        avg_aeso_load_mw=("calgary_aeso_load_mw", "mean"),
        avg_load_modifier_percent=("load_modifier_percent", "mean"),
        max_load_modifier_percent=("load_modifier_percent", "max")
    ).reset_index()

    return summary


# -----------------------------
# Run model
# -----------------------------

def main():
    print("Starting full HP/AC load modifier model...")

    weather = read_weather()
    aeso = read_aeso_load()

    model = calculate_hp_ac_load(weather)
    results = merge_with_aeso(model, aeso)
    summary = monthly_summary(results)

    results.to_csv(RESULTS_FOLDER / "hourly_hp_ac_load_modifier_results.csv", index=False)
    summary.to_csv(RESULTS_FOLDER / "monthly_hp_ac_load_modifier_summary.csv", index=False)

    print("\nDone.")
    print("Saved:")
    print("results/hourly_hp_ac_load_modifier_results.csv")
    print("results/monthly_hp_ac_load_modifier_summary.csv")
    print("\nPreview:")
    print(summary.head())


if __name__ == "__main__":
    main()