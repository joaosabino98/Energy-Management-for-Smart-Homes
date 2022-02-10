import os
import django
from scheduler.models import AppVals, BatteryConsumption, ProductionData
from django.utils import timezone
from math import floor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

def get_unfinished_battery_usage():
    return BatteryConsumption.objects.exclude(end_time__lt=timezone.now()).order_by('end_time')

def get_battery_usage_within(start_time, end_time):
    unfinished = get_unfinished_battery_usage()
    return 

def get_production_data_within(start_time, end_time):
    data = ProductionData.objects.filter(month__lte=end_time.month).filter(month__gte=start_time.month)
    end_of_start_month = start_of_next_month(start_time)
    start_of_end_month = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if (end_of_start_month - start_time < timezone.timedelta(days=1)):
        data = data.exclude(month=start_time.month, hour__lt=start_time.hour)
    if (end_time - start_of_end_month < timezone.timedelta(days=1)):
        data = data.exclude(month=end_time.month, hour__gt=end_time.hour)
    
    return data

def start_battery(start_time, end_time):
    pass

def finish_battery():
    pass

def start_of_next_month(date):
    return timezone.datetime(
        year=date.year + floor((date.month + 1) / 12),
        month=(date.month + 1) % 12,
        day=1).astimezone(timezone.get_current_timezone())