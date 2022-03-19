import processor.external_energy as ext

def get_power_available_within(start_time, end_time):
    return ext.get_power_available_within(start_time, end_time)

def get_battery_executions_within(start_time, end_time):
    return ext.get_battery_executions_within(start_time, end_time)

def get_battery_charge_within(start_time, end_time):
    return ext.get_battery_charge_within(start_time, end_time)

def get_battery_discharge_within(start_time, end_time):
    return ext.get_battery_discharge_within(start_time, end_time)

def get_battery_discharge_reference_times_within(start_time, end_time):
    return ext.get_battery_discharge_reference_times_within(start_time, end_time)

def get_last_battery_execution():
    return ext.get_last_battery_execution()

def get_last_battery_discharge():
    return ext.get_last_battery_discharge()

def get_battery_energy(time=None):
    return ext.get_battery_energy(time)

def get_battery_power_charge(time):
    return ext.get_battery_power_charge(time)

def get_battery_power_discharge(time):
    return ext.get_battery_power_discharge(time)

def get_minimum_battery_power_discharge_within(start_time, end_time):
    return ext.get_minimum_battery_power_discharge_within(start_time, end_time)

def get_maximum_battery_power_discharge_within(start_time, end_time):
    return ext.get_maximum_battery_power_discharge_within(start_time, end_time)

def get_battery_depletion_below_minimum(start_time, subtracted_energy):
    return ext.get_battery_depletion_below_minimum(start_time, subtracted_energy)

def is_battery_discharge_available(execution, start_time):
    return ext.is_battery_charge_interruptible(execution, start_time)

def is_battery_charge_interruptible(execution):
    return ext.is_battery_charge_interruptible(execution)

def schedule_battery_discharge_on_consumption_above_threshold(execution, current_time, start_time):
    return ext.schedule_battery_discharge_on_consumption_above_threshold(execution, current_time, start_time, debug=True)

def schedule_battery_discharge_on_high_demand(current_time):
    return ext.schedule_battery_charge_on_low_demand(current_time, debug=True)

def create_battery_execution(start_time, end_time, power):
    return ext.create_battery_execution(start_time, end_time, power)

def attempt_schedule_battery_charge_on_solar(current_time, energy_needed):
    return ext.attempt_schedule_battery_charge_on_solar(current_time, energy_needed, debug=True)

def schedule_battery_charge_on_low_demand(current_time, energy_needed):
    return ext.schedule_battery_charge_on_low_demand(current_time, energy_needed, debug=True)

def schedule_battery_charge():
    return ext.schedule_battery_charge(debug=True)

def get_day_reference_times(date):
    return ext.get_day_reference_times(date)

def get_low_consumption_day_periods(current_time):
    return ext.get_low_consumption_day_periods(current_time)

def get_day_periods_without_full_solar_utilization(current_time):
    return ext.get_day_periods_without_full_solar_utilization(current_time)

def get_day_production_reference_times(date):
    return ext.get_day_production_reference_times(date)

def get_power_production(time):
    return ext.get_power_production(time)

def get_minimum_production_within(start_time, end_time):
    return ext.get_minimum_production_within(start_time, end_time)

def power_to_energy(start_time, end_time, power):
    return ext.power_to_energy(start_time, end_time, power)

def energy_to_power(start_time, end_time, energy):
    return ext.energy_to_power(start_time, end_time, energy)
