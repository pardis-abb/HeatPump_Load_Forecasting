import numpy as np
import pandas as pd


def estimate_calgary_supported_installations(
    alberta_supported_installations: float,
    calgary_population_share_of_alberta: float,
) -> float:
    """
    Estimate Calgary's share of Alberta-supported installations.

    This does not represent the exact total number of heat pumps
    installed in Calgary.
    """

    return (
        alberta_supported_installations
        * calgary_population_share_of_alberta
    )


def add_aggregate_heat_pump_load(
    formulation_results: pd.DataFrame,
    number_of_heat_pumps: float,
) -> pd.DataFrame:
    """
    Scale one-unit heat-pump demand to all estimated Calgary units.
    """

    results = formulation_results.copy()

    per_unit_columns = [
        column
        for column in results.columns
        if column.startswith("HP_load_")
        and column.endswith("_kW_per_unit")
    ]

    for per_unit_column in per_unit_columns:
        formulation_name = (
            per_unit_column
            .replace("HP_load_", "")
            .replace("_kW_per_unit", "")
        )

        total_load_column = (
            f"total_HP_load_{formulation_name}_MW"
        )

        modifier_column = (
            f"HP_modifier_{formulation_name}_percent"
        )

        modified_forecast_column = (
            f"modified_forecast_{formulation_name}_MW"
        )

        results[total_load_column] = (
            results[per_unit_column]
            * number_of_heat_pumps
            / 1000.0
        )

        if "calgary_load_MW" in results.columns:
            results[modifier_column] = np.where(
                results["calgary_load_MW"] > 0,
                (
                    100.0
                    * results[total_load_column]
                    / results["calgary_load_MW"]
                ),
                np.nan,
            )

            results[modified_forecast_column] = (
                results["calgary_load_MW"]
                + results[total_load_column]
            )

    results["estimated_Calgary_HP_count"] = (
        number_of_heat_pumps
    )

    return results