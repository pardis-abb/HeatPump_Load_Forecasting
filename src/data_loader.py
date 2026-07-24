from pathlib import Path

import pandas as pd


def read_csv_file(file_path: Path) -> pd.DataFrame:
    """
    Read a CSV file and convert its datetime column.
    """

    if not file_path.exists():
        raise FileNotFoundError(f"Could not find file: {file_path}")

    data = pd.read_csv(file_path)

    if "datetime" not in data.columns:
        raise ValueError(
            f"{file_path.name} must contain a column called 'datetime'."
        )

    data["datetime"] = pd.to_datetime(
        data["datetime"],
        errors="coerce",
    )

    data = data.dropna(subset=["datetime"])
    data = data.drop_duplicates(subset=["datetime"])
    data = data.sort_values("datetime").reset_index(drop=True)

    return data


def load_multiple_weather_files(
    weather_files: list[Path],
) -> pd.DataFrame:
    """
    Load and combine multiple Environment Canada hourly
    weather CSV files.

    The files are expected to contain columns such as:
        Date/Time (LST)
        Temp (°C)

    The returned data contains:
        datetime
        outside_temperature_C
    """

    if not weather_files:
        raise FileNotFoundError(
            "No weather CSV files were found."
        )

    all_weather_data = []

    for weather_file in weather_files:
        print(f"Reading weather file: {weather_file.name}")

        data = pd.read_csv(
            weather_file,
            low_memory=False,
        )

        # Environment Canada files may use one of these
        # datetime column names.
        possible_datetime_columns = [
            "Date/Time (LST)",
            "Date/Time",
            "LOCAL_DATE",
            "datetime",
        ]

        datetime_column = None

        for column in possible_datetime_columns:
            if column in data.columns:
                datetime_column = column
                break

        if datetime_column is None:
            raise ValueError(
                f"No datetime column was found in "
                f"{weather_file.name}."
            )

        # Environment Canada usually uses Temp (°C).
        possible_temperature_columns = [
            "Temp (°C)",
            "Temperature (°C)",
            "outside_temperature_C",
        ]

        temperature_column = None

        for column in possible_temperature_columns:
            if column in data.columns:
                temperature_column = column
                break

        if temperature_column is None:
            raise ValueError(
                f"No temperature column was found in "
                f"{weather_file.name}."
            )

        cleaned_data = data[
            [
                datetime_column,
                temperature_column,
            ]
        ].copy()

        cleaned_data = cleaned_data.rename(
            columns={
                datetime_column: "datetime",
                temperature_column:
                    "outside_temperature_C",
            }
        )

        cleaned_data["datetime"] = pd.to_datetime(
            cleaned_data["datetime"],
            errors="coerce",
        )

        cleaned_data[
            "outside_temperature_C"
        ] = pd.to_numeric(
            cleaned_data[
                "outside_temperature_C"
            ],
            errors="coerce",
        )

        cleaned_data = cleaned_data.dropna(
            subset=[
                "datetime",
                "outside_temperature_C",
            ]
        )

        all_weather_data.append(cleaned_data)

    combined_weather_data = pd.concat(
        all_weather_data,
        ignore_index=True,
    )

    combined_weather_data = (
        combined_weather_data
        .drop_duplicates(subset=["datetime"])
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    print(
        f"Combined {len(weather_files)} weather files "
        f"into {len(combined_weather_data):,} hourly rows."
    )

    return combined_weather_data

def load_electricity_data(
    file_path: Path,
    calgary_area_column: str,
) -> pd.DataFrame:
    """
    Load AESO hourly area-load data from Excel and keep only
    the Calgary area column.

    Required workbook columns:
        DT_MST
        selected AREA column
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Could not find electricity-load file: {file_path}"
        )

    data = pd.read_excel(
        file_path,
        engine="openpyxl",
    )

    data.columns = (
        data.columns
        .astype(str)
        .str.strip()
    )

    if "DT_MST" not in data.columns:
        raise ValueError(
            "The electricity workbook does not contain "
            "the expected 'DT_MST' column."
        )

    if calgary_area_column not in data.columns:
        raise ValueError(
            f"The selected Calgary area column "
            f"'{calgary_area_column}' was not found.\n"
            f"Available columns are:\n{list(data.columns)}"
        )

    electricity_data = data[
        [
            "DT_MST",
            calgary_area_column,
        ]
    ].copy()

    electricity_data = electricity_data.rename(
        columns={
            "DT_MST": "datetime",
            calgary_area_column: "calgary_load_MW",
        }
    )

    electricity_data["datetime"] = pd.to_datetime(
        electricity_data["datetime"],
        errors="coerce",
    )

    electricity_data["calgary_load_MW"] = pd.to_numeric(
        electricity_data["calgary_load_MW"],
        errors="coerce",
    )

    electricity_data = electricity_data.dropna(
        subset=[
            "datetime",
            "calgary_load_MW",
        ]
    )

    electricity_data = (
        electricity_data
        .drop_duplicates(subset=["datetime"])
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    print(
        f"Loaded {len(electricity_data):,} hourly rows "
        f"from {calgary_area_column}."
    )

    return electricity_data


def load_validation_data(file_path: Path) -> pd.DataFrame:
    """
    Load the database used to prove the heat-pump model.

    Required columns:
        datetime
        outside_temperature_C
        measured_hp_load_kW_per_unit
    """

    data = read_csv_file(file_path)

    required_columns = {
        "datetime",
        "outside_temperature_C",
        "measured_hp_load_kW_per_unit",
    }

    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            "Validation data is missing columns: "
            f"{sorted(missing_columns)}"
        )

    numeric_columns = [
        "outside_temperature_C",
        "measured_hp_load_kW_per_unit",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data = data.dropna(subset=numeric_columns)

    return data


def merge_weather_and_electricity_load(
    weather_data: pd.DataFrame,
    electricity_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge weather and electricity load using matching timestamps.
    """

    merged_data = pd.merge(
        weather_data,
        electricity_data,
        on="datetime",
        how="inner",
    )

    if merged_data.empty:
        raise ValueError(
            "No matching timestamps were found between the "
            "weather data and electricity-load data."
        )

    return merged_data.sort_values("datetime").reset_index(drop=True)