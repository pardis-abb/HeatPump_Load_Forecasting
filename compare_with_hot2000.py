from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


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


# Rated heat-pump COP reported by HOT2000.
RATED_COP = 3.84


# HOT2000 monthly reference values.
#
# HP electrical input is multiplied by COP using Methodology 2:
#
#     Q_thermal = W_electrical × COP
#
# The calculated thermal output is then compared with the
# HOT2000 monthly heating load.
HOT2000_DATA = pd.DataFrame(
    {
        "month": [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "Nov",
            "Dec",
        ],
        "HOT2000_HP_electrical_input_MJ": [
            1172.3,
            885.4,
            528.4,
            66.0,
            478.2,
            956.5,
        ],
        "HOT2000_heating_load_MJ": [
            4262.3,
            3178.9,
            1865.0,
            229.4,
            1699.6,
            3450.1,
        ],
    }
)


def calculate_metrics(
    reference: pd.Series,
    calculated: pd.Series,
) -> dict:
    """
    Calculate comparison statistics.
    """

    error = calculated - reference
    absolute_error = error.abs()

    percentage_error = np.where(
        reference.abs() > 1e-9,
        absolute_error / reference.abs() * 100.0,
        np.nan,
    )

    reference_total = reference.sum()
    calculated_total = calculated.sum()

    return {
        "comparison": (
            "Methodology 2 calculated heat delivered "
            "versus HOT2000 heating load"
        ),
        "rated_COP": RATED_COP,
        "number_of_months": len(reference),
        "MAE_MJ": absolute_error.mean(),
        "RMSE_MJ": np.sqrt(
            np.mean(error**2)
        ),
        "MBE_MJ": error.mean(),
        "MAPE_percent": np.nanmean(
            percentage_error
        ),
        "correlation": reference.corr(
            calculated
        ),
        "HOT2000_total_heating_load_MJ":
            reference_total,
        "methodology_2_total_heat_delivered_MJ":
            calculated_total,
        "total_difference_MJ": (
            calculated_total
            - reference_total
        ),
        "total_difference_percent": (
            (
                calculated_total
                - reference_total
            )
            / reference_total
            * 100.0
        ),
    }


def main() -> None:
    print(
        "Creating Methodology 2 versus HOT2000 comparison..."
    )

    comparison = HOT2000_DATA.copy()

    # Methodology 2 rearranged:
    #
    # W = Q / COP
    #
    # therefore:
    #
    # Q = W × COP
    comparison[
        "methodology_2_heat_delivered_MJ"
    ] = (
        comparison[
            "HOT2000_HP_electrical_input_MJ"
        ]
        * RATED_COP
    )

    comparison["difference_MJ"] = (
        comparison[
            "methodology_2_heat_delivered_MJ"
        ]
        - comparison[
            "HOT2000_heating_load_MJ"
        ]
    )

    comparison[
        "absolute_difference_MJ"
    ] = comparison["difference_MJ"].abs()

    comparison[
        "percentage_difference"
    ] = (
        comparison["difference_MJ"]
        / comparison[
            "HOT2000_heating_load_MJ"
        ]
        * 100.0
    )

    comparison[
        "absolute_percentage_difference"
    ] = comparison[
        "percentage_difference"
    ].abs()

    # Save monthly comparison.
    comparison_file = (
        OUTPUT_FOLDER
        / "hot2000_comparison.csv"
    )

    comparison.to_csv(
        comparison_file,
        index=False,
    )

    # Save validation metrics.
    metrics = calculate_metrics(
        comparison[
            "HOT2000_heating_load_MJ"
        ],
        comparison[
            "methodology_2_heat_delivered_MJ"
        ],
    )

    metrics_file = (
        OUTPUT_FOLDER
        / "hot2000_validation_metrics.csv"
    )

    pd.DataFrame([metrics]).to_csv(
        metrics_file,
        index=False,
    )

    # Create comparison plot.
    plt.figure(figsize=(11, 6))

    plt.plot(
        comparison["month"],
        comparison[
            "HOT2000_heating_load_MJ"
        ],
        marker="o",
        label="HOT2000 heating load",
    )

    plt.plot(
        comparison["month"],
        comparison[
            "methodology_2_heat_delivered_MJ"
        ],
        marker="o",
        label="Methodology 2 heat delivered",
    )

    plt.xlabel("Month")
    plt.ylabel("Monthly thermal energy (MJ)")

    plt.title(
        "Methodology 2 versus HOT2000 "
        "Monthly Heating Load"
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

    # Create README.
    readme_text = f"""# HOT2000 Methodology 2 Comparison

This folder compares the thermal heat delivered calculated
using Methodology 2 with the monthly heating load reported
by HOT2000.

## Method

Methodology 2 normally calculates electrical input as:

`W = Q / COP`

For this comparison, the equation is rearranged to calculate
thermal heat delivered:

`Q = W × COP`

The HOT2000 monthly heat-pump electrical input is multiplied
by the reported rated COP of {RATED_COP}. The resulting
thermal output is compared against the monthly HOT2000
heating load.

## Results

Across the six heating months:

- HOT2000 total heating load:
  {metrics["HOT2000_total_heating_load_MJ"]:.1f} MJ
- Methodology 2 calculated heat delivered:
  {metrics["methodology_2_total_heat_delivered_MJ"]:.1f} MJ
- Total percentage difference:
  {metrics["total_difference_percent"]:.2f}%

## Output files

- `hot2000_comparison.csv`
- `hot2000_validation_metrics.csv`
- `hot2000_validation_plot.png`
- `HOT2000_Full_Report.pdf`
- `HOT2000_Extracted_Data_Report.pdf`

## Limitation

The HOT2000 system is a hybrid ground-source heat pump with
a natural-gas backup furnace. Therefore, this comparison is
best treated as a reasonableness check for Methodology 2,
rather than a strict heat-pump-only validation.
"""

    readme_file = (
        OUTPUT_FOLDER
        / "README.md"
    )

    readme_file.write_text(
        readme_text,
        encoding="utf-8",
    )

    print("\nComparison completed.")
    print(
        comparison[
            [
                "month",
                "HOT2000_HP_electrical_input_MJ",
                "methodology_2_heat_delivered_MJ",
                "HOT2000_heating_load_MJ",
                "absolute_percentage_difference",
            ]
        ].to_string(index=False)
    )

    print(
        "\nTotal percentage difference: "
        f"{metrics['total_difference_percent']:.2f}%"
    )

    print(f"\nComparison saved to: {comparison_file}")
    print(f"Metrics saved to: {metrics_file}")
    print(f"Plot saved to: {plot_file}")
    print(f"README saved to: {readme_file}")


if __name__ == "__main__":
    main()