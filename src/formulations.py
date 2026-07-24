import numpy as np
import pandas as pd


def calculate_heating_thermal_load(
    outside_temperature_c: pd.Series,
    balance_temperature_c: float,
    ua_heating_kw_per_c: float,
) -> pd.Series:
    """
    Calculate the required thermal heating load.

    Q_heat = UA × max(T_balance - T_outside, 0)
    """

    heating_temperature_difference = (
        balance_temperature_c - outside_temperature_c
    ).clip(lower=0.0)

    return (
        ua_heating_kw_per_c
        * heating_temperature_difference
    )


def calculate_lorenz_cop(
    outside_temperature_c: pd.Series,
    indoor_temperature_c: float,
    approach_temperature_c: float,
    minimum_cop: float = 1.0,
    maximum_cop: float = 100.0,
) -> pd.Series:
    """
    Calculate the reversible Lorenz COP.

    This function does not apply refrigeration efficiency.
    Efficiency is applied later when calculating electrical load.
    """

    indoor_temperature_k = indoor_temperature_c + 273.15
    outside_temperature_k = outside_temperature_c + 273.15

    numerator = (
        indoor_temperature_k
        - approach_temperature_c / 2.0
    )

    denominator = (
        indoor_temperature_k
        - outside_temperature_k
        + approach_temperature_c
    ).clip(lower=0.5)

    reversible_cop = numerator / denominator

    return reversible_cop.clip(
        lower=minimum_cop,
        upper=maximum_cop,
    )

def calculate_carnot_cop(
    outside_temperature_c: pd.Series,
    indoor_temperature_c: float,
    minimum_cop: float = 1.0,
    maximum_cop: float = 100.0,
) -> pd.Series:
    """
    Calculate the reversible Carnot heating COP.

    This function does not apply refrigeration efficiency.
    """

    indoor_temperature_k = indoor_temperature_c + 273.15
    outside_temperature_k = outside_temperature_c + 273.15

    denominator = (
        indoor_temperature_k
        - outside_temperature_k
    ).clip(lower=0.5)

    reversible_cop = (
        indoor_temperature_k
        / denominator
    )

    return reversible_cop.clip(
        lower=minimum_cop,
        upper=maximum_cop,
    )

def calculate_electrical_load(
    thermal_load_kw: pd.Series,
    reversible_cop: pd.Series,
    refrigeration_efficiency: float,
) -> pd.Series:
    """
    Calculate electrical heat-pump demand using Equation 11:

    Load = Q / (eta_R × COP_reversible)
    """

    actual_cop = (
        refrigeration_efficiency
        * reversible_cop
    )

    safe_actual_cop = actual_cop.replace(
        0,
        np.nan,
    )

    electrical_load = (
        thermal_load_kw
        / safe_actual_cop
    )

    return electrical_load.fillna(0.0)


def fit_empirical_model(
    validation_data: pd.DataFrame,
    polynomial_degree: int = 2,
) -> np.ndarray:
    """
    Fit an empirical relationship between outdoor temperature
    and measured heat-pump electrical load.
    """

    clean_data = validation_data[
        [
            "outside_temperature_C",
            "measured_hp_load_kW_per_unit",
        ]
    ].dropna()

    if len(clean_data) <= polynomial_degree:
        raise ValueError(
            "There are not enough validation observations "
            "to fit the empirical model."
        )

    coefficients = np.polyfit(
        clean_data["outside_temperature_C"],
        clean_data["measured_hp_load_kW_per_unit"],
        polynomial_degree,
    )

    return coefficients


def calculate_empirical_load(
    outside_temperature_c: pd.Series,
    coefficients: np.ndarray,
    heating_active: pd.Series,
) -> pd.Series:
    """
    Predict heat-pump electrical load using the empirical model.
    """

    predicted_load = pd.Series(
        np.polyval(
            coefficients,
            outside_temperature_c,
        ),
        index=outside_temperature_c.index,
    )

    predicted_load = predicted_load.clip(lower=0.0)

    return predicted_load.where(
        heating_active,
        0.0,
    )


def calculate_all_formulations(
    data: pd.DataFrame,
    indoor_temperature_c: float,
    balance_temperature_c: float,
    approach_temperature_c: float,
    refrigeration_efficiency: float,
    ua_heating_kw_per_c: float,
    minimum_cop: float,
    maximum_cop: float,
    empirical_coefficients: np.ndarray | None = None,
) -> pd.DataFrame:
    """
    Calculate thermal demand and all available formulations.
    """

    results = data.copy()

    results["thermal_heating_load_kW"] = (
        calculate_heating_thermal_load(
            results["outside_temperature_C"],
            balance_temperature_c,
            ua_heating_kw_per_c,
        )
    )

    results["COP_Lorenz_Reversible"] = (
        calculate_lorenz_cop(
            results["outside_temperature_C"],
            indoor_temperature_c,
            approach_temperature_c,
            minimum_cop,
            maximum_cop,
        )
    )

    results["COP_Lorenz_Actual"] = (
        refrigeration_efficiency
        * results["COP_Lorenz_Reversible"]
    )

    results["COP_Carnot_Reversible"] = (
        calculate_carnot_cop(
            results["outside_temperature_C"],
            indoor_temperature_c,
            minimum_cop,
            maximum_cop,
        )
    )

    results["COP_Carnot_Actual"] = (
        refrigeration_efficiency
        * results["COP_Carnot_Reversible"]
    )

    results["HP_load_Lorenz_kW_per_unit"] = (
        calculate_electrical_load(
            results["thermal_heating_load_kW"],
            results["COP_Lorenz_Reversible"],
            refrigeration_efficiency,
        )
    )

    results["HP_load_Carnot_kW_per_unit"] = (
        calculate_electrical_load(
            results["thermal_heating_load_kW"],
            results["COP_Carnot_Reversible"],
            refrigeration_efficiency,
        )
    )

    if empirical_coefficients is not None:
        results["HP_load_Empirical_kW_per_unit"] = (
            calculate_empirical_load(
                results["outside_temperature_C"],
                empirical_coefficients,
                results["thermal_heating_load_kW"] > 0,
            )
        )

    return results