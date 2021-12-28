# Scheduler variables

INTERRUPTIBLE = 0
NONINTERRUPTIBLE = 1
NONSCHEDULABLE = 2

IMMEDIATE = 0
NORMAL = 1
LOW_PRIORITY = 2

SCHEDULABILITY_OPTIONS = [
    (INTERRUPTIBLE, 'Schedulable, interruptible'),
    (NONINTERRUPTIBLE, 'Schedulable, non-interruptible'),
    (NONSCHEDULABLE, 'Non-schedulable'),
]

PRIORITY_OPTIONS = [
    (IMMEDIATE, "Immediate"),
    (NORMAL, "Normal"),
    (LOW_PRIORITY, "Low-priority"),
]