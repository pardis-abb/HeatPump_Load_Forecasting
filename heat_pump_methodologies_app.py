"""
Heat Pump Load Calculator App

This program lets the user choose between three formulations:
1. Thermal Energy Balance Method
2. COP-Based Electrical Load Method
3. Electrical Power Measurement Method

The only built-in known value is Cp = 4.2.
All other values are entered by the user.
"""



CP = 4.2


def get_number(prompt, allow_blank=False):
    """Get a numeric value from the user. Allows blank only when requested."""
    while True:
        value = input(prompt).strip()

        if allow_blank and value == "":
            return None

        try:
            return float(value)
        except ValueError:
            print("Invalid input. Please enter a number.")





def methodology_1():
    """Thermal Energy Balance Method."""
    print("\nMethodology 1: Thermal Energy Balance Method")
    print("Use this if you have mass flow rates and inlet/outlet temperatures.")
    print(f"Cp is already set to {CP}.\n")

    condenser_mass_flow = get_number("Condenser mass flow rate (kg/s): ")
    condenser_inlet_temp = get_number("Condenser inlet temperature (°C): ")
    condenser_outlet_temp = get_number("Condenser outlet temperature (°C): ")

    evaporator_mass_flow = get_number("Evaporator mass flow rate (kg/s): ")
    evaporator_inlet_temp = get_number("Evaporator inlet temperature (°C): ")
    evaporator_outlet_temp = get_number("Evaporator outlet temperature (°C): ")

    q_evaporator = evaporator_mass_flow * CP * (evaporator_outlet_temp - evaporator_inlet_temp)
    q_condenser = condenser_mass_flow * CP * (condenser_outlet_temp - condenser_inlet_temp)
    w_compressor = q_evaporator - q_condenser
    hourly_load = w_compressor * 1 

    result = f"Hourly Load: {hourly_load:.1f} kWh"

    width = 40

    print("\nResult")
    print("-" * width)
    print(f"{result:^{width}}")
    print("-" * width)



def methodology_2():
    """COP-Based Electrical Load Method."""
    print("\nMethodology 2: COP-Based Electrical Load Method")
    print("Use this if you have heating capacity and COP.")
    print("If COP is unknown, leave it blank and enter hot/cold side temperatures.\n")

    heating_capacity = get_number("Heating capacity / thermal load Q (kW): ")
    cop = get_number("COP, if available. Press Enter if unknown: ", allow_blank=True)

    if cop is None:
        hot_side_temp = get_number("Hot side temperature (°C): ")
        cold_side_temp = get_number("Cold side temperature (°C): ")

        hot_kelvin = hot_side_temp + 273.15
        cold_kelvin = cold_side_temp + 273.15

        if hot_kelvin == cold_kelvin:
            print("Invalid values: hot side and cold side temperatures cannot be equal.")
            return

        calculated_cop = hot_kelvin / (hot_kelvin - cold_kelvin)
        final_cop = calculated_cop
    else:
        calculated_cop = cop
        final_cop = cop

    if final_cop == 0:
        print("Invalid value: COP cannot be zero.")
        return

    w_compressor = heating_capacity / final_cop
    hourly_load = w_compressor

   
    result = f"Hourly Load: {hourly_load:.1f} kWh"

    width = 40

    print("\nResult")
    print("-" * width)
    print(f"{result:^{width}}")
    print("-" * width)


def methodology_3():
    """Electrical Power Measurement Method."""
    print("\nMethodology 3: Electrical Power Measurement Method")
    print("Use this if you have voltage, current, and power factor.")
    print("If power factor is unknown, enter 1.\n")

    voltage = get_number("Voltage (V): ")
    current = get_number("Current (A): ")
    power_factor = get_number("Power factor: ")

    power_watts = voltage * current * power_factor
    power_kw = power_watts / 1000
    hourly_load = power_kw

    result = f"Hourly Load: {hourly_load:.1f} kWh"

    width = 40

    print("\nResult")
    print("-" * width)
    print(f"{result:^{width}}")
    print("-" * width)  


def choose_methodology_helper():
    """Help the user choose the best methodology based on available values."""
    print("\nMethodology Helper")
    print("Answer yes or no based on the values you have.\n")

    has_mass_temps = input(
        "Do you have mass flow rates and inlet/outlet temperatures? (yes/no): "
    ).strip().lower()

    if has_mass_temps in ["yes", "y", "Y", "Yes"]:
        methodology_1()
        return

    has_cop = input(
        "Do you have heating capacity/thermal load and COP or hot/cold temperatures? (yes/no): "
    ).strip().lower()

    if has_cop in ["yes", "y", "Y", "Yes"]:
        methodology_2()
        return

    has_electrical = input(
        "Do you have voltage, current, and power factor? (yes/no): "
    ).strip().lower()

    if has_electrical in ["yes", "y", "Y", "Yes"]:
        methodology_3()
        return

    print("\nBased on your answers, there is not enough information to calculate the load.")


def main():
    while True:
        print("\nHeat Pump Load Calculator")
        print("=" * 46)
        print("1. Methodology 1: Thermal Energy Balance")
        print("2. Methodology 2: COP-Based Electrical Load")
        print("3. Methodology 3: Electrical Power Measurement")
        print("4. Help me choose based on the values I have")
        print("5. Exit")
        print("=" * 46)

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            methodology_1()
        elif choice == "2":
            methodology_2()
        elif choice == "3":
            methodology_3()
        elif choice == "4":
            choose_methodology_helper()
        elif choice == "5":
            print("\nGoodbye.")
            break
        else:
            print("Invalid choice. Please choose 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()
