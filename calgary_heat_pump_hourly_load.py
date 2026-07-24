from pathlib import Path

import pandas as pd

from config import (
    ALBERTA_SUPPORTED_INSTALLATIONS,
    APPROACH_TEMPERATURE_C,
    BALANCE_TEMPERATURE_C,
    CALGARY_POPULATION_SHARE_OF_ALBERTA,
    ELECTRICITY_LOAD_DIR,
    FORMULATION_RESULTS_DIR,
    GRAPHS_DIR,
    INDOOR_TEMPERATURE_C,
    MAXIMUM_COP,
    MINIMUM_COP,
    REFRIGERATION_EFFICIENCY,
    SCENARIOS,
    SCENARIO_RESULTS_DIR,
    UA_HEATING_KW_PER_C,
    VALIDATION_DATA_DIR,
    VALIDATION_RESULTS_DIR,
    WEATHER_DATA_DIR,
    create_output_folders,
)

from src.adoption_model import (
    add_aggregate_heat_pump_load,
    estimate_calgary_supported_installations,
)

from src.data_loader import (
    load_electricity_data,
    load_multiple_weather_files,
    load_validation_data,
    merge_weather_and_electricity_load,
)

from src.formulations import calculate_all_formulations

from src.plotting import (
    plot_aggregate_heat_pump_load,
    plot_formulation_comparison,
    plot_validation_results,
)

from src.scenarios import run_scenario_analysis
from src.validation import validate_models


# ============================================================
# CHANGE THESE FILENAMES TO MATCH YOUR REAL FILES
# ============================================================

WEATHER_FILES = sorted(
    WEATHER_DATA_DIR.glob("en_climate_hourly_AB_*.csv")
)

ELECTRICITY_LOAD_FILE = (
    ELECTRICITY_LOAD_DIR
    / "Hourly-load-by-area-and-region-Nov-2023-to-Dec-2024 (1).xlsx"
)
CALGARY_AREA_COLUMN = "AREA13"

VALIDATION_FILE = (
    VALIDATION_DATA_DIR
    / "heat_pump_validation_database.csv"
)


def main() -> None:
    """
    Run the complete Calgary heat-pump load-modifier workflow.
    """

    print("Starting heat-pump load-modifier model...")

    create_output_folders()

    # --------------------------------------------------------
    # STEP 1: LOAD WEATHER AND ELECTRICITY DATA
    # --------------------------------------------------------

    weather_data = load_multiple_weather_files(
    WEATHER_FILES
)

    electricity_load_data = load_electricity_data(
    ELECTRICITY_LOAD_FILE,
    CALGARY_AREA_COLUMN,
)

    base_data = merge_weather_and_electricity_load(
        weather_data,
        electricity_load_data,
    )

    print(
        f"Loaded {len(base_data):,} matching hourly rows."
    )

    # --------------------------------------------------------
    # STEP 2: PROVE THE MODEL USING THE DATABASE
    # --------------------------------------------------------

    empirical_coefficients = None

    if VALIDATION_FILE.exists():
        validation_data = load_validation_data(
            VALIDATION_FILE
        )

        (
            validation_results,
            empirical_coefficients,
        ) = validate_models(
            validation_data=validation_data,
            output_folder=VALIDATION_RESULTS_DIR,
            indoor_temperature_c=INDOOR_TEMPERATURE_C,
            balance_temperature_c=BALANCE_TEMPERATURE_C,
            approach_temperature_c=APPROACH_TEMPERATURE_C,
            refrigeration_efficiency=
                REFRIGERATION_EFFICIENCY,
            ua_heating_kw_per_c=
                UA_HEATING_KW_PER_C,
            minimum_cop=MINIMUM_COP,
            maximum_cop=MAXIMUM_COP,
        )

        plot_validation_results(
            validation_results,
            VALIDATION_RESULTS_DIR,
        )

        print("Model-validation step completed.")

    else:
        print(
            "Validation database was not found. "
            "Lorenz and Carnot will still run, but the "
            "empirical formulation and model-proof step "
            "will be skipped."
        )

    # --------------------------------------------------------
    # STEP 3: CALCULATE ALL FORMULATIONS
    # --------------------------------------------------------

    formulation_results = calculate_all_formulations(
        data=base_data,
        indoor_temperature_c=INDOOR_TEMPERATURE_C,
        balance_temperature_c=BALANCE_TEMPERATURE_C,
        approach_temperature_c=APPROACH_TEMPERATURE_C,
        refrigeration_efficiency=
            REFRIGERATION_EFFICIENCY,
        ua_heating_kw_per_c=
            UA_HEATING_KW_PER_C,
        minimum_cop=MINIMUM_COP,
        maximum_cop=MAXIMUM_COP,
        empirical_coefficients=empirical_coefficients,
    )

    # --------------------------------------------------------
    # STEP 4: ESTIMATE CALGARY HEAT-PUMP INSTALLATIONS
    # --------------------------------------------------------

    estimated_calgary_heat_pumps = (
        estimate_calgary_supported_installations(
            alberta_supported_installations=
                ALBERTA_SUPPORTED_INSTALLATIONS,
            calgary_population_share_of_alberta=
                CALGARY_POPULATION_SHARE_OF_ALBERTA,
        )
    )

    print(
        "Estimated Calgary supported installations: "
        f"{estimated_calgary_heat_pumps:,.2f}"
    )

    # --------------------------------------------------------
    # STEP 5: CALCULATE AGGREGATE LOAD AND LOAD MODIFIER
    # --------------------------------------------------------

    final_results = add_aggregate_heat_pump_load(
        formulation_results,
        estimated_calgary_heat_pumps,
    )

    final_results.to_csv(
        FORMULATION_RESULTS_DIR
        / "hourly_heat_pump_load_modifier.csv",
        index=False,
    )

    # --------------------------------------------------------
    # STEP 6: SCENARIO ANALYSIS
    # --------------------------------------------------------

    scenario_results = run_scenario_analysis(
        base_data=base_data,
        scenarios=SCENARIOS,
        base_installation_count=
            estimated_calgary_heat_pumps,
        balance_temperature_c=
            BALANCE_TEMPERATURE_C,
        approach_temperature_c=
            APPROACH_TEMPERATURE_C,
        minimum_cop=MINIMUM_COP,
        maximum_cop=MAXIMUM_COP,
        empirical_coefficients=empirical_coefficients,
    )

    scenario_results.to_csv(
        SCENARIO_RESULTS_DIR
        / "scenario_summary.csv",
        index=False,
    )

    # --------------------------------------------------------
    # STEP 7: CREATE GRAPHS
    # --------------------------------------------------------

    plot_formulation_comparison(
        final_results,
        GRAPHS_DIR,
    )

    plot_aggregate_heat_pump_load(
        final_results,
        GRAPHS_DIR,
    )

    print("\nModel completed successfully.")
    print(
        "Hourly results saved in: "
        f"{FORMULATION_RESULTS_DIR}"
    )
    print(
        "Scenario results saved in: "
        f"{SCENARIO_RESULTS_DIR}"
    )
    print(
        "Graphs saved in: "
        f"{GRAPHS_DIR}"
    )


if __name__ == "__main__":
    main()