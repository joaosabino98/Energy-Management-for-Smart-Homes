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
    if end_time is None:
        return Execution.objects.filter(appliance=battery.appliance, end_time__gt=start_time)
    return Execution.objects.filter(appliance=battery.appliance, start_time__lte=end_time, end_time__gt=start_time)

def get_battery_charge_within(start_time, end_time):
    return get_battery_executions_within(start_time, end_time).filter(profile__rated_power__gt=0)

def get_battery_discharge_within(start_time, end_time):
    return get_battery_executions_within(start_time, end_time).filter(profile__rated_power__lt=0)

def get_battery_discharge_reference_times_within(start_time, end_time):
    time_list = [start_time, end_time]
    queryset = get_battery_discharge_within(start_time, end_time)
    for discharge in queryset:
        if discharge.start_time > start_time:
            time_list.append(discharge.start_time)
        if discharge.end_time < end_time:
            time_list.append(discharge.end_time)
    time_list.sort()
    return time_list

def get_last_battery_execution():
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return Execution.objects.none()
    return Execution.objects.filter(appliance=battery.appliance).order_by('end_time').last()

def get_last_battery_discharge():
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return Execution.objects.none()
    return Execution.objects.filter(appliance=battery.appliance, profile__rated_power__lt=0).order_by('end_time').last()

def get_battery_energy(time=None):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return 0
    queryset = Execution.objects.filter(appliance=battery.appliance, start_time__gte=battery.last_full_charge_time)
    if time is not None:
        queryset = queryset.exclude(start_time__gte=time)
    energy = battery.total_energy_capacity
    for execution in queryset:
        power = execution.profile.rated_power
        energy += power_to_energy(execution.start_time,
            execution.end_time if execution.end_time < time else time,
            power)
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

def get_maximum_battery_power_discharge_within(start_time, end_time):
    maximum_discharge = 0
    if BatteryStorageSystem.get_system() is not None:
        reference_times = get_battery_discharge_reference_times_within(start_time, end_time)
        for time in reference_times:
            power_discharge = get_battery_power_discharge(time)
            if power_discharge > maximum_discharge:
                maximum_discharge = power_discharge
    return maximum_discharge

def get_maximum_possible_battery_energy_discharge(start_time):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return 0
    minimum_energy = floor(battery.total_energy_capacity * (1 - battery.depth_of_discharge))
    minimum_energy_available = energy_available = get_battery_energy(start_time)
    queryset = get_battery_executions_within(start_time, None)
    for battery_execution in queryset:
        start_time_after_measurement = battery_execution.start_time if battery_execution.start_time > start_time else start_time
        energy_available += power_to_energy(start_time_after_measurement, battery_execution.end_time, battery_execution.profile.rated_power)
        if energy_available < minimum_energy_available:
            minimum_energy_available = energy_available
    return minimum_energy_available - minimum_energy
    
# Available if:
# 1. Battery exists
# 2. Battery is not charging
# 3. Battery available power output > power needed
# 4. Battery energy unscheduled for consumption > energy needed
def get_battery_discharge_available(start_time, end_time):
    battery = BatteryStorageSystem.get_system()
    if battery is None or get_battery_charge_within(start_time, end_time):
        return 0
    power_discharge = get_maximum_battery_power_discharge_within(start_time, end_time)
    maximum_remaining_power_discharge = battery.continuous_power - power_discharge
    maximum_remaining_energy_discharge = get_maximum_possible_battery_energy_discharge(start_time)
    return min(maximum_remaining_power_discharge, energy_to_power(start_time, end_time, maximum_remaining_energy_discharge))

def is_battery_discharge_available(execution, start_time):
    battery = BatteryStorageSystem.get_system()
    if battery is None or get_battery_charge_within(start_time, end_time):
        return False
    end_time = core.calculate_execution_end_time(execution, start_time)
    battery_energy_needed = power_to_energy(start_time, end_time, execution.profile.rated_power)
    if get_maximum_possible_battery_energy_discharge(start_time) > battery_energy_needed:
        return True
    else:
        return False

# battery charge is interruptible if future consumptions don't consume beyond depth of discharge
def is_battery_charge_interruptible(execution):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    battery_energy_provided = power_to_energy(execution.start_time, execution.end_time, execution.profile.rated_power)
    if get_maximum_possible_battery_energy_discharge(execution.end_time) > battery_energy_provided:
        return True
    else:
        return False

