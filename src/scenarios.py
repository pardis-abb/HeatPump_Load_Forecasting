import pandas as pd

from src.adoption_model import add_aggregate_heat_pump_load
from src.formulations import calculate_all_formulations


def run_scenario_analysis(
    base_data: pd.DataFrame,
    scenarios: dict,
    base_installation_count: float,
    balance_temperature_c: float,
    approach_temperature_c: float,
    minimum_cop: float,
    maximum_cop: float,
    empirical_coefficients=None,
) -> pd.DataFrame:
    """
    Run P10, P50 and P90 scenario analysis.
    """

    summary_rows = []

    for scenario_name, parameters in scenarios.items():
        scenario_data = base_data.copy()

        scenario_data["outside_temperature_C"] = (
            scenario_data["outside_temperature_C"]
            + parameters["temperature_shift_c"]
        )

        formulation_results = calculate_all_formulations(
            data=scenario_data,
            indoor_temperature_c=parameters[
                "indoor_temperature_c"
            ],
            balance_temperature_c=balance_temperature_c,
            approach_temperature_c=approach_temperature_c,
            refrigeration_efficiency=parameters[
                "refrigeration_efficiency"
            ],
            ua_heating_kw_per_c=parameters[
                "ua_heating_kw_per_c"
            ],
            minimum_cop=minimum_cop,
            maximum_cop=maximum_cop,
            empirical_coefficients=empirical_coefficients,
        )

        scenario_installation_count = (
            base_installation_count
            * parameters["installation_multiplier"]
        )

        aggregate_results = add_aggregate_heat_pump_load(
            formulation_results,
            scenario_installation_count,
        )

        total_load_columns = [
            column
            for column in aggregate_results.columns
            if column.startswith("total_HP_load_")
            and column.endswith("_MW")
        ]

        for total_load_column in total_load_columns:
            formulation_name = (
                total_load_column
                .replace("total_HP_load_", "")
                .replace("_MW", "")
            )

            modifier_column = (
                f"HP_modifier_{formulation_name}_percent"
            )

            peak_index = aggregate_results[
                total_load_column
            ].idxmax()

            summary_rows.append(
                {
                    "scenario": scenario_name,
                    "formulation": formulation_name,
                    "estimated_Calgary_HP_count":
                        scenario_installation_count,
                    "annual_energy_GWh":
                        aggregate_results[
                            total_load_column
                        ].sum()
                        / 1000.0,
                    "peak_load_MW":
                        aggregate_results[
                            total_load_column
                        ].max(),
                    "peak_datetime":
                        aggregate_results.loc[
                            peak_index,
                            "datetime",
                        ],
                    "average_modifier_percent":
                        aggregate_results[
                            modifier_column
                        ].mean(),
                    "peak_modifier_percent":
                        aggregate_results[
                            modifier_column
                        ].max(),
                }
            )

    return pd.DataFrame(summary_rows)