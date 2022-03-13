from turtle import st
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

def get_battery_energy(time=None):
    return ext.get_battery_energy(time)

def get_battery_power_charge(time):
    return ext.get_battery_power_charge(time)

def get_battery_power_discharge(time):
    return ext.get_battery_power_discharge(time)

def get_minimum_battery_power_discharge_within(start_time, end_time):
    return ext.get_minimum_battery_power_discharge_within(start_time, end_time)

def is_battery_execution_interruptable(execution):
    return ext.is_battery_execution_interruptable(execution)

def create_battery_execution(start_time, end_time, power):
    return ext.create_battery_execution(start_time, end_time, power)

def attempt_schedule_battery_on_solar(current_time, energy_needed):
    return ext.attempt_schedule_battery_on_solar(current_time, energy_needed, debug=True)

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
