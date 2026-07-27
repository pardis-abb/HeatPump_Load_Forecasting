# HOT2000 Methodology 2 Comparison

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
by the reported rated COP of 3.84. The resulting
thermal output is compared against the monthly HOT2000
heating load.

## Results

Across the six heating months:

- HOT2000 total heating load:
  14685.3 MJ
- Methodology 2 calculated heat delivered:
  15693.3 MJ
- Total percentage difference:
  6.86%

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
