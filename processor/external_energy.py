import os
import django
from scheduler.models import AppVals, BatteryConsumption, BatteryStorageSystem, PhotovoltaicSystem, ProductionData
from django.utils import timezone
from math import floor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

def get_unfinished_battery_discharge():
    return BatteryConsumption.objects.exclude(end_time__lt=timezone.now()).order_by('end_time')

def get_battery_discharge_within(start_time, end_time):
    unfinished = get_unfinished_battery_discharge()
    return unfinished.filter(start_time__lte=end_time, end_time__gte=start_time)

def get_battery_reference_times_within(start_time, end_time):
    time_list = [start_time, end_time]
    queryset = get_battery_discharge_within(start_time, end_time)
    for discharge in queryset:
        if discharge.start_time >= start_time:
            time_list.append(discharge.start_time)
        if discharge.end_time <= end_time:
            time_list.append(discharge.end_time)
    time_list.sort()
    return time_list

def get_battery_discharge(time):
    power = 0
    queryset = get_battery_discharge_within(time, time)
    for discharge in queryset:
        power += discharge.power_used
    return power

def get_minimum_battery_discharge_within(start_time, end_time):
    minimum_discharge = None
    if (BatteryStorageSystem.objects.exists()):
        reference_times = get_battery_reference_times_within(start_time, end_time)
        for time in reference_times:
            power_discharge = get_battery_discharge(time)
            if minimum_discharge is None or power_discharge < minimum_discharge:
                minimum_discharge = power_discharge
    return minimum_discharge

def manage_battery_charge_cycle():
    pass

def schedule_battery_charge(bss, start_time, end_time, power):
    pass

def schedule_battery_discharge(bss, start_time, end_time, power):
    pass

# def get_production_data_within(start_time, end_time):
#     data = ProductionData.objects.filter(month__lte=end_time.month).filter(month__gte=start_time.month)
#     end_of_start_month = start_of_next_month(start_time)
#     start_of_end_month = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

#     if (start_time.month == end_time.month and end_time - start_time < timezone.timedelta(days=1)):
#         if (start_time.hour <= end_time.hour):
#             data = data.exclude(hour__lt=start_time.hour).exclude(hour__gt=end_time.hour)
#         else:
#             data = data.exclude(hour__lt=start_time.hour, hour__gt=end_time.hour)
#     else:
#         if (end_of_start_month - start_time < timezone.timedelta(days=1)):
#             data = data.exclude(month=start_time.month, hour__lt=start_time.hour)
#         if (end_time - start_of_end_month < timezone.timedelta(days=1)):
#             data = data.exclude(month=end_time.month, hour__gt=end_time.hour)
#     return data

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