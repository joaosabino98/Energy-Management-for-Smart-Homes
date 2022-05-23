import os
import django
from home.settings import INF_DATE
import processor.core as core
from scheduler.models import Home, Execution, NoBSSystemException, NoPVSystemException, ProductionData
from django.utils import timezone
from math import floor

from scheduler.settings import INTERRUPTIBLE, LOW_PRIORITY, NONINTERRUPTIBLE
from processor.tools import compact_periods, power_to_energy, energy_to_power

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

# battery executions are accounted for in consumption
def get_power_threshold_within(start_time, end_time):
    home = Home.objects.get(pk=core.home_id)
    threshold = home.consumption_threshold
    production = get_minimum_production_within(start_time, end_time)
    power = threshold + production
    return power

def get_battery_executions_within(start_time, end_time):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return Execution.objects.none()
    battery = home.batterystoragesystem
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
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return Execution.objects.none()
    battery = home.batterystoragesystem
    return Execution.objects.filter(appliance=battery.appliance).order_by('end_time').last()

def get_last_battery_charge():
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return Execution.objects.none()
    battery = home.batterystoragesystem
    return Execution.objects.filter(appliance=battery.appliance, profile__rated_power__gt=0).order_by('end_time').last()

def get_last_battery_discharge():
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return Execution.objects.none()
    battery = home.batterystoragesystem
    return Execution.objects.filter(appliance=battery.appliance, profile__rated_power__lt=0).order_by('end_time').last()

def get_battery_energy(time=None):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return 0
    battery = home.batterystoragesystem
    queryset = Execution.objects.filter(appliance=battery.appliance, start_time__gte=battery.last_full_charge_time)
    if time is not None:
        queryset = queryset.exclude(start_time__gte=time)
    energy = battery.total_energy_capacity
    for execution in queryset:
        power = execution.profile.rated_power        
        energy += power_to_energy(execution.start_time,
            execution.end_time if time is None or execution.end_time < time else time,
            power)
    return energy

def get_allocable_battery_energy_charge(day_periods):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    battery = home.batterystoragesystem
    energy_to_allocate = 0
    for period in day_periods:
        if get_battery_executions_within(period[0], period[1]):
            continue
        power = min(day_periods[period], battery.continuous_power)
        energy_to_allocate += power_to_energy(period[0], period[1], power)
    return energy_to_allocate

def get_maximum_possible_battery_energy_charge(start_time):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return 0
    battery = home.batterystoragesystem
    maximum_energy = battery.total_energy_capacity
    maximum_energy_available = energy_available = get_battery_energy(start_time)
    queryset = get_battery_executions_within(start_time, None)
    for battery_execution in queryset:
        start_time_after_measurement = battery_execution.start_time if battery_execution.start_time > start_time else start_time
        energy_available += power_to_energy(start_time_after_measurement, battery_execution.end_time, battery_execution.profile.rated_power)
        if energy_available > maximum_energy_available:
            maximum_energy_available = energy_available
    return maximum_energy - maximum_energy_available

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
    home = Home.objects.get(pk=core.home_id)
    if hasattr(home, "batterystoragesystem"):
        reference_times = get_battery_discharge_reference_times_within(start_time, end_time)
        for time in reference_times:
            power_discharge = get_battery_power_discharge(time)
            if minimum_discharge is None or power_discharge < minimum_discharge:
                minimum_discharge = power_discharge
    return minimum_discharge

def get_maximum_battery_power_discharge_within(start_time, end_time):
    maximum_discharge = 0
    home = Home.objects.get(pk=core.home_id)
    if hasattr(home, "batterystoragesystem"):
        reference_times = get_battery_discharge_reference_times_within(start_time, end_time)
        for time in reference_times:
            power_discharge = get_battery_power_discharge(time)
            if power_discharge > maximum_discharge:
                maximum_discharge = power_discharge
    return maximum_discharge

def get_maximum_possible_battery_energy_discharge(start_time):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        return 0
    battery = home.batterystoragesystem
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
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem") or get_battery_charge_within(start_time, end_time):
        return 0
    battery = home.batterystoragesystem
    power_discharge = get_maximum_battery_power_discharge_within(start_time, end_time)
    maximum_remaining_power_discharge = battery.continuous_power - power_discharge
    maximum_remaining_energy_discharge = get_maximum_possible_battery_energy_discharge(start_time)
    return min(maximum_remaining_power_discharge, energy_to_power(start_time, end_time, maximum_remaining_energy_discharge))

