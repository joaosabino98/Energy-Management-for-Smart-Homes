import math
import os
import django
import processor.core as core
from scheduler.models import AppVals, BatteryStorageSystem, Execution, NoBSSystemException, NoPVSystemException, PhotovoltaicSystem, ProductionData, Profile
from django.utils import timezone
from math import floor

from scheduler.settings import INTERRUPTIBLE, LOAD_DISTRIBUTION, LOW_PRIORITY, NONINTERRUPTIBLE, PEAK_SHAVING

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

def get_power_available_within(start_time, end_time):
	threshold = AppVals.get_consumption_threshold()
	battery_discharge = get_minimum_battery_power_discharge_within(start_time, end_time)
	production = get_minimum_production_within(start_time, end_time)
	if battery_discharge is not None:
		threshold += battery_discharge
	if production is not None:
		threshold += production
	return threshold

def get_battery_executions_within(start_time, end_time):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return Execution.objects.none()
    return Execution.objects.filter(appliance=battery.appliance, start_time__lte=end_time, end_time__gt=start_time)

def get_battery_charge_within(start_time, end_time):
    return get_battery_executions_within(start_time, end_time).filter(profile__rated_power__gt=0)

def get_battery_discharge_within(start_time, end_time):
    return get_battery_executions_within(start_time, end_time).filter(profile__rated_power__lt=0)

def get_battery_discharge_reference_times_within(start_time, end_time):
    time_list = [start_time, end_time]
    queryset = get_battery_discharge_within(start_time, end_time)
    for discharge in queryset:
        if discharge.start_time >= start_time:
            time_list.append(discharge.start_time)
        if discharge.end_time <= end_time:
            time_list.append(discharge.end_time)
    time_list.sort()
    return time_list

def get_last_battery_execution():
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return Execution.objects.none()
    return Execution.objects.filter(appliance=battery.appliance).order_by('end_time').last()

def get_battery_energy(time=None):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return 0
    queryset = Execution.objects.filter(appliance=battery.appliance, start_time__gt=battery.last_full_charge_time)
    if time is not None:
        queryset = queryset.exclude(end_time__gt=time)
    energy = battery.total_energy_capacity
    for execution in queryset:
        power = execution.profile.rated_power
        energy += floor((execution.end_time - execution.start_time).seconds / 3600 * power)
    return energy

def get_battery_power_charge(time):
    power = 0
    queryset = get_battery_charge_within(time, time)
    for charge in queryset:
        power += charge.profile.rated_power
    return power

def get_battery_power_discharge(time):
    power = 0
    queryset = get_battery_discharge_within(time, time)
    for discharge in queryset:
        power -= discharge.profile.rated_power
    return power

def get_minimum_battery_power_discharge_within(start_time, end_time):
    minimum_discharge = None
    if BatteryStorageSystem.get_system() is not None:
        reference_times = get_battery_discharge_reference_times_within(start_time, end_time)
        for time in reference_times:
            power_discharge = get_battery_power_discharge(time)
            if minimum_discharge is None or power_discharge < minimum_discharge:
                minimum_discharge = power_discharge
    return minimum_discharge

def is_battery_discharge_available(execution, start_time):
    pass

def is_battery_charge_interruptable(execution):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    energy = get_battery_energy(execution.start_time) - \
        power_to_energy(execution.start_time, execution.end_time, execution.profile.rated_power)
    minimum_energy = floor(battery.total_energy_capacity * (1 - battery.depth_of_discharge))
    queryset = get_battery_executions_within(execution.start_time, execution.end_time)
    for battery_execution in queryset:
        if battery_execution != execution:
            energy += power_to_energy(battery_execution.start_time, battery_execution.end_time, battery_execution.profile.rated_power)
            if energy < minimum_energy:
                return False
    return True

def create_battery_execution(start_time, end_time, power):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    profile, _ = battery.appliance.profiles.get_or_create(
            rated_power=power,
            defaults={
                "name": f"BSS {power}W Charge" if power > 0 else f"BSS {-power}W Discharge",
                "schedulability": INTERRUPTIBLE if power > 0 else NONINTERRUPTIBLE,
                "maximum_delay": None,
                "priority": LOW_PRIORITY,
                "hidden": True
            }
        )
    return Execution.objects.create(
        appliance=battery.appliance,
        profile=profile,
        start_time=start_time,
        end_time=end_time
    )