def create_battery_execution(start_time, end_time, power):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    profile, _ = battery.appliance.profiles.get_or_create(
            name=f"BSS {power}W Charge" if power > 0 else f"BSS {-power}W Discharge",
            defaults={
                "schedulability": INTERRUPTIBLE if power > 0 else NONINTERRUPTIBLE,
                "maximum_delay": None,
                "rated_power": power,
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

# used before executions are scheduled to temporarily increase threshold
def schedule_battery_discharge_on_consumption_above_threshold(execution, current_time, start_time, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    end_time = core.calculate_execution_end_time(execution, start_time)
    battery_power_needed = max(execution.profile.rated_power - get_power_available_within(start_time, end_time), get_battery_discharge_available(start_time, end_time))
    execution = create_battery_execution(start_time, end_time, -battery_power_needed)
    if start_time == current_time:
        core.start_execution(execution, None, debug)
    else:
        core.start_execution(execution, start_time, debug)

# used after executions are scheduled to ensure load balancing
def schedule_battery_discharge_on_high_demand(current_time, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is not None:
        high_demand = get_high_consumption_periods(current_time)
        for period in high_demand:
            if get_battery_discharge_available(period[0], period[1]) > battery.continuous_power * 0.1:
                battery_power_needed = min(get_battery_discharge_available(period[0], period[1]), high_demand[period])
                execution = create_battery_execution(period[0], period[1], -battery_power_needed)
                if period[0] == current_time:
                    core.start_execution(execution, None, debug)
                else:
                    core.start_execution(execution, period[0], debug)

def attempt_schedule_battery_charge_on_solar(current_time, start_time, energy_needed, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()
    photovoltaic_system = PhotovoltaicSystem.get_system()
    if photovoltaic_system is None:
        return False

    overproduction = get_day_periods_without_full_solar_utilization(start_time)
    energy_to_allocate = 0
    for period in overproduction:
        if get_battery_executions_within(period[0], period[1]):
            continue
        power = overproduction[period] if overproduction[period] < battery.continuous_power else battery.continuous_power
        energy_to_allocate += power_to_energy(period[0], period[1], power)
    if energy_to_allocate >= energy_needed:
        for period in overproduction:
            if get_battery_executions_within(period[0], period[1]):
                continue
            power = min(battery.continuous_power, overproduction[period], energy_to_power(period[0], period[1], energy_needed))
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

#TODO change same thing on solar
def schedule_battery_charge_on_low_demand(current_time, start_time, energy_needed, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        raise NoBSSystemException()

    low_demand = get_low_consumption_day_periods(start_time)
    for period in low_demand:
        if get_battery_executions_within(period[0], period[1]):
            continue
        power = min(battery.continuous_power, low_demand[period], energy_to_power(period[0], period[1], energy_needed))
        energy_needed -= power_to_energy(period[0], period[1], power)
        execution = create_battery_execution(period[0], period[1], power)
        if period[0] == current_time:
            core.start_execution(execution, None, debug)
        else:
            core.start_execution(execution, period[0], debug)
        if energy_needed < battery.total_energy_capacity * 0.01:
            break

def schedule_battery_charge(start_time=None, debug=False):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return NoBSSystemException()
    now = timezone.now()
    if start_time is None:
        start_time = now
    energy_needed = battery.total_energy_capacity - get_battery_energy(start_time)
    if energy_needed > battery.total_energy_capacity * 0.01:
        success = attempt_schedule_battery_charge_on_solar(now, start_time, energy_needed, debug)
        if not success:
            schedule_battery_charge_on_low_demand(now, start_time, energy_needed, debug)

def get_high_consumption_periods(start_time):
    day_periods = {}
    if core.get_unfinished_executions() is not None:
        end_time = core.get_unfinished_executions().last().end_time
        reference_times = core.get_consumption_reference_times_within(start_time, end_time)
        prev_time = None
        for time in reference_times:
            if prev_time is not None and prev_time >= start_time:
                high_consumption_threshold = get_power_available_within(prev_time, time) * 0.7
                consumption = core.get_maximum_consumption_within(prev_time, time)
                if high_consumption_threshold < consumption:
                    allocable_power = consumption - floor(get_power_available_within(prev_time, time) * 0.5)
                    day_periods[(prev_time, time)] = allocable_power
            prev_time = time
        day_periods = compact_periods(day_periods)
    return day_periods

def get_low_consumption_day_periods(start_time):
    day_periods = {}
    reference_times = get_day_reference_times(start_time)
    prev_time = None
    for time in reference_times:
        if prev_time is not None and prev_time >= start_time:
            low_consumption_threshold = get_power_available_within(prev_time, time) * 0.3
            consumption = core.get_maximum_consumption_within(prev_time, time)
            if low_consumption_threshold > consumption:
                allocable_power = floor(get_power_available_within(prev_time, time) * 0.5) - consumption
                day_periods[(prev_time, time)] = allocable_power
        prev_time = time
    # day_periods = compact_periods(day_periods)
    return day_periods

def get_day_periods_without_full_solar_utilization(start_time):
    day_periods = {}
    if PhotovoltaicSystem.get_system() is not None:
        reference_times = get_day_reference_times(start_time)
        prev_time = None
        for time in reference_times:
            if prev_time is not None and prev_time >= start_time:
                production = get_power_production(prev_time)
                consumption = core.get_power_consumption(prev_time)
                if production > consumption:
                    day_periods[(prev_time, time)] = production - consumption
            prev_time = time
        day_periods = compact_periods(day_periods)
    return day_periods

def get_day_reference_times(current_time):
    start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + timezone.timedelta(days=1)
    consumption_reference_times = core.get_consumption_reference_times_within(start_time, end_time)
    reference_times = sorted(list(dict.fromkeys(consumption_reference_times + [current_time])))
    return reference_times

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

def compact_periods(day_periods):
    new_periods = {}
    if day_periods:
        block_start_time = next(iter(day_periods))[0]
        block_end_time = next(iter(day_periods))[1]
        block_energy = day_periods[next(iter(day_periods))]
        for period in day_periods:
            if day_periods[period] == block_energy:
                block_end_time = period[1]
            else:
                new_periods[(block_start_time, block_end_time)] = block_energy
                block_start_time = period[0]
                block_end_time = period[1]
                block_energy = day_periods[period]
        new_periods[(block_start_time, block_end_time)] = block_energy
    return new_periods

def power_to_energy(start_time, end_time, power):
    return floor(power * (end_time - start_time).seconds/3600)

def energy_to_power(start_time, end_time, energy):
    return floor(energy / ((end_time - start_time).seconds/3600)) if (end_time - start_time).seconds != 0 else 0