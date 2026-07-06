from pathlib import Path
import pandas as pd


T_BASE_C = 18.0
T_ROOM_C = 21.0
DELTA_T = 5.0
ETA_R = 0.8

UAH = 0.125   # kW/°C
UAC = 0.163   # kW/°C

HOURS = 1

WEATHER_FOLDER = Path("datasets/weather_data")
RESULTS_FOLDER = Path("results")
RESULTS_FOLDER.mkdir(exist_ok=True)


def find_temperature_column(dataframe):
    possible_columns = [
        "Temp (°C)",
        "Temp (C)",
        "Temperature",
        "Temperature (°C)",
        "temperature",
        "temp",
    ]

    for column in possible_columns:
        if column in dataframe.columns:
            return column

    for column in dataframe.columns:
        if "temp" in column.lower():
            return column

    raise ValueError("No temperature column found.")


def calculate_cop(outdoor_temp_c):
    outdoor_k = outdoor_temp_c + 273.15
    indoor_k = T_ROOM_C + 273.15

    temperature_difference = abs(indoor_k - outdoor_k)

    if temperature_difference == 0:
        return None

    cop = (indoor_k - DELTA_T / 2) / (temperature_difference + DELTA_T)

    return cop


def calculate_loads_for_row(row, temp_column):
    outdoor_temp_c = row[temp_column]

    if pd.isna(outdoor_temp_c):
        return pd.Series({
            "COP": None,
            "Q_heat_kW": None,
            "Q_cool_kW": None,
            "HP_load_kWh_per_unit": None,
            "AC_load_kWh_per_unit": None,
            "Total_HP_AC_load_kWh_per_unit": None,
        })

    cop = calculate_cop(outdoor_temp_c)

    if cop is None or cop <= 0:
        return pd.Series({
            "COP": cop,
            "Q_heat_kW": None,
            "Q_cool_kW": None,
            "HP_load_kWh_per_unit": None,
            "AC_load_kWh_per_unit": None,
            "Total_HP_AC_load_kWh_per_unit": None,
        })

    q_heat = max(UAH * (T_BASE_C - outdoor_temp_c), 0)
    q_cool = max(UAC * (outdoor_temp_c - T_BASE_C), 0)

    hp_load = (q_heat / (ETA_R * cop)) * HOURS if q_heat > 0 else 0
    ac_load = (q_cool / (ETA_R * cop)) * HOURS if q_cool > 0 else 0

    total_load = hp_load + ac_load

    return pd.Series({
        "COP": cop,
        "Q_heat_kW": q_heat,
        "Q_cool_kW": q_cool,
        "HP_load_kWh_per_unit": hp_load,
        "AC_load_kWh_per_unit": ac_load,
        "Total_HP_AC_load_kWh_per_unit": total_load,
    })


def process_weather_database():
    weather_files = list(WEATHER_FOLDER.glob("*.csv"))

    if not weather_files:
        print("No CSV files found in datasets/weather_data/")
        return

    all_results = []

    for file_path in weather_files:
        print(f"Processing: {file_path.name}")

        weather_df = pd.read_csv(file_path)

        temp_column = find_temperature_column(weather_df)

        calculations = weather_df.apply(
            calculate_loads_for_row,
            axis=1,
            temp_column=temp_column
        )

        result = pd.concat([weather_df, calculations], axis=1)
        result["source_file"] = file_path.name

        all_results.append(result)

        individual_output = RESULTS_FOLDER / f"{file_path.stem}_hp_ac_results.csv"
        result.to_csv(individual_output, index=False)

    final_results = pd.concat(all_results, ignore_index=True)

    final_output = RESULTS_FOLDER / "combined_hourly_hp_ac_load_results.csv"
    final_results.to_csv(final_output, index=False)

    print("\nDone.")
    print(f"Combined results saved to: {final_output}")
    print("Individual file results were also saved in the results folder.")


if __name__ == "__main__":
    process_weather_database()
