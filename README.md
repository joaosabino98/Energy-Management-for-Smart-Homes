# Energy Management for Smart Homes

## Common commands
### Go to project root folder
`cd C:\Users\jsabi\Documents\Tese\home`

### Create database schema
`python manage.py makemigrations`

### Apply schema
`python manage.py migrate`

### Create admin
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

---

## Shell tests
### Schedule execution
```
import processor.core as core
import processor.external_energy as ext
from coordinator.models import *
core.start()
home = Home.objects.get(pk=1)
e = Execution.objects.create(home=home, appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
core.schedule_execution(e)
e.delete()
```
### Test execution finish 
```
import processor.core as core
import processor.external_energy as ext
from coordinator.models import *
import time
core.start()
home = Home.objects.get(pk=1)
e = Execution.objects.create(home=home, appliance=Appliance.objects.get(pk=10),profile=Profile.objects.get(pk=30))
core.schedule_execution(e)
time.sleep(6)
e = Execution.objects.get(pk=e.id)
assert e.status() == "Finished"
e.delete()
```

---

## Complex scenarios
### Scenario 1: average consumption

User wakes up at 7:00 AM, takes a warm shower, prepares their breakfast with the coffee machine and the toaster.
Leaves to work with their electric car.
Comes home at 18:00 PM. Turns on the television, 

```
from coordinator.models import *
import time
home = Home.objects.get(pk=1)
midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)+timezone.timedelta(days=1)
e1 = Execution.objects.create(home=home, request_time=midnight+timezone.timedelta(hours=7),
appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=19))
e1 = Execution.objects.create(home=home, request_time=midnight+timezone.timedelta(hours=7),
    appliance=Appliance.objects.get(pk=1))


# Television
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=20))
# Microwave
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=1))
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=3))
# Oven
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=4))
# Heater (bedroom)
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=17))
# Water heater
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=19))
# Washing Machine
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=6),profile=Profile.objects.get(pk=10))
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=6),profile=Profile.objects.get(pk=11))
# Dishwasher
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=7),profile=Profile.objects.get(pk=7))
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=7),profile=Profile.objects.get(pk=8))
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=7),profile=Profile.objects.get(pk=9))
# Air Conditioner
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=8),profile=Profile.objects.get(pk=5))
# Fridge
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=9),profile=Profile.objects.get(pk=6))
# Coffee Machine
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=10),profile=Profile.objects.get(pk=13))
# Vacuum Cleaner
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=11),profile=Profile.objects.get(pk=12))
# Electric Vehicle
Execution.objects.create(home=home,appliance=Appliance.objects.get(pk=12),profile=Profile.objects.get(pk=21))
# Phone Charger

# Laptop Charger

# Hair Dryer


```

#### Single-house consumption with unlimited threshold - baseline


#### Single-house consumption


```
import processor.core as core
import processor.external_energy as ext
from coordinator.models import *
import time
core.start()
home = Home.objects.get(pk=1)

```

---

<!-- ## General To-do
- Implement multi-house mode recommendations in choose_execution_time
    * Three best times according to house strategy are sent to aggregator
    * Aggregator decides on best time according to global consumption (aggregated load balancing) -->

### Scheduling strategies
1. Peak-shaving: application scheduled to nearest available time
2. Load balancing: scheduled to period with less consumption

### Battery Storage System
1. Manage battery charging
    * if solar energy is enough to charge battery, charge exclusively during solar hours
    * if solar energy is available but not enough, charge using all solar energy + percentage of energy from grid
    * if no solar energy, charge whenever consumption < 37.5% during day (up to 50% of available energy)

2. Manage battery consumption
    * schedule whenever consumption > 62.5% (down to 50%)
    * schedule if an increased threshold is needed for some execution

3. Rules
    * Battery can't charge and discharge at the same time.
    * Battery can't be discharged below DOD

4. Implementation details
    * Battery charge is scheduled every midnight or when depleted
    * Battery charges can be interrupted as long as there's enough energy to accomodate all scheduled discharges
    * Last full recharge time is set when battery capacity is full, to facilitate future schedulings
    * Multiple battery discharges can run at the same time, as long as maximum power output is respected
    * Battery charge can be scheduled when energy is not fully depleted or discharges are scheduled: charges will be scheduled as long as maximum energy capacity isn't exceeded in future schedulings

---

## Technical Documentation

<!-- 
### Object classes

### SchedulerManager

