import os
import django
import re
import threading
from math import floor, log10
from django.utils import timezone
from apscheduler.triggers.cron import CronTrigger
import processor.apsched as aps

from scheduler.settings import IMMEDIATE, INTERRUPTIBLE, LOW_PRIORITY, NONSCHEDULABLE, NORMAL
from scheduler.models import AppVals, Appliance, Execution

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

def start_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if (execution.is_started is False):
		execution.set_started()
	print("Execution of " + execution.appliance.name + " started at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

def finish_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if (execution.is_finished is False and execution.is_interrupted is False):
		execution.set_finished()
	print("Execution of " + execution.appliance.name + " finished by the system at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

def update_queue_priorities_job():
	# ScheduleManager().anticipate_pending_executions()
	pass

def change_threshold(threshold):
	AppVals.set_consumption_threshold(threshold)
	# anticipate_pending_executions()

def get_unfinished_executions():
	date_limit = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=2)
	return Execution.objects.filter(request_time__gt=date_limit).exclude(end_time__lt=timezone.now()).order_by('end_time')

def get_running_executions():
	unfinished = get_unfinished_executions()
	return unfinished.filter(start_time__lte=timezone.now())

def get_running_executions_within(start_time, end_time):
	unfinished = get_unfinished_executions()
	return unfinished.filter(start_time__lte=end_time).filter(end_time__gte=start_time)

def get_lower_priority_shiftable_executions_within(start_time, end_time, target_power, target_priority):
	shiftable_executions = []
	for execution in get_running_executions_within(start_time, end_time):
		priority = calculate_weighted_priority(execution)
		if (priority < target_priority and execution.profile.schedulability is INTERRUPTIBLE):
			shiftable_executions.append(execution)
	# sorted_keys = sorted(shiftable_executions, key=lambda e: get_maximum_consumption_within(e.start_time, e.end_time), reverse=True)
	sorted_keys = sorted(shiftable_executions,
		key=lambda e: (calculate_weighted_priority(e), get_positive_energy_difference(e.profile.rated_power, target_power)))
	return sorted_keys

def get_pending_executions():
	unfinished = get_unfinished_executions()
	return unfinished.filter(start_time__gt=timezone.now())

def get_energy_consumption(time, queryset=None):
	rated_power = 0
	if queryset is None:
		queryset = get_running_executions_within(time, time)
	for execution in queryset:
		rated_power += execution.profile.rated_power
	return rated_power

def get_maximum_consumption_within(start_time, end_time, queryset=None):
	peak_consumption = 0
	if queryset is None:
		queryset = get_running_executions_within(start_time, end_time)
	reference_times = get_reference_times_within(start_time, end_time, queryset)
	for time in reference_times:
		energy_consumption = get_energy_consumption(time, queryset)
		if (energy_consumption > peak_consumption):
			peak_consumption = energy_consumption
	return peak_consumption

def get_positive_energy_difference(rated_power, target_power):
	return rated_power - target_power if rated_power < target_power else float("inf")

#Current algorithm: try to schedule whole execution
#Alternative: find all available slots and schedule fractioned execution
def get_available_execution_time(execution, minimum_start_time=timezone.now()):
	unfinished = get_unfinished_executions()
	remaining_execution_time = execution.appliance.maximum_duration_of_usage - execution.previous_progress_time
	proposed_start_time = minimum_start_time
	for ending_execution in unfinished:
		running = get_running_executions_within(proposed_start_time, proposed_start_time + remaining_execution_time)
		power_consumption = 0
		for running_execution in running:
			power_consumption += running_execution.profile.rated_power
		if (AppVals.get_consumption_threshold() - power_consumption >= execution.profile.rated_power):
			break
		elif ending_execution.end_time is not None:
			proposed_start_time = ending_execution.end_time

	return proposed_start_time

def get_available_fractioned_execution_time(execution, minimum_start_time=timezone.now()):
	pass

def get_reference_times_within(start_time, end_time, queryset=None):
	time_list = [start_time, end_time]
	if queryset is None:
		queryset = get_running_executions_within(start_time, end_time)
	for execution in queryset:
		if execution.start_time >= start_time:
			time_list.append(execution.start_time)
		if execution.end_time <= end_time:
			time_list.append(execution.end_time)
	time_list.sort()
	return time_list

def start_execution(execution, start_time=None):
	if (start_time is None):
		execution.start()
		print("Execution of " + execution.appliance.name + " started at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))
	else:
		execution.set_start_time(start_time)
		bgsched.add_job(start_execution_job, 'date', [execution.id],
			run_date=execution.start_time,
			id=str(execution.id) + "_start",
			max_instances=1,
			replace_existing=True)
		print("Execution of " + execution.appliance.name + " starting at " + start_time.strftime("%m/%d/%Y, %H:%M:%S."))
	bgsched.add_job(finish_execution_job, 'date', [execution.id],
		id=str(execution.id) + "_finish",
		run_date=execution.end_time,
		max_instances=1,
		replace_existing=True)

def interrupt_execution(execution):
	execution.interrupt()
	if (bgsched.get_job(f"{execution.id}_finish") is not None):
		bgsched.remove_job(f"{execution.id}_finish")
	print("Execution of " + execution.appliance.name + " interrupted at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

def finish_execution(execution):
	execution.finish()
	if (bgsched.get_job(f"{execution.id}_finish") is not None):
		bgsched.remove_job(f"{execution.id}_finish")
	print("Execution of " + execution.appliance.name + " finished by the user at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

def schedule_execution(execution):
	rated_power = execution.profile.rated_power
	now = timezone.now()
	available_time = get_available_execution_time(execution, now)

	if (available_time == now):
		print("Enough available power.")
		start_execution(execution)
		return 1
	else:
		print("Unable to activate immediately. Attempting to shift lower priority running executions...")
		priority = calculate_weighted_priority(execution)
		remaining_execution_time = execution.appliance.maximum_duration_of_usage - execution.previous_progress_time
		result, interrupted = shift_executions(now, now + remaining_execution_time, rated_power, priority)
		if (result == True):
			print("Lower priority running executions found.")
			start_execution(execution)
			for execution in interrupted:
				new = Execution.objects.create(
					appliance=execution.appliance,
					profile=execution.profile,
					previous_progress_time=execution.end_time-execution.start_time+execution.previous_progress_time,
					previous_waiting_time=execution.start_time-execution.request_time+execution.previous_waiting_time)
				schedule_later(new)
			return 2
		else:
			print("Unable to shift running executions.")
			schedule_later(execution)
			return 3

def schedule_later(execution):
	now = timezone.now()
	available_time = get_available_execution_time(execution, now)
	start_execution(execution, available_time)

def shift_executions(start_time, end_time, rated_power, priority):
	running_executions = get_running_executions_within(start_time, end_time)
	shiftable_executions = get_lower_priority_shiftable_executions_within(start_time, end_time, rated_power, priority)
	minimum_power_available = AppVals.get_consumption_threshold() - get_maximum_consumption_within(start_time, end_time, running_executions)
	maximum_shiftable_power = get_maximum_consumption_within(start_time, end_time, shiftable_executions)

	if (minimum_power_available + maximum_shiftable_power < rated_power):
		return False, []

	interrupted = []
	for execution in shiftable_executions:
		interrupt_execution(execution)
		running_executions = get_running_executions_within(start_time, end_time)
		minimum_power_available = AppVals.get_consumption_threshold() - get_maximum_consumption_within(start_time, end_time, running_executions)
		interrupted.append(execution)
		if (minimum_power_available >= rated_power):
			break
	
	return True, interrupted

def calculate_weighted_priority(execution):
	maximum_delay = execution.profile.maximum_delay
	start_time = execution.start_time if execution.start_time is not None else timezone.now()
	waiting_time = start_time - execution.request_time + execution.previous_waiting_time
	time_until_deadline = maximum_delay - waiting_time
	minutes_until_deadline = time_until_deadline.seconds/60 if maximum_delay > waiting_time else 0

	if (execution.profile.priority is IMMEDIATE):
		base_priority = 7
	elif (execution.profile.priority is NORMAL): 
		base_priority = 3
	elif (execution.profile.priority is LOW_PRIORITY):
		base_priority = 1

	multiplier = 8 # steepness of curve: 6, 8, 10 are viable
	priority = base_priority + floor(60*multiplier/(minutes_until_deadline+60))

	return priority if priority <= 10 else 10

step = 5
bgsched = aps.scheduler
aps.start()
# bgsched.add_job(
# 	update_queue_priorities_job,
# 	trigger=CronTrigger(minute=f"*/{step}"),
# 	id="update_queue_priorities",
# 	replace_existing=True)
AppVals.set_running(True)

# 	"""
# 	def anticipate_pending_executions(self) -> None

# 	Sort pending executions by decreasing priority and attempt to reschedule them,
# 	or shift lower priority executions. Also accomodates increases in the threshold.
# 	TODO: optimize: skip if no executions were added/threshold wasn't changed?
# 	"""
# 	def anticipate_pending_executions(self):
# 		temp = {k: v for k, v in sorted(self.pending.items(), key=lambda item: item[1], reverse=True)}
# 		for execution, priority in temp.items():
# 			print(f"Attempting to anticipate execution {execution.id}.")
# 			now = self.get_current_schedule_slot()
# 			start_time = self.get_available_timeslot(now, execution)
# 			if (start_time is not None and start_time < execution.start_time):
# 				self.remove_executions_from_timetable([execution])
# 				self.schedule_later(execution)
# 			else:
# 				print("Unable to reschedule earlier. Attempting to shift running executions with lower priority.")
# 				rated_power = execution.profile.rated_power
# 				result, interrupted = self.shift_executions(rated_power, priority)
# 				if (result == True):
# 					print("Lower priority running executions found.")
# 					self.remove_executions_from_timetable([execution])
# 					self.start_execution(execution)
					
# 					for execution in interrupted:
# 						new = Execution.objects.create(
# 							appliance=execution.appliance,
# 							profile=execution.profile,
# 							previous_progress_time=execution.end_time-execution.start_time+execution.previous_progress_time)
# 						self.schedule_later(new)
# 				else:
# 					print("Unable to anticipate execution.")

# 	"""