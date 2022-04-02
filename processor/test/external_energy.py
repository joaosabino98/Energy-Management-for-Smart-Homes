import processor.external_energy as ext
from django.utils import timezone

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

def get_last_battery_charge():
    return ext.get_last_battery_charge()

def get_last_battery_discharge():
    return ext.get_last_battery_discharge()

def get_battery_energy(time=None):
    return ext.get_battery_energy(time)

def get_allocable_battery_energy_charge(day_periods):
    return ext.get_allocable_battery_energy_charge(day_periods)

def get_battery_power_charge(time):
    return ext.get_battery_power_charge(time)

def get_battery_power_discharge(time):
    return ext.get_battery_power_discharge(time)

def get_minimum_battery_power_discharge_within(start_time, end_time):
    return ext.get_minimum_battery_power_discharge_within(start_time, end_time)

def get_maximum_battery_power_discharge_within(start_time, end_time):
    return ext.get_maximum_battery_power_discharge_within(start_time, end_time)

def get_maximum_possible_battery_energy_discharge(start_time):
    return ext.get_maximum_possible_battery_energy_discharge(start_time)

def get_battery_discharge_available(start_time, end_time):
    return ext.get_battery_discharge_available(start_time, end_time)

def is_battery_discharge_available(execution, start_time):
    return ext.is_battery_charge_interruptible(execution, start_time)

def is_battery_charge_interruptible(execution):
    return ext.is_battery_charge_interruptible(execution)

def schedule_battery_discharge_on_consumption_above_threshold(execution, current_time, start_time):
    return ext.schedule_battery_discharge_on_consumption_above_threshold(execution, current_time, start_time, debug=True)

def schedule_battery_discharge_on_high_demand(current_time):
    return ext.schedule_battery_charge_on_low_demand(current_time, debug=True)

def start_battery_executions(current_time, energy_needed, day_periods):
    return ext.start_battery_executions(current_time, energy_needed, day_periods, debug=True)

def create_battery_execution(start_time, end_time, power):
    return ext.create_battery_execution(start_time, end_time, power)

def schedule_battery_charge_on_solar(current_time, energy_needed):
    return ext.schedule_battery_charge_on_solar(current_time, energy_needed, debug=True)

def schedule_battery_charge_on_low_demand(current_time, energy_needed):
    return ext.schedule_battery_charge_on_low_demand(current_time, energy_needed, debug=True)

def schedule_battery_charge(start_time=timezone.now()):
    return ext.schedule_battery_charge(start_time, debug=True)

def get_high_consumption_periods(start_time):
    return ext.get_high_consumption_periods(start_time)

def get_low_consumption_day_periods(start_time):
    return ext.get_low_consumption_day_periods(start_time)

def get_low_consumption_solar_day_periods(start_time, threshold_multiplier):
    return ext.get_low_consumption_solar_day_periods(start_time, threshold_multiplier)

def get_day_reference_times(current_time):
    return ext.get_day_reference_times(current_time)

def get_power_production(time):
    return ext.get_power_production(time)

def get_minimum_production_within(start_time, end_time):
    return ext.get_minimum_production_within(start_time, end_time)