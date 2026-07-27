# HOT2000 Model Comparison

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
