import processor.external_energy as ext

""" Production-related methods """
def get_power_threshold_within(home, start_time, end_time):
    return ext.get_power_threshold_within(home, start_time, end_time)

def get_day_reference_times(home, current_time):
    return ext.get_day_reference_times(home, current_time)

def get_power_production(home, time):
    return ext.get_power_production(home, time)

""" Consumption-related methods """
def get_high_consumption_periods(home, start_time):
    return ext.get_high_consumption_periods(home, start_time)

def get_low_consumption_day_periods(home, start_time):
    return ext.get_low_consumption_day_periods(home, start_time)

def get_low_consumption_solar_day_periods(home, start_time, threshold_multiplier):
    return ext.get_low_consumption_solar_day_periods(home, start_time, threshold_multiplier)

def get_battery_discharge_available_on_high_demand_periods(home, start_time, end_time, rated_power=0):
    return ext.get_battery_discharge_available_on_high_demand_periods(home, start_time, end_time, rated_power)

def get_minimum_production_within(home, start_time, end_time):
    return ext.get_minimum_production_within(home, start_time, end_time)

""" Battery-related methods """
def get_battery_executions_within(home, start_time, end_time):
    return ext.get_battery_executions_within(home, start_time, end_time)

def get_battery_charge_within(home, start_time, end_time):
    return ext.get_battery_charge_within(home, start_time, end_time)

def get_battery_discharge_within(home, start_time, end_time):
    return ext.get_battery_discharge_within(home, start_time, end_time)

def get_battery_discharge_reference_times_within(home, start_time, end_time):
    return ext.get_battery_discharge_reference_times_within(home, start_time, end_time)

def get_last_battery_execution(home):
    return ext.get_last_battery_execution(home)

def get_last_battery_charge(home):
    return ext.get_last_battery_charge(home)

def get_last_battery_discharge(home):
    return ext.get_last_battery_discharge(home)

def get_battery_energy(home, time=None):
    return ext.get_battery_energy(home, time)

def get_allocable_battery_energy_charge(home, day_periods):
    return ext.get_allocable_battery_energy_charge(home, day_periods)

def get_battery_power_charge(home, time):
    return ext.get_battery_power_charge(home, time)

def get_battery_power_discharge(home, time):
    return ext.get_battery_power_discharge(home, time)

def get_maximum_battery_power_discharge_within(home, start_time, end_time):
    return ext.get_maximum_battery_power_discharge_within(home, start_time, end_time)

def get_maximum_possible_battery_energy_discharge(home, start_time):
    return ext.get_maximum_possible_battery_energy_discharge(home, start_time)

def get_battery_discharge_available(home, start_time, end_time):
    return ext.get_battery_discharge_available(home, start_time, end_time)

def is_battery_charge_interruptible(execution):
    return ext.is_battery_charge_interruptible(execution)

def schedule_battery_discharge_on_consumption_above_threshold(home, start_time, end_time):
    return ext.schedule_battery_discharge_on_consumption_above_threshold(home, start_time, end_time, debug=True)

def schedule_battery_discharge_on_high_demand(home, current_time):
    return ext.schedule_battery_charge_on_low_demand(home, current_time, debug=True)

def start_battery_executions(home, energy_needed, day_periods):
    return ext.start_battery_executions(home, energy_needed, day_periods, debug=True)

def create_battery_execution(home, start_time, end_time, power):
    return ext.create_battery_execution(home, start_time, end_time, power)

def schedule_battery_charge_on_solar(home, start_time, energy_needed):
    return ext.schedule_battery_charge_on_solar(home, start_time, energy_needed, debug=True)

def schedule_battery_charge_on_low_demand(home, start_time, energy_needed):
    return ext.schedule_battery_charge_on_low_demand(home, start_time, energy_needed, debug=True)

def schedule_battery_charge(home, start_time=None):
    return ext.schedule_battery_charge(home, start_time, debug=True)