The SchedulerManager receives requests from appliances that need to be executed or stopped, acting as a local server. It is primarily responsible for managing execution lifecycles. To do so, it needs to keep track of the available energy resources across the next hours, accounting for the energy to be consumed by running or pending (scheduled) executions until their expected end.

Each execution has a priority ranging from 1 to 10, where 10 is the highest priority and 1 is the lowest. This priority is calculated when the start request is processed, based on the priority class and maximum delay parameters defined by the user, and updated periodically.


#### Start request handling logic

When a start request arrives, the script checks if there is enough available power to run the appliance immediately. This option is preferred in situations of low energy demand, 

> Setting: don't start immediately if execution is not interruptible? or don't start immediately if power is above xx% of limit? -->

### Appliance categorization
An effective HEMS solution depends on accurate parametrization of appliance behaviour and time sensitiveness. Appliances can be primarily categorized regarding their ability to interrupt and resume their work. Some appliances can stop and resume with little to no loss of progress, such as recent models of washing machines or HVAC. These machines either keep track of their current progress, or perform a single task with continuous output, where an interruption at opportune times is considered acceptable by the user. Appliances within this category are classified as interruptible. On the other hand, appliances that are unable to resume their progress on restart, require a significant amount of energy to go back to the state before shutdown, or simply require continuous execution to achieve a goal, are considered non-interruptible. Examples are the oven, coffee machine, or even the television during an important segment.

[Priority categorization]


In previous iterations of the proposed solution, there was additional separation between schedulable and non-schedulable appliances, regarding their compatibility with a scheduling solution at all. For example, a fridge requires constant execution and regulates its own cooling efficiently. Users typically don't unplug a fridge, at the risk of spoiling food inside. However, a fridge can simply be classified as a non-interruptible appliance with maximum priority and unlimited duration of usage.

### Scheduling strategy

In this paper, a challenging scheduling problem arose from the context of energy management. Scheduling solutions are frequently designed for a "one-job-to-one-processor" pattern, where only one job can be executed at a time. The pattern assumes every job uses the same amount of resources at any point during their execution, corresponding to the exact capacity of the processor, so the only constraint is time.

Other jobs waiting for execution are organized in a queue. The arrival time of said jobs can be fixed or variable. If the arrival time is fixed, all jobs are known during the scheduling and can be sorted immediately, by execution time or external factors described by a discretized priority function. But with a variable rate of arrival, a job i that would be scheduled before job j in a fixed arrival setting may arrive later, and not be able to get processed immediately. Logically, the priority of job i is higher than of job j, thus it should complete before all jobs j in queue. It must be decided if the queue behavior is head-of-the-line, where the current job is not interrupted but job i is placed ahead of all lower-priority jobs, or preemptive, where the current job is interrupted to execute the higher-priority job j. Within the preemptive queue model, job i may need to be started from the beginning (preemptive restart) or keep its progress (preemptive resume). The queue behavior depends on the context of the problem and the constraints of the jobs.

Algorithms are developed to optimize a certain function, an objective measure of the scheduling performance. The most common goal is minimization of makespan - the total time required to execute all jobs. Once again, it is adequate for systems only constrained by processing time. Other criteria include lateness, earliness and tardiness, measurements that relate the deadline and completion time of each job. Throughput and fairness are useful metrics in scheduling systems with homogeneous jobs. 

However, in a house or building, multiple appliances can run simultaneously and independently, there being no restriction on the number of jobs. Executions are heterogeneous in running times and energy consumption, varying according to the energy profile and typical duration of usage of each application. Users can activate appliances at any time and stop them manually, earlier than predicted. [What else?]

[Reapproach paragraph above with scheduling-specific terms]

[Stochastic scheduling?]
[Utility Function]

#### Appliance lifecycle

#### Utility function
<!-- Use deterministic priorities to avoid appliances cycling between on and off? -->

### Solar energy representation
[PVWatts]
[hourly averages for each month, calculated for location coordinates based on European data]

### Multi-house mode
[Recommendations]

### Interprocess communication
 - ZeroMQ (pyzmq)

### Future work
<!-- Use real power, measured or reported by appliances, or a more accurate estimate based on the consumption profile across time -->
<!-- Integrate proximity to desired temperature as a criteria for HVAC appliance priority decision -->

---

### Useful links / papers

[1] H. Li, C. Zang, P. Zeng, H. Yu, Z. Li and N. Fenglian, "Optimal home energy management integrating random PV and appliances based on stochastic programming," 2016 Chinese Control and Decision Conference (CCDC), 2016, pp. 429-434, doi: 10.1109/CCDC.2016.7531023.