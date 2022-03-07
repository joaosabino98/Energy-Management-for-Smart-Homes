import math
import os
import django
import processor.core as core
from scheduler.models import AppVals, BatteryConsumption, BatteryStorageSystem, Execution, PhotovoltaicSystem, ProductionData, Profile
from django.utils import timezone
from math import floor

from scheduler.settings import INTERRUPTIBLE, LOAD_DISTRIBUTION, LOW_PRIORITY, PEAK_SHAVING, TIME_BAND

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

def get_battery_charge_within(start_time, end_time):
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return Execution.objects.none()
    return Execution.objects.filter(appliance=battery.appliance, start_time__lte=end_time, end_time__gt=start_time)

def get_battery_discharge_within(start_time, end_time):
    return BatteryConsumption.objects.filter(start_time__lte=end_time, end_time__gt=start_time)

def get_battery_charge_since_last_charge():
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return Execution.objects.none()
    return Execution.objects.filter(start_time__gt=battery.last_full_charge_time, appliance=battery.appliance)

def get_battery_discharge_since_last_charge():
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return BatteryConsumption.objects.none()
    next_charge = Execution.objects.filter(start_time__gt=battery.last_full_charge_time, appliance=battery.appliance).first()
    if next_charge is None:
        return BatteryConsumption.objects.filter(start_time__gte=battery.last_full_charge_time)
    else:
        return BatteryConsumption.objects.filter(start_time__gte=battery.last_full_charge_time, end_time__lte=next_charge.start_time)

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

def get_battery_energy_discharge():
    battery = BatteryStorageSystem.get_system()
    if battery is None:
        return None
    queryset = get_battery_discharge_since_last_charge()
    energy = 0
    for discharge in queryset:
        energy += floor((discharge.end_time - discharge.start_time).seconds / 3600 * discharge.power_used)
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
        power += discharge.power_used
    return power

def get_minimum_battery_power_discharge_within(start_time, end_time):
    minimum_discharge = None
    if (BatteryStorageSystem.get_system() is not None):
        reference_times = get_battery_discharge_reference_times_within(start_time, end_time)
        for time in reference_times:
            power_discharge = get_battery_power_discharge(time)
            if minimum_discharge is None or power_discharge < minimum_discharge:
                minimum_discharge = power_discharge
    return minimum_discharge

def get_available_discharge_time(execution, available_periods):
    for period in available_periods:
        #check if battery is not charging
        #check if enough energy is available
        #check if current discharge power is below power capacity
        pass

def choose_battery_charge_time(energy_needed):
    battery = BatteryStorageSystem.get_system()
    if (battery is None):
        return None
    last_discharge = get_battery_discharge_since_last_charge().order_by('end_time').last()

    power = battery.maximum_power_transfer if energy_needed > battery.maximum_power_transfer else energy_needed       
    execution = create_battery_charge(power=power)

    available_periods = core.get_available_execution_times(execution, last_discharge.end_time)
    sorted_periods = {k: v for k, v in sorted(available_periods.items(), key=lambda item: item[1])}
    for period in sorted_periods:
        if get_battery_power_charge(period[0]) == 0:
            return period, power

def create_battery_charge(start_time, end_time, power):
    battery = BatteryStorageSystem.get_system()
    if (battery is None):
        return None
    profile = battery.appliance.profiles.get_or_create(
            rated_power=power,
            defaults={
                "name": f"BSS Charger {power}W",
                "schedulability": INTERRUPTIBLE,
                "priority": LOW_PRIORITY,
            }
        )
    return Execution.objects.create(
        appliance=battery.appliance,
        profile=profile,
        start_time=start_time,
        end_time=end_time
    )

# Battery charge strategy w/ PV system:
# 1. Charge using unused generated energy
# 2. Charge using load balancing strategy
def schedule_battery_charge():
    battery = BatteryStorageSystem.get_system()
    if (battery is None):
        return None
    photovoltaic_system = PhotovoltaicSystem.get_system()
    energy_needed = battery.total_energy_capacity - get_battery_energy_discharge()
    minimum_charge_threshold = battery.total_energy_capacity * (1 - battery.depth_of_discharge/100)
    if photovoltaic_system is not None:
        overproduction = get_day_periods_without_full_solar_utilization(timezone.now())
        for period in overproduction:
            power = overproduction[period] if overproduction[period] < battery.maximum_power_transfer else battery.maximum_power_transfer
            if (energy_needed - power_to_energy(period[0], period[1], power) > minimum_charge_threshold):
                energy_needed -= power_to_energy(period[0], period[1], power)
                execution = create_battery_charge(period[0], period[1], power)
                core.start_execution(execution, period[0])
            elif (energy_needed > minimum_charge_threshold):
                power = energy_to_power(period[0], period[1], energy_needed)
                energy_needed = 0
                execution = create_battery_charge(period[0], period[1], power)
                core.start_execution(execution, period[0])
            else:
                break

    while energy_needed > minimum_charge_threshold:
        time, energy = choose_battery_charge_time(energy_needed)
        if time is not None:
            execution = create_battery_charge(period[0], period[1], power)
            core.start_execution(execution, period[0], period[1])
            energy_needed -= energy



        #TODO: detect last charge to set it to last_full_charge_time?
        #TODO: finish get_available_execution_times to return {(start, end): power}, then schedule here or in choose_execution_time

def power_to_energy(start_time, end_time, power):
    return math.floor(power * (start_time - end_time).seconds/3600)

def energy_to_power(start_time, end_time, energy):
    return math.floor(energy / ((start_time - end_time).seconds/3600))

# return {(start, end): power}
def get_day_periods_without_full_solar_utilization(date):
    periods = {}
    production_reference_times = get_production_reference_times_within(date)
    start_time = production_reference_times[0]
    end_time = production_reference_times[-1]
    reference_times = list(dict.fromkeys(production_reference_times + core.get_consumption_reference_times_within(start_time, end_time)))
    reference_times.sort()

    prev_time = None
    for time in reference_times:
        if prev_time is not None:
            production = get_power_production(prev_time)
            consumption = core.get_power_consumption(prev_time)
            if (production > consumption):
                periods[(prev_time, time)] = production - consumption
        prev_time = time
    return periods

def get_production_reference_times_within(day):
    time_list = []
    start_time = day.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + timezone.timedelta(days=1)
    time = start_time
    while (time < end_time):
        power = get_power_production(time)
        if (power > 1):
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
    if (PhotovoltaicSystem.objects.exists()):
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