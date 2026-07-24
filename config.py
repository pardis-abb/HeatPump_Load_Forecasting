from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DATASETS_DIR = PROJECT_ROOT / "datasets"

WEATHER_DATA_DIR = DATASETS_DIR / "weather_data"
ELECTRICITY_LOAD_DIR = DATASETS_DIR / "electricity_load"
HEAT_PUMP_DATA_DIR = DATASETS_DIR / "heat_pump_data"
VALIDATION_DATA_DIR = DATASETS_DIR / "validation_data"
MARKET_DATA_DIR = DATASETS_DIR / "market_data"

RESULTS_DIR = PROJECT_ROOT / "results"
GRAPHS_DIR = RESULTS_DIR / "graphs"
VALIDATION_RESULTS_DIR = RESULTS_DIR / "validation"
FORMULATION_RESULTS_DIR = RESULTS_DIR / "formulations"
SCENARIO_RESULTS_DIR = RESULTS_DIR / "scenarios"


# ============================================================
# MODEL PARAMETERS
# ============================================================

INDOOR_TEMPERATURE_C = 21.0
BALANCE_TEMPERATURE_C = 18.0
APPROACH_TEMPERATURE_C = 5.0

REFRIGERATION_EFFICIENCY = 0.80

# Heating UA value from the original methodology.
# Replace when an updated, better-supported average is available.
UA_HEATING_KW_PER_C = 0.125

MINIMUM_COP = 1.0
MAXIMUM_COP = 100

HOURS_PER_TIMESTEP = 1.0


# ============================================================
# HEAT-PUMP INSTALLATION ASSUMPTIONS
# ============================================================

# The 1,215 value represents installations supported through
# named programs in Alberta from 2020 to June 2024.
# It is not the total number of all Alberta heat pumps in 2023.
ALBERTA_SUPPORTED_INSTALLATIONS = 1215

# Replace with the exact population share you decide to use.
CALGARY_POPULATION_SHARE_OF_ALBERTA = 0.35

# This will produce approximately 425 supported installations.
CALGARY_SUPPORTED_INSTALLATIONS = (
    ALBERTA_SUPPORTED_INSTALLATIONS
    * CALGARY_POPULATION_SHARE_OF_ALBERTA
)


# ============================================================
# SCENARIO PARAMETERS
# ============================================================

SCENARIOS = {
    "P10": {
        "installation_multiplier": 0.75,
        "ua_heating_kw_per_c": 0.100,
        "refrigeration_efficiency": 0.70,
        "indoor_temperature_c": 20.0,
        "temperature_shift_c": 2.0,
    },
    "P50": {
        "installation_multiplier": 1.00,
        "ua_heating_kw_per_c": 0.125,
        "refrigeration_efficiency": 0.80,
        "indoor_temperature_c": 21.0,
        "temperature_shift_c": 0.0,
    },
    "P90": {
        "installation_multiplier": 1.50,
        "ua_heating_kw_per_c": 0.150,
        "refrigeration_efficiency": 0.75,
        "indoor_temperature_c": 22.0,
        "temperature_shift_c": -3.0,
    },
}


def create_output_folders() -> None:
    """Create result folders when they do not already exist."""

    folders = [
        RESULTS_DIR,
        GRAPHS_DIR,
        VALIDATION_RESULTS_DIR,
        FORMULATION_RESULTS_DIR,
        SCENARIO_RESULTS_DIR,
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)