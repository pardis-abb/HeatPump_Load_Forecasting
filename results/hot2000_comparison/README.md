# HOT2000 Methodology 2 Comparison

This folder compares the heat delivered calculated using
Methodology 2 with the monthly heating load reported by HOT2000.

## Calculation

Methodology 2 normally calculates electrical input as:

`W = Q / COP`

For this comparison, the equation was rearranged:

`Q = W × COP`

The HOT2000 heat-pump electrical input was multiplied by the
reported rated COP of 3.84.

## Monthly comparison

| Month | HOT2000 HP input | Methodology 2 heat delivered | HOT2000 heating load | Difference |
|---|---:|---:|---:|---:|
| Jan | 1172.3 MJ | 4501.6 MJ | 4262.3 MJ | 5.62% |
| Feb | 885.4 MJ | 3399.9 MJ | 3178.9 MJ | 6.95% |
| Mar | 528.4 MJ | 2029.1 MJ | 1865.0 MJ | 8.80% |
| Apr | 66.0 MJ | 253.4 MJ | 229.4 MJ | 10.48% |
| Nov | 478.2 MJ | 1836.3 MJ | 1699.6 MJ | 8.04% |
| Dec | 956.5 MJ | 3673.0 MJ | 3450.1 MJ | 6.46% |

## Overall result

- HOT2000 total heating load: 14,685.3 MJ
- Methodology 2 calculated heat delivered: 15,693.3 MJ
- Total difference: 6.86%

The comparison shows that Methodology 2 produces monthly
thermal-output estimates within approximately 5.6% to 10.5%
of the HOT2000 heating-load values.

## Limitation

The HOT2000 case uses a ground-source heat pump with a
natural-gas backup furnace. Therefore, this is a reasonableness
check rather than a strict heat-pump-only validation.

## Files

- `hot2000_comparison.csv`
- `hot2000_validation_metrics.csv`
- `hot2000_validation_plot.png`
- `HOT2000_Full_Report.pdf`
- `HOT2000_Extracted_Data_Report.pdf`