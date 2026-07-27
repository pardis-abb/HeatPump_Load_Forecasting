from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# OUTPUT LOCATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

OUTPUT_FOLDER = (
    PROJECT_ROOT
    / "results"
    / "hot2000_comparison"
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# MODEL PARAMETERS
# ============================================================

INDOOR_TEMPERATURE_C = 21.0
APPROACH_TEMPERATURE_C = 5.0
REFRIGERATION_EFFICIENCY = 0.80

MINIMUM_COP = 1.0
MAXIMUM_COP = 100.0


# ============================================================
# HOT2000 MONTHLY REFERENCE DATA
# ============================================================
#
# Source: REEP House HOT2000 report
#
# The thermal loads and heat-pump electrical inputs below
# are reported monthly values.
#
# Because this is a ground-source heat pump, the monthly
# ground/source temperatures from the report are used rather
# than Calgary outdoor-air temperatures.
# ============================================================

hot2000_data = pd.DataFrame(
    {
        "month": [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "Nov",
            "Dec",
        ],
        "month_number": [
            1,
            2,
            3,
            4,
            11,
            12,
        ],
        "source_temperature_C": [
            9.6,
            9.4,
            9.4,
            9.6,
            10.3,
            9.9,
        ],
        "HOT2000_thermal_heating_load_MJ": [
            4262.3,
            3178.9,
            1865.0,
            229.4,
            1699.6,
            3450.1,
        ],
        "HOT2000_HP_electrical_input_MJ": [
            1172.3,
            885.4,
            528.4,
            66.0,
            478.2,
            956.5,
        ],
        "HOT2000_monthly_COP": [
            3.0,
            3.0,
            2.9,
            2.8,
            3.0,
            3.0,
        ],
    }
)


# ============================================================
# COP FUNCTIONS
# ============================================================

def calculate_lorenz_cop(
    source_temperature_c: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Calculate reversible and actual Lorenz COP.

    For this HOT2000 comparison, the source temperature is
    the monthly ground temperature reported for the GSHP.

    COP_actual = eta_R × COP_reversible
    """

    indoor_temperature_k = (
        INDOOR_TEMPERATURE_C + 273.15
    )

    source_temperature_k = (
        source_temperature_c + 273.15
    )

    numerator = (
        indoor_temperature_k
        - APPROACH_TEMPERATURE_C / 2.0
    )

    denominator = (
        indoor_temperature_k
        - source_temperature_k
        + APPROACH_TEMPERATURE_C
    ).clip(lower=0.5)

    reversible_cop = (
        numerator / denominator
    ).clip(
        lower=MINIMUM_COP,
        upper=MAXIMUM_COP,
    )

    actual_cop = (
        REFRIGERATION_EFFICIENCY
        * reversible_cop
    )

    return reversible_cop, actual_cop


def calculate_carnot_cop(
    source_temperature_c: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Calculate reversible and actual Carnot COP.
    """

    indoor_temperature_k = (
        INDOOR_TEMPERATURE_C + 273.15
    )

    source_temperature_k = (
        source_temperature_c + 273.15
    )

    denominator = (
        indoor_temperature_k
        - source_temperature_k
    ).clip(lower=0.5)

    reversible_cop = (
        indoor_temperature_k
        / denominator
    ).clip(
        lower=MINIMUM_COP,
        upper=MAXIMUM_COP,
    )

    actual_cop = (
        REFRIGERATION_EFFICIENCY
        * reversible_cop
    )

    return reversible_cop, actual_cop


# ============================================================
# VALIDATION METRICS
# ============================================================

def calculate_metrics(
    measured: pd.Series,
    modelled: pd.Series,
    formulation: str,
) -> dict:
    """
    Calculate validation statistics.
    """

    measured_values = measured.to_numpy(
        dtype=float
    )

    modelled_values = modelled.to_numpy(
        dtype=float
    )

    errors = (
        modelled_values
        - measured_values
    )

    absolute_errors = np.abs(errors)

    percentage_errors = np.where(
        measured_values != 0,
        absolute_errors
        / np.abs(measured_values)
        * 100.0,
        np.nan,
    )

    measured_total = measured_values.sum()
    modelled_total = modelled_values.sum()

    return {
        "formulation": formulation,
        "number_of_months": len(measured_values),
        "MAE_MJ": absolute_errors.mean(),
        "RMSE_MJ": np.sqrt(
            np.mean(errors**2)
        ),
        "MBE_MJ": errors.mean(),
        "MAPE_percent": np.nanmean(
            percentage_errors
        ),
        "correlation": np.corrcoef(
            measured_values,
            modelled_values,
        )[0, 1],
        "HOT2000_total_MJ": measured_total,
        "modelled_total_MJ": modelled_total,
        "total_difference_MJ": (
            modelled_total
            - measured_total
        ),
        "total_difference_percent": (
            (
                modelled_total
                - measured_total
            )
            / measured_total
            * 100.0
        ),
    }


# ============================================================
# MAIN COMPARISON
# ============================================================

def main() -> None:
    """
    Compare modelled monthly heat-pump electrical input
    with the HOT2000 monthly electrical input.
    """

    print(
        "Creating model-versus-HOT2000 comparison..."
    )

    comparison = hot2000_data.copy()

    (
        comparison["COP_Lorenz_Reversible"],
        comparison["COP_Lorenz_Actual"],
    ) = calculate_lorenz_cop(
        comparison["source_temperature_C"]
    )

    (
        comparison["COP_Carnot_Reversible"],
        comparison["COP_Carnot_Actual"],
    ) = calculate_carnot_cop(
        comparison["source_temperature_C"]
    )

    comparison[
        "modelled_Lorenz_HP_input_MJ"
    ] = (
        comparison[
            "HOT2000_thermal_heating_load_MJ"
        ]
        / comparison["COP_Lorenz_Actual"]
    )

    comparison[
        "modelled_Carnot_HP_input_MJ"
    ] = (
        comparison[
            "HOT2000_thermal_heating_load_MJ"
        ]
        / comparison["COP_Carnot_Actual"]
    )

    comparison[
        "Lorenz_error_MJ"
    ] = (
        comparison[
            "modelled_Lorenz_HP_input_MJ"
        ]
        - comparison[
            "HOT2000_HP_electrical_input_MJ"
        ]
    )

    comparison[
        "Carnot_error_MJ"
    ] = (
        comparison[
            "modelled_Carnot_HP_input_MJ"
        ]
        - comparison[
            "HOT2000_HP_electrical_input_MJ"
        ]
    )

    comparison[
        "Lorenz_absolute_percentage_error"
    ] = (
        comparison["Lorenz_error_MJ"].abs()
        / comparison[
            "HOT2000_HP_electrical_input_MJ"
        ]
        * 100.0
    )

    comparison[
        "Carnot_absolute_percentage_error"
    ] = (
        comparison["Carnot_error_MJ"].abs()
        / comparison[
            "HOT2000_HP_electrical_input_MJ"
        ]
        * 100.0
    )

    comparison_file = (
        OUTPUT_FOLDER
        / "hot2000_comparison.csv"
    )

    comparison.to_csv(
        comparison_file,
        index=False,
    )

    metrics = pd.DataFrame(
        [
            calculate_metrics(
                comparison[
                    "HOT2000_HP_electrical_input_MJ"
                ],
                comparison[
                    "modelled_Lorenz_HP_input_MJ"
                ],
                "Lorenz",
            ),
            calculate_metrics(
                comparison[
                    "HOT2000_HP_electrical_input_MJ"
                ],
                comparison[
                    "modelled_Carnot_HP_input_MJ"
                ],
                "Carnot",
            ),
        ]
    )

    metrics_file = (
        OUTPUT_FOLDER
        / "hot2000_validation_metrics.csv"
    )

    metrics.to_csv(
        metrics_file,
        index=False,
    )

    # --------------------------------------------------------
    # CREATE COMPARISON PLOT
    # --------------------------------------------------------

    plt.figure(figsize=(11, 6))

    plt.plot(
        comparison["month"],
        comparison[
            "HOT2000_HP_electrical_input_MJ"
        ],
        marker="o",
        label="HOT2000 reference",
    )

    plt.plot(
        comparison["month"],
        comparison[
            "modelled_Lorenz_HP_input_MJ"
        ],
        marker="o",
        label="Lorenz model",
    )

    plt.plot(
        comparison["month"],
        comparison[
            "modelled_Carnot_HP_input_MJ"
        ],
        marker="o",
        label="Carnot model",
    )

    plt.xlabel("Month")
    plt.ylabel(
        "Monthly heat-pump electrical input (MJ)"
    )

    plt.title(
        "HOT2000 versus Modelled Heat-Pump "
        "Electrical Input"
    )

    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plot_file = (
        OUTPUT_FOLDER
        / "hot2000_validation_plot.png"
    )

    plt.savefig(
        plot_file,
        dpi=200,
    )

    plt.close()

    # --------------------------------------------------------
    # CREATE README
    # --------------------------------------------------------

    readme_text = """# HOT2000 Model Comparison

This folder contains a preliminary validation of the Python
heat-pump model against a HOT2000 residential energy report.

## Reference case

- Location: Kitchener, Ontario
- HOT2000 weather station: Toronto Metro Residential Station
- Heating equipment: Ground-source heat pump
- Backup equipment: Natural-gas furnace
- Heat-pump rated COP: 3.84
- Reported annual combined system COP: 2.984

## Comparison method

The HOT2000 report provides monthly:

- thermal space-heating load;
- heat-pump electrical input;
- heat-pump COP; and
- ground/source temperature.

The Python model uses the reported monthly thermal load and
ground/source temperature to calculate monthly electrical input
using the Lorenz and Carnot formulations. These calculated
values are compared against the monthly HOT2000 heat-pump
electrical input.

## Output files

- `hot2000_comparison.csv`: monthly reference and calculated values;
- `hot2000_validation_metrics.csv`: MAE, RMSE, MAPE, bias,
  correlation and annual energy differences;
- `hot2000_validation_plot.png`: monthly comparison graph;
- `HOT2000_Full_Report.pdf`: complete reference report;
- `HOT2000_Extracted_Data_Report.pdf`: extracted summary values.

## Important limitation

This is a preliminary model comparison, not a strict validation
of the Calgary forecasting case. The HOT2000 house is located in
Kitchener, uses Toronto weather, and has a ground-source heat
pump. The Calgary forecast uses Calgary weather and represents
a generic heat-pump/building formulation.

The comparison therefore evaluates whether the model produces
a reasonably similar energy pattern and magnitude under the
HOT2000 reference inputs. It does not demonstrate direct
hour-by-hour agreement for a Calgary air-source heat pump.
"""

    readme_file = (
        OUTPUT_FOLDER
        / "README.md"
    )

    readme_file.write_text(
        readme_text,
        encoding="utf-8",
    )

    print("\nHOT2000 comparison completed.")
    print(f"Comparison: {comparison_file}")
    print(f"Metrics:    {metrics_file}")
    print(f"Plot:       {plot_file}")
    print(f"README:     {readme_file}")


if __name__ == "__main__":
    main()