def is_battery_discharge_available(execution, start_time):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem") or get_battery_charge_within(start_time, end_time):
        return False
    end_time = core.calculate_execution_end_time(execution, start_time)
    battery_energy_needed = power_to_energy(start_time, end_time, execution.profile.rated_power)
    if get_maximum_possible_battery_energy_discharge(start_time) > battery_energy_needed:
        return True
    else:
        return False

# battery charge is interruptible if future consumptions don't consume beyond depth of discharge
def is_battery_charge_interruptible(execution):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    battery_energy_provided = power_to_energy(execution.start_time, execution.end_time, execution.profile.rated_power)
    if get_maximum_possible_battery_energy_discharge(execution.end_time) > battery_energy_provided:
        return True
    else:
        return False

def create_battery_execution(start_time, end_time, power):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    battery = home.batterystoragesystem
    charge_time = timezone.timedelta(seconds=floor(battery.total_energy_capacity / power * 3600))
    profile, _ = battery.appliance.profiles.get_or_create(
            name=f"BSS {power}W Charge" if power > 0 else f"BSS {-power}W Discharge",
            defaults={
                "schedulability": INTERRUPTIBLE if power > 0 else NONINTERRUPTIBLE,
                "maximum_duration_of_usage": charge_time,
                "rated_power": power,
                "priority": LOW_PRIORITY,
                "hidden": True
            }
        )
    return Execution.objects.create(
        home=home,
        appliance=battery.appliance,
        profile=profile,
        start_time=start_time,
        end_time=end_time
    )

def start_battery_executions(energy_needed, day_periods, debug=False):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    battery = home.batterystoragesystem
    for period in day_periods:
        if get_battery_executions_within(period[0], period[1]):
            continue
        power = min(battery.continuous_power, day_periods[period], energy_to_power(period[0], period[1], energy_needed))
        energy_needed -= power_to_energy(period[0], period[1], power)
        execution = create_battery_execution(period[0], period[1], power)
        core.start_execution(execution, period[0], debug)
        if energy_needed < battery.total_energy_capacity * 0.01:
            break

# used before executions are scheduled to temporarily increase threshold
def schedule_battery_discharge_on_consumption_above_threshold(start_time, end_time, debug=False):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    # battery_power_needed = min(get_battery_discharge_available(period[0], period[1]), power_needed)
    battery_power_available = get_battery_discharge_available(start_time, end_time)
    execution = create_battery_execution(start_time, end_time, -battery_power_available)
    core.start_execution(execution, start_time, debug)

# used after executions are scheduled to ensure load balancing
def schedule_battery_discharge_on_high_demand(current_time, debug=False):
    home = Home.objects.get(pk=core.home_id)
    if hasattr(home, "batterystoragesystem"):
        battery = home.batterystoragesystem
        high_demand = get_high_consumption_periods(current_time)
        for period in high_demand:
            if get_battery_discharge_available(period[0], period[1]) > battery.continuous_power * 0.1:
                battery_power_needed = min(get_battery_discharge_available(period[0], period[1]), high_demand[period])
                execution = create_battery_execution(period[0], period[1], -battery_power_needed)
                core.start_execution(execution, period[0], debug)

def schedule_battery_charge_on_solar(start_time, energy_needed, debug=False):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    if not hasattr(home, "photovoltaicsystem"):
        raise NoPVSystemException()
    low_demand = get_low_consumption_solar_day_periods(start_time, 0)
    energy_to_allocate = get_allocable_battery_energy_charge(low_demand)
    print(f"Energy on stategy 1: {energy_to_allocate}Wh")
    if energy_to_allocate < energy_needed: 
        low_demand = get_low_consumption_solar_day_periods(start_time, 0.1)
        energy_to_allocate = get_allocable_battery_energy_charge(low_demand)
        print(f"Energy on stategy 2: {energy_to_allocate}Wh")
        if energy_to_allocate < energy_needed: 
            low_demand = get_low_consumption_solar_day_periods(start_time, 0.25)
            energy_to_allocate = get_allocable_battery_energy_charge(low_demand)
            print(f"Energy on stategy 3: {energy_to_allocate}Wh")
            if energy_to_allocate < energy_needed: 
                low_demand = get_low_consumption_day_periods(start_time)
                energy_to_allocate = get_allocable_battery_energy_charge(low_demand)
                print(f"Energy on stategy 4: {energy_to_allocate}Wh")
    start_battery_executions(energy_needed, low_demand, debug)

