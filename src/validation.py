from pathlib import Path

import numpy as np
import pandas as pd

from src.formulations import (
    calculate_all_formulations,
    fit_empirical_model,
)


def calculate_validation_metrics(
    measured: pd.Series,
    modelled: pd.Series,
) -> dict:
    """
    Calculate model-validation statistics.
    """

    comparison = pd.DataFrame(
        {
            "measured": measured,
            "modelled": modelled,
        }
    ).dropna()

    if comparison.empty:
        raise ValueError(
            "No valid measured and modelled values were available."
        )

    error = (
        comparison["modelled"]
        - comparison["measured"]
    )

    nonzero_measured = (
        comparison["measured"].abs() > 1e-9
    )

    metrics = {
        "number_of_observations": len(comparison),
        "MAE_kW": error.abs().mean(),
        "RMSE_kW": np.sqrt((error**2).mean()),
        "MBE_kW": error.mean(),
        "correlation": comparison[
            "measured"
        ].corr(comparison["modelled"]),
        "measured_total_kWh": comparison[
            "measured"
        ].sum(),
        "modelled_total_kWh": comparison[
            "modelled"
        ].sum(),
    }

    if nonzero_measured.any():
        metrics["MAPE_percent"] = (
            (
                error[nonzero_measured].abs()
                / comparison.loc[
                    nonzero_measured,
                    "measured",
                ].abs()
            ).mean()
            * 100.0
        )
    else:
        metrics["MAPE_percent"] = np.nan

    measured_total = metrics["measured_total_kWh"]

    if abs(measured_total) > 1e-9:
        metrics["total_energy_difference_percent"] = (
            100.0
            * (
                metrics["modelled_total_kWh"]
                - measured_total
            )
            / measured_total
        )
    else:
        metrics["total_energy_difference_percent"] = np.nan

    return metrics


def validate_models(
    validation_data: pd.DataFrame,
    output_folder: Path,
    indoor_temperature_c: float,
    balance_temperature_c: float,
    approach_temperature_c: float,
    refrigeration_efficiency: float,
    ua_heating_kw_per_c: float,
    minimum_cop: float,
    maximum_cop: float,
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Validate Lorenz, Carnot and empirical formulations.
    """

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    empirical_coefficients = fit_empirical_model(
        validation_data,
        polynomial_degree=2,
    )

    model_results = calculate_all_formulations(
        data=validation_data[
            [
                "datetime",
                "outside_temperature_C",
            ]
        ].copy(),
        indoor_temperature_c=indoor_temperature_c,
        balance_temperature_c=balance_temperature_c,
        approach_temperature_c=approach_temperature_c,
        refrigeration_efficiency=refrigeration_efficiency,
        ua_heating_kw_per_c=ua_heating_kw_per_c,
        minimum_cop=minimum_cop,
        maximum_cop=maximum_cop,
        empirical_coefficients=empirical_coefficients,
    )

    model_results[
        "measured_hp_load_kW_per_unit"
    ] = validation_data[
        "measured_hp_load_kW_per_unit"
    ].to_numpy()

    metric_rows = []

    formulation_columns = {
        "Lorenz": "HP_load_Lorenz_kW_per_unit",
        "Carnot": "HP_load_Carnot_kW_per_unit",
        "Empirical": "HP_load_Empirical_kW_per_unit",
    }

    for formulation, column in formulation_columns.items():
        metrics = calculate_validation_metrics(
            model_results[
                "measured_hp_load_kW_per_unit"
            ],
            model_results[column],
        )

        metrics["formulation"] = formulation
        metric_rows.append(metrics)

    metrics_data = pd.DataFrame(metric_rows)

    metrics_data.to_csv(
        output_folder / "validation_metrics.csv",
        index=False,
    )

    model_results.to_csv(
        output_folder / "validation_hourly_results.csv",
        index=False,
    )

    return model_results, empirical_coefficients