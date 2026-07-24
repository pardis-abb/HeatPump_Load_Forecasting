from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_formulation_comparison(
    results: pd.DataFrame,
    output_folder: Path,
) -> None:
    """
    Plot hourly per-unit heat-pump demand.
    """

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(figsize=(12, 6))

    formulation_columns = {
        "Lorenz": "HP_load_Lorenz_kW_per_unit",
        "Carnot": "HP_load_Carnot_kW_per_unit",
        "Empirical": "HP_load_Empirical_kW_per_unit",
    }

    for formulation, column in formulation_columns.items():
        if column in results.columns:
            plt.plot(
                results["datetime"],
                results[column],
                label=formulation,
            )

    plt.xlabel("Datetime")
    plt.ylabel("Heat-pump load (kW per unit)")
    plt.title("Hourly Heat-Pump Load by Formulation")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        output_folder / "formulation_comparison.png",
        dpi=200,
    )

    plt.close()


def plot_aggregate_heat_pump_load(
    results: pd.DataFrame,
    output_folder: Path,
) -> None:
    """
    Plot total estimated Calgary heat-pump load.
    """

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(figsize=(12, 6))

    aggregate_columns = {
        "Lorenz": "total_HP_load_Lorenz_MW",
        "Carnot": "total_HP_load_Carnot_MW",
        "Empirical": "total_HP_load_Empirical_MW",
    }

    for formulation, column in aggregate_columns.items():
        if column in results.columns:
            plt.plot(
                results["datetime"],
                results[column],
                label=formulation,
            )

    plt.xlabel("Datetime")
    plt.ylabel("Total heat-pump load (MW)")
    plt.title("Estimated Aggregate Calgary Heat-Pump Load")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        output_folder / "aggregate_heat_pump_load.png",
        dpi=200,
    )

    plt.close()


def plot_validation_results(
    validation_results: pd.DataFrame,
    output_folder: Path,
) -> None:
    """
    Plot measured/reference and modelled heat-pump load.
    """

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(figsize=(12, 6))

    plt.plot(
        validation_results["datetime"],
        validation_results[
            "measured_hp_load_kW_per_unit"
        ],
        label="Measured/reference",
    )

    comparison_columns = {
        "Lorenz": "HP_load_Lorenz_kW_per_unit",
        "Carnot": "HP_load_Carnot_kW_per_unit",
        "Empirical": "HP_load_Empirical_kW_per_unit",
    }

    for formulation, column in comparison_columns.items():
        if column in validation_results.columns:
            plt.plot(
                validation_results["datetime"],
                validation_results[column],
                label=formulation,
            )

    plt.xlabel("Datetime")
    plt.ylabel("Heat-pump load (kW per unit)")
    plt.title("Model Proof: Measured versus Modelled Load")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        output_folder / "validation_comparison.png",
        dpi=200,
    )

    plt.close()