def schedule_battery_charge_on_low_demand(start_time, energy_needed, debug=False):
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    low_demand = get_low_consumption_day_periods(start_time)
    start_battery_executions(energy_needed, low_demand, debug)

# Should be called after last battery execution.
# If not, it will charge as much as future executions allow without going over total capacity
def schedule_battery_charge(start_time=None, debug=False):
    if start_time is None:
        start_time = timezone.now()
    home = Home.objects.get(pk=core.home_id)
    if not hasattr(home, "batterystoragesystem"):
        raise NoBSSystemException()
    battery = home.batterystoragesystem
    energy_needed = get_maximum_possible_battery_energy_charge(start_time)
    if energy_needed > battery.total_energy_capacity * 0.01:
        if hasattr(home, "photovoltaicsystem"):
            schedule_battery_charge_on_solar(start_time, energy_needed, debug)
        else:
            schedule_battery_charge_on_low_demand(start_time, energy_needed, debug)

def get_high_consumption_periods(start_time):
    day_periods = {}
    if core.get_unfinished_executions() is not None:
        end_time = core.get_unfinished_executions().last().end_time
        reference_times = core.get_consumption_reference_times_within(start_time, end_time)
        prev_time = None
        for time in reference_times:
            if prev_time is not None and prev_time >= start_time:
                high_consumption_threshold = floor(get_power_threshold_within(prev_time, time) * 0.7)
                consumption = core.get_maximum_consumption_within(prev_time, time)
                if high_consumption_threshold < consumption:
                    allocable_power = consumption - high_consumption_threshold
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
            low_consumption_threshold = floor(get_power_threshold_within(prev_time, time) * 0.3)
            consumption = core.get_maximum_consumption_within(prev_time, time)
            if low_consumption_threshold > consumption:
                allocable_power = low_consumption_threshold - consumption
                day_periods[(prev_time, time)] = allocable_power
        prev_time = time
    # day_periods = compact_periods(day_periods)
    return day_periods

def get_low_consumption_solar_day_periods(start_time, threshold_multiplier):
    day_periods = {}
    home = Home.objects.get(pk=core.home_id)
    if hasattr(home, "photovoltaicsystem"):
        reference_times = get_day_reference_times(start_time)
        prev_time = None
        for time in reference_times:
            if prev_time is not None and prev_time >= start_time:
                low_consumption_threshold = floor(home.consumption_threshold * threshold_multiplier) + get_power_production(prev_time)
                consumption = core.get_power_consumption(prev_time)
                if low_consumption_threshold > consumption:
                    day_periods[(prev_time, time)] = low_consumption_threshold - consumption
            prev_time = time
        day_periods = compact_periods(day_periods)
    return day_periods

def get_day_reference_times(current_time):
    start_time = current_time
    end_time = start_time + timezone.timedelta(days=1)
    consumption_reference_times = core.get_consumption_reference_times_within(start_time, end_time)
    return consumption_reference_times

def get_power_production(time):
    home = Home.objects.get(pk=core.home_id)
    power = 0
    if hasattr(home, "photovoltaicsystem"):
        pv = home.photovoltaicsystem
        queryset = ProductionData.objects.filter(system=pv, month=time.month, hour=time.hour)
        for production in queryset:
            power += production.average_power_generated
    return power

def get_minimum_production_within(start_time, end_time):
    minimum_production = None
    home = Home.objects.get(pk=core.home_id)
    if hasattr(home, "photovoltaicsystem"):
        time = start_time
        while time < end_time:
            power_production = get_power_production(time)
            if minimum_production is None or power_production < minimum_production:
                minimum_production = power_production
            time += timezone.timedelta(hours=1)
    if minimum_production is None:
        minimum_production = 0
    return minimum_production