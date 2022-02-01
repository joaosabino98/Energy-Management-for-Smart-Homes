# Scheduler variables

INTERRUPTIBLE = 0
NONINTERRUPTIBLE = 1

IMMEDIATE = 0
NORMAL = 1
LOW_PRIORITY = 2

SCHEDULABILITY_OPTIONS = [
    (INTERRUPTIBLE, 'Interruptible'),
    (NONINTERRUPTIBLE, 'Non-interruptible')
]

PRIORITY_OPTIONS = [
    (IMMEDIATE, "Immediate"),
    (NORMAL, "Normal"),
    (LOW_PRIORITY, "Low-priority"),
]