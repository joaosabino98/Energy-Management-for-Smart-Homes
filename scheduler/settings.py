# Scheduler variables

from django.utils import timezone
import zoneinfo

INTERRUPTIBLE = 0
NONINTERRUPTIBLE = 1

IMMEDIATE = 0
NORMAL = 1
LOW_PRIORITY = 2

SIMPLE = 0
TIME_BAND = 1

SCHEDULABILITY_OPTIONS = [
    (INTERRUPTIBLE, 'Interruptible'),
    (NONINTERRUPTIBLE, 'Non-interruptible')
]

PRIORITY_OPTIONS = [
    (IMMEDIATE, "Immediate"),
    (NORMAL, "Normal"),
    (LOW_PRIORITY, "Low-priority"),
]

STRATEGY_OPTIONS = [
    (SIMPLE, "Simple"),
    (TIME_BAND, "Prioritize low-demand hours, avoid periods of high demand")
]

INF_DATE = timezone.datetime.max.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))