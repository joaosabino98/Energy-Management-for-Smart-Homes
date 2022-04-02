# Scheduler variables

INTERRUPTIBLE = 0
NONINTERRUPTIBLE = 1

IMMEDIATE = 0
NORMAL = 1
LOW_PRIORITY = 2

PEAK_SHAVING = 0
LOAD_DISTRIBUTION = 1
TIME_BAND = 2

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
    (PEAK_SHAVING, "Schedule ASAP"),
    (LOAD_DISTRIBUTION, "Schedule to lowest consumption period, within maximum delay"),
    (TIME_BAND, "Prioritize low-demand hours, avoid periods of high demand")
]