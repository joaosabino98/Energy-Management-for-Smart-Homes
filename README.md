# Energy Management for Smart Homes

## Common commands
### Go to project folder
`cd C:\Users\jsabi\Documents\Tese\home`

### Create database schema
`python manage.py makemigrations`

### Apply schema
`python manage.py migrate`

### Create admin (jsabi)
`python manage.py createsuperuser`

### Run server
`python manage.py runserver`

### Load fixture
`python manage.py loaddata <fixture>`

### Create fixtures
`python manage.py dumpdata`

### Access objects through shell
`python manage.py shell`

### Run tests
`python manage.py test [--tag=core] [--exclude-tag=slow]`

### Clean database and start development server (PowerShell script)
`.\clean_setup.ps1`

### Run schedule manager (management command)
`python manage.py runmanager`


## Common executions (copy / paste)
### Recreate DB and migrations, load sample fixture and run
```
.\scripts\clean_setup.ps1
```
### Run scheduler
```
python manage.py runscheduler
```
## Shell tests
### Create execution and schedule it
```
from manager.schedule_core import ScheduleManager
from scheduler.models import *
import pprint
s = ScheduleManager()
e = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
s.schedule_execution(e)
pprint.pprint(s.schedule)
```
### Test get_lower_priority_shiftable_executions
```
from manager.schedule_core import ScheduleManager
from scheduler.models import *
from django.utils import timezone
from datetime import timedelta

s = ScheduleManager()
rt1 = timezone.now() # 1 hour of remaining maximum delay
rt2 = timezone.now()-timedelta(seconds=2700) # 15 minutes remaining

# Interruptible, priority: 5
e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
# Interruptible, priority: 9
e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))

s.schedule_execution(e1)
s.schedule_execution(e2)

s.get_lower_priority_shiftable_executions(4)
s.get_lower_priority_shiftable_executions(7)
s.get_lower_priority_shiftable_executions(9)
s.get_lower_priority_shiftable_executions(10)
```
### Check get_current_schedule_slot
```
from manager.schedule_core import ScheduleManager
s = ScheduleManager()
s.get_current_schedule_slot()
```
### Test schedule_later
```
# Create 6 executions with the same priority.
# Executions e1 to e4 are scheduled immediately.
# For e5 and e6, schedule_execution() should consider that no execution can be shifted /
# and use schedule_later().

from manager.schedule_core import ScheduleManager
from scheduler.models import *
import pprint
s = ScheduleManager()
e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e6 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
s.schedule_execution(e1)
s.schedule_execution(e2)
s.schedule_execution(e3)
s.schedule_execution(e4)
s.schedule_execution(e5)
s.schedule_execution(e6)
pprint.pprint(s.schedule)
```
### Test shift_executions
```
# Sample test 1
# Create 4 executions with normal priority and a fifth with immediate priority.
# Executions e1 to e4 are scheduled immediately and take all the energy available.
# Using shift_executions, e5 must displace one of the previous executions for its exact execution time, \
# execute immediately and update the schedule accordingly.

from manager.schedule_core import ScheduleManager
from scheduler.models import *
import pprint
s = ScheduleManager()
e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=10),profile=Profile.objects.get(pk=13))
s.schedule_execution(e1)
s.schedule_execution(e2)
s.schedule_execution(e3)
s.schedule_execution(e4)
s.schedule_execution(e5)
pprint.pprint(s.schedule)

```
### Test shift_executions
```
# Sample test 2
# A slot is available for the shifted appliance but doesn't have enough duration: \
# Will it search for the first contiguous block of available slots correctly?
# TODO
```
### Test shift_executions
```
# Sample test 3
# more complex scenarios, idk
# TODO
```
### Test execution finish after 5 seconds
```
from manager.schedule_core import ScheduleManager
from scheduler.models import *
s = ScheduleManager()
e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=12),profile=Profile.objects.get(pk=13))
s.schedule_execution(e5)
```
### Test parse_time_to_slot
```
from manager.schedule_core import ScheduleManager
from django.utils import timezone
import pprint
s = ScheduleManager()
s.parse_time_to_slot("2021, 12, 7, 11, 55")
s.parse_time_to_slot("2021-12-7 11:55:00")
s.parse_time_to_slot("2021/12/7 11:55:00")
s.parse_time_to_slot(timezone.datetime(2021, 12, 7, 11, 55))

```
### Test previous_progress_time
```
from manager.schedule_core import ScheduleManager
from scheduler.models import *
import pprint
import time
s = ScheduleManager()
e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
s.schedule_execution(e1)
s.schedule_execution(e2)
s.schedule_execution(e3)
s.schedule_execution(e4)
time.sleep(5)
e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=10),profile=Profile.objects.get(pk=13))
s.schedule_execution(e5)
print(Execution.objects.get(pk=1).appliance.name)
print(Execution.objects.get(pk=6).appliance.name)
print(Execution.objects.get(pk=6).previous_progress_time)
print(Execution.objects.get(pk=6).end_time-Execution.objects.get(pk=6).start_time+Execution.objects.get(pk=6).previous_progress_time)
s.running

```

## General To-do
 * Check APScheduler support for storing jobs in db and resuming on restart (django-apscheduler) - DONE
 * Repopulate schedule daily (APScheduler decorator?) - DONE
 * Update priorities periodically (APScheduler decorator?) - DONE, requires better testing
 * FIX BUG: executions are constantly shifted back and forth because priority is recalculated - DONE
 . Add "previous_progress" field to execution
 . Don't calculate priority based on maximum wait / arrange deterministically based on current time-request time - DONE
 * Include support for energy generators (best way to represent energy addition? average, minimum, time-based?)
 * UI, etc
 
### Refactoring options:
1. ScheduleManager process receives communications: schedule_execution, finish_execution
 - more flexible and efficient

2. ScheduleManager keeps checking for database changes
 - start/finish_execution_job are no longer needed
 - new executions prompt schedule_execution
 - old executions are finished if time is exceeded
 - IDEAL DJANGO approach: runs periodically, state is not kept, appvals effectively manages if it runs periodically or not

## Technical Documentation

### Object classes

### SchedulerManager

The SchedulerManager receives requests from appliances that need to be executed or stopped, acting as a local server.  It is primarily responsible for managing execution lifecycles. To do so, it needs to keep track of the available energy resources across the next hours, accounting for the energy to be consumed by running or pending (scheduled) executions until their expected end.

Each execution has a priority ranging from 1 to 10, where 10 is the highest priority and 1 is the lowest. This priority is calculated when the start request is processed, based on the priority class and maximum delay parameters defined by the user, and updated periodically.



#### Start request handling logic

When a start request arrives, the script checks if there is enough available power to run the appliance immediately. This option is preferred in situations of low energy demand, 

> Setting: don't start immediately if execution is not interruptible? or don't start immediately if power is above xx% of limit?

#### Energy tracking
##### Time table
##### Timeslot definition

#### Application lifecycle

### Priority calculation
#### Update rules

### Interprocess communication
 - ZeroMQ (pyzmq)


> Users may decide to terminate the execution of an appliance before the time assumed by the script. 

> Keeping track of available energy resources, managing execution lifecycles and updating relative priorities.

