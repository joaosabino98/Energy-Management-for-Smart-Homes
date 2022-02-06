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

### Clean database and setup sample data (PowerShell script)
`.\scripts\clean_setup.ps1`

### Test scheduler
`python manage.py test`

## Shell tests
### Schedule execution
```
import processor.core as core
from scheduler.models import *
core.start()
e = Execution.objects.create(appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
core.schedule_execution(e)
e.delete()
```
### Test execution finish 
```
import processor.core as core
from scheduler.models import *
import time
core.start()
e = Execution.objects.create(appliance=Appliance.objects.get(pk=12),profile=Profile.objects.get(pk=13))
core.schedule_execution(e)
while e.status() != "Finished":
    e = Execution.objects.get(pk=e.id)

assert e.status() == "Finished"
e.delete()
```

## General To-do
 * Check APScheduler support for storing jobs in db and resuming on restart (django-apscheduler) - DONE
 * Repopulate schedule daily (APScheduler decorator?) - DONE
 * Update priorities periodically (APScheduler decorator?) - DONE, requires better testing
 * FIX BUG: executions are constantly shifted back and forth because priority is recalculated - DONE
 . Add "previous_progress" field to execution - DONE
 . Don't calculate priority based on maximum wait / arrange deterministically based on current time-request time - DONE
 * Create test_core (test_connector) with current functions, and enable background jobs in core - DONE
 * Include support for energy generators (best way to represent energy addition? average, minimum, time-based?)
 * New scheduling strategies: production-hours-first, battery-consumption-at-peak-hours-first
 * UI, etc

## Technical Documentation

### Object classes

### SchedulerManager

The SchedulerManager receives requests from appliances that need to be executed or stopped, acting as a local server. It is primarily responsible for managing execution lifecycles. To do so, it needs to keep track of the available energy resources across the next hours, accounting for the energy to be consumed by running or pending (scheduled) executions until their expected end.

Each execution has a priority ranging from 1 to 10, where 10 is the highest priority and 1 is the lowest. This priority is calculated when the start request is processed, based on the priority class and maximum delay parameters defined by the user, and updated periodically.



#### Start request handling logic

When a start request arrives, the script checks if there is enough available power to run the appliance immediately. This option is preferred in situations of low energy demand, 

> Setting: don't start immediately if execution is not interruptible? or don't start immediately if power is above xx% of limit?

#### Energy tracking
##### Time table
##### Timeslot definition

#### Appliance lifecycle

### Priority calculation
#### Update rules

---


### Appliance categorization
An effective HEMS solution depends on accurate parametrization of appliance behaviour and time sensitiveness. Appliances can be primarily categorized regarding their ability to interrupt and resume their work. Some appliances can stop and resume with little to no loss of progress, such as recent models of washing machines or HVAC. These machines either keep track of their current progress, or perform a single task with continuous output, where an interruption at opportune times is considered acceptable by the user. Appliances within this category are classified as interruptible. On the other hand, appliances that are unable to resume their progress on restart, require a significant amount of energy to go back to the state before shutdown, or simply require continuous execution to achieve a goal, are considered non-interruptible. Examples are the oven, coffee machine, or even the television during an important segment.
<!-- Non-schedulable appliances aren't really non-schedulable, just non-interruptible, immediate appliances with 0 maximum acceptable delay -->

### Future work
<!-- Use real power, measured or reported by appliances, or a more accurate estimate based on the consumption profile across time -->
<!-- Integrate proximity to desired temperature as a criteria for HVAC appliance priority decision -->

### Scheduling strategy

In this paper, a challenging scheduling problem arose from the context of energy management. Scheduling solutions are frequently designed for a "one-job-to-one-processor" pattern, where only one job can be executed at a time. The pattern assumes every job uses the same amount of resources at any point during their execution, corresponding to the exact capacity of the processor, so the only constraint is time.

Other jobs waiting for execution are organized in a queue. The arrival time of said jobs can be fixed or variable. If the arrival time is fixed, all jobs are known during the scheduling and can be sorted immediately, by execution time or external factors described by a discretized priority function. But with a variable rate of arrival, a job i that would be scheduled before job j in a fixed arrival setting may arrive later, and not be able to get processed immediately. Logically, the priority of job i is higher than of job j, thus it should complete before all jobs j in queue. It must be decided if the queue behavior is head-of-the-line, where the current job is not interrupted but job i is placed ahead of all lower-priority jobs, or preemptive, where the current job is interrupted to execute the higher-priority job j. Within the preemptive queue model, job i may need to be started from the beginning (preemptive restart) or keep its progress (preemptive resume). The queue behavior depends on the context of the problem and the constraints of the jobs.

Algorithms are developed to optimize a certain function, an objective measure of the scheduling performance. The most common goal is minimization of makespan - the total time required to execute all jobs. Once again, it is adequate for systems only constrained by processing time. Other criteria include lateness, earliness and tardiness, measurements that relate the deadline and completion time of each job. Throughput and fairness are useful metrics in scheduling systems with homogeneous jobs. 

However, in a house or building, multiple appliances can run simultaneously and independently, there being no restriction on the number of jobs. Executions are heterogeneous in running times and energy consumption, varying according to the energy profile and typical duration of usage of each application. Users can activate appliances at any time and stop them manually, earlier than predicted. [What else?]

[Reapproach paragraph above with scheduling-specific terms]

[Stochastic scheduling?]
[Utility Function]

### Interprocess communication
 - ZeroMQ (pyzmq)


> Users may decide to terminate the execution of an appliance before the time assumed by the script. 

> Keeping track of available energy resources, managing execution lifecycles and updating relative priorities.

### Useful links / papers

[1] H. Li, C. Zang, P. Zeng, H. Yu, Z. Li and N. Fenglian, "Optimal home energy management integrating random PV and appliances based on stochastic programming," 2016 Chinese Control and Decision Conference (CCDC), 2016, pp. 429-434, doi: 10.1109/CCDC.2016.7531023.