def attempt_schedule_battery_charge_on_solar(current_time, energy_needed, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    photovoltaic_system = PhotovoltaicSystem.get_system()
    if photovoltaic_system is None:
        raise NoPVSystemException() 

    overproduction = get_day_periods_without_full_solar_utilization(current_time)
    if not overproduction:
        tomorrow = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        overproduction = get_day_periods_without_full_solar_utilization(tomorrow)
    energy_to_allocate = 0
    for period in overproduction:
        power = overproduction[period] if overproduction[period] < battery.continuous_power else battery.continuous_power
        energy_to_allocate += power_to_energy(period[0], period[1], power)
    if energy_to_allocate >= energy_needed:
        for period in overproduction:
            if energy_needed < overproduction[period]:
                power = energy_needed
                energy_needed = 0
            elif battery.continuous_power < overproduction[period]:
                power = battery.continuous_power
                energy_needed -= power_to_energy(period[0], period[1], power)
            else:
                power = overproduction[period]
                energy_needed -= power_to_energy(period[0], period[1], power)
            execution = create_battery_execution(period[0], period[1], power)
            if period[0] == current_time:
                core.start_execution(execution, None, debug)
            else:
                core.start_execution(execution, period[0], debug)
            if energy_needed < battery.total_energy_capacity * 0.01:
                break
        return True
    else:
        return False

def schedule_battery_charge_on_low_demand(current_time, energy_needed, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    photovoltaic_system = PhotovoltaicSystem.get_system()
    if photovoltaic_system is None:
        raise NoPVSystemException() 

    low_demand = get_low_consumption_day_periods(current_time)
    for period in low_demand:
        if energy_needed < low_demand[period]:
            power = energy_needed
            energy_needed = 0
        elif battery.continuous_power < low_demand[period]:
            power = battery.continuous_power
            energy_needed -= power_to_energy(period[0], period[1], power)
        else:
            power = low_demand[period]
            energy_needed -= power_to_energy(period[0], period[1], power)
        execution = create_battery_execution(period[0], period[1], power)
        if period[0] == current_time:
            core.start_execution(execution, None, debug)
        else:
            core.start_execution(execution, period[0], debug)
        if energy_needed < battery.total_energy_capacity * 0.01:
            break

def schedule_battery_charge(debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return NoBSSystemException()
    today = timezone.now()
    energy_needed = battery.total_energy_capacity - get_battery_energy()

    success = attempt_schedule_battery_charge_on_solar(today, energy_needed, debug)
    if not success:
        schedule_battery_charge_on_low_demand(today, energy_needed, debug)   

def power_to_energy(start_time, end_time, power):
    return math.floor(power * (end_time - start_time).seconds/3600)

def energy_to_power(start_time, end_time, energy):
    return math.floor(energy / ((end_time - start_time).seconds/3600))

def get_day_reference_times(date):
    production_reference_times = get_day_production_reference_times(date)
    if production_reference_times:
        start_time = production_reference_times[0]
        end_time = production_reference_times[-1]
        reference_times = list(dict.fromkeys(production_reference_times + core.get_consumption_reference_times_within(start_time, end_time)))
        reference_times.append(date)
        reference_times.sort()
    else:
        start_time = date
        end_time = start_time + timezone.timedelta(days=1)
        reference_times = core.get_consumption_reference_times_within(start_time, end_time)
    return reference_times

def get_low_consumption_day_periods(current_time):
    reference_times = get_day_reference_times(current_time)
    day_periods = {}
    prev_time = None
    for time in reference_times:
        if prev_time is not None and prev_time >= current_time:
            low_consumption_threshold = get_power_available_within(prev_time, time) * 0.4
            consumption = core.get_maximum_consumption_within(prev_time, time)
            if low_consumption_threshold > consumption:
                allocable_energy = floor(get_power_available_within(prev_time, time) * 0.6 - consumption)
                day_periods[(prev_time, time)] = allocable_energy
        prev_time = time
    return day_periods

def get_day_periods_without_full_solar_utilization(current_time):
    reference_times = get_day_reference_times(current_time)
    day_periods = {}
    if PhotovoltaicSystem.get_system() is not None:
        prev_time = None
        for time in reference_times:
            if prev_time is not None and prev_time >= current_time:
                production = get_power_production(prev_time)
                consumption = core.get_power_consumption(prev_time)
                if production > consumption:
                    day_periods[(prev_time, time)] = production - consumption
            prev_time = time
    return day_periods

def get_day_production_reference_times(date):
    time_list = []
    start_time = date.replace(hour=0, minute=0, second=0, microsecond=0) 
    end_time = start_time + timezone.timedelta(days=1)
    time = start_time
    while (time < end_time):
        power = get_power_production(time)
        if power > 0:
            time_list.append(time)
        time += timezone.timedelta(hours=1)
    end_time = time_list[-1] + timezone.timedelta(hours=1)
    time_list.append(end_time)
    return time_list

def get_power_production(time):
    power = 0
    queryset = ProductionData.objects.filter(month=time.month, hour=time.hour)
    for production in queryset:
        power += production.average_power_generated
    return power

def get_minimum_production_within(start_time, end_time):
    minimum_production = None
    if PhotovoltaicSystem.objects.exists():
        time = start_time
        while time < end_time:
            power_production = get_power_production(time)
            if minimum_production is None or power_production < minimum_production:
                minimum_production = power_production
            time += timezone.timedelta(hours=1)
    return minimum_production

def start_of_next_month(date):
    return timezone.datetime(
        year=date.year + floor((date.month + 1) / 12),
        month=(date.month + 1) % 12,
        day=1).astimezone(timezone.get_current_timezone())