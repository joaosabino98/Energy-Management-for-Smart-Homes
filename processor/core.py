import os
import django
from math import floor
from django.utils import timezone
from apscheduler.triggers.cron import CronTrigger
import processor.apsched as aps
import processor.external_energy as ext

from scheduler.settings import IMMEDIATE, INF_DATE, INTERRUPTIBLE, LOAD_DISTRIBUTION, LOW_PRIORITY, NORMAL, PEAK_SHAVING, TIME_BAND
from scheduler.models import AppVals, BatteryStorageSystem, Execution

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

def start_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if execution.is_started is False:
		execution.set_started()
	print("Execution of " + execution.appliance.name + " started at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))

def finish_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if execution.is_finished is False and execution.is_interrupted is False:
		execution.set_finished()
	if BatteryStorageSystem.compare_appliance(execution.appliance):
		battery = BatteryStorageSystem.get_system()
		energy_stored = ext.get_battery_energy(execution.end_time)
		if energy_stored >= battery.total_energy_capacity * 0.99:
			battery.last_full_charge_time = execution.end_time
			battery.save()
		elif energy_stored <= battery.total_energy_capacity * 0.01 and id == ext.get_last_battery_execution().id:
			ext.schedule_battery_charge()
	print("Execution of " + execution.appliance.name + " finished by the system at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))

def anticipate_high_priority_executions_job():
	anticipate_high_priority_executions()

def schedule_battery_charge_job():
	ext.schedule_battery_charge()

def change_threshold(threshold):
	AppVals.set_consumption_threshold(threshold)
	anticipate_pending_executions()

def get_unfinished_executions():
	date_limit = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=2)
	return Execution.objects.filter(request_time__gt=date_limit).exclude(end_time__lt=timezone.now()).order_by('end_time')

def get_pending_executions():
	unfinished = get_unfinished_executions()
	return unfinished.filter(start_time__gt=timezone.now())

def get_running_executions():
	unfinished = get_unfinished_executions()
	return unfinished.filter(start_time__lte=timezone.now())

def get_running_executions_within(start_time, end_time):
	unfinished = get_unfinished_executions()
	if end_time is None:
		return unfinished.filter(end_time__gt=start_time)
	return unfinished.filter(start_time__lte=end_time).filter(end_time__gt=start_time)

def get_lower_priority_shiftable_executions_within(start_time, end_time, target_power, target_priority):
	shiftable_executions = []
	for execution in get_running_executions_within(start_time, end_time):
		priority = calculate_weighted_priority(execution)
		if priority < target_priority and execution.profile.schedulability is INTERRUPTIBLE:
			if BatteryStorageSystem.compare_appliance(execution.appliance) and execution.profile.rated_power > 0:
				if ext.is_battery_execution_interruptable(execution):
					shiftable_executions.append(execution)
			else:
				shiftable_executions.append(execution)
	# sorted_keys = sorted(shiftable_executions, key=lambda e: get_maximum_consumption_within(e.start_time, e.end_time), reverse=True)
	sorted_keys = sorted(shiftable_executions,
		key=lambda e: (calculate_weighted_priority(e), get_positive_power_difference(e.profile.rated_power, target_power)))
	return sorted_keys

def get_power_consumption(time, queryset=None):
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
	reference_times = get_consumption_reference_times_within(start_time, end_time, queryset)
	for time in reference_times:
		power_consumption = get_power_consumption(time, queryset)
		if power_consumption > peak_consumption:
			peak_consumption = power_consumption
	return peak_consumption

def get_positive_power_difference(rated_power, target_power):
	return rated_power - target_power if rated_power < target_power else float("inf")

def calculate_execution_end_time(execution, start_time, duration=None):
	if execution.appliance.maximum_duration_of_usage is None and duration is None:
		end_time = INF_DATE
	elif duration is not None:
		remaining_execution_time = duration - execution.previous_progress_time
		end_time = start_time + remaining_execution_time
	else:
		remaining_execution_time = execution.appliance.maximum_duration_of_usage - execution.previous_progress_time
		end_time = start_time + remaining_execution_time
	return end_time

def choose_execution_time(execution, available_periods, strategy=AppVals.get_strategy()):
	maximum_delay = execution.profile.maximum_delay
	if maximum_delay is not None:
		available_periods = dict(filter(lambda e: e[0][0] - execution.request_time < maximum_delay, available_periods.items()))
	if available_periods:
		if strategy is PEAK_SHAVING:
			earliest_start_time = next(iter(available_periods))[0]
			return earliest_start_time
		elif strategy is LOAD_DISTRIBUTION:
			sorted_periods = {k: v for k, v in sorted(available_periods.items(), key=lambda item: item[1])}
			for period in sorted_periods:
				if period[0] - execution.request_time < maximum_delay:
					return period[0]
		else:
			pass

def get_available_execution_times(execution, minimum_start_time=timezone.now(), duration=None):
	available_periods = {}
	reference_times = get_consumption_reference_times_within(minimum_start_time, None)
	for proposed_start_time in reference_times:
		proposed_end_time = calculate_execution_end_time(execution, proposed_start_time, duration)
		power_consumption = get_maximum_consumption_within(proposed_start_time, proposed_end_time)
		power_available = ext.get_power_available_within(proposed_start_time, proposed_end_time) - power_consumption
		if power_available >= execution.profile.rated_power:
			available_periods[(proposed_start_time, proposed_end_time)] = power_available
	
	return available_periods

#TODO: attempt to shedule execution in parts instead of whole
def get_available_fractioned_execution_time(execution, minimum_start_time=timezone.now()):
	pass

# Slight hack: returned list includes hourly references for at most two days
# This means PV production times are included and periods can be found after timespan of running executions
def get_consumption_reference_times_within(start_time, end_time, queryset=None):
	time_list = [start_time]
	if end_time is not None and end_time != INF_DATE:
		time_list.append(end_time)
	if start_time != INF_DATE:
		hour_break = start_time.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
		date_limit = start_time.replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=2)
		while hour_break < date_limit:
			if end_time is not None and hour_break < end_time:
				time_list.append(hour_break)
				hour_break += timezone.timedelta(hours=1)
			else:
				break
	if queryset is None:
		queryset = get_running_executions_within(start_time, end_time)
	for execution in queryset:
		if execution.start_time >= start_time:
			time_list.append(execution.start_time)
		if execution.end_time is not None and (end_time is None or execution.end_time < end_time):
				time_list.append(execution.end_time)
	time_list.sort()
	return time_list

def start_execution(execution, start_time=None, debug=False):
	if debug:
		execution.start() if start_time is None else execution.set_start_time(start_time)
	else:
		if start_time is None:
			start_time = timezone.now()
		if execution.start_time is None:
			execution.set_start_time(start_time)
		bgsched.add_job(start_execution_job, 'date', [execution.id],
			run_date=execution.start_time,
			id=str(execution.id) + "_start",
			max_instances=1,
			replace_existing=True)
		if execution.end_time is not None:
			bgsched.add_job(finish_execution_job, 'date', [execution.id],
				id=str(execution.id) + "_finish",
				run_date=execution.end_time,
				max_instances=1,
				replace_existing=True)
	print("Execution of " + execution.appliance.name + " starting at " + execution.start_time.strftime("%d/%m/%Y, %H:%M:%S."))

def interrupt_execution(execution):
	execution.interrupt()
	if bgsched.get_job(f"{execution.id}_finish") is not None:
		bgsched.remove_job(f"{execution.id}_finish")
	print("Execution of " + execution.appliance.name + " interrupted at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))

def finish_execution(execution, debug=False):
	execution.finish()
	if bgsched.get_job(f"{execution.id}_finish") is not None:
		bgsched.remove_job(f"{execution.id}_finish")
	print("Execution of " + execution.appliance.name + " finished by the user at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))
	anticipate_pending_executions(debug)

def schedule_execution(execution, debug=False):
	now = timezone.now()
	strategy = AppVals.get_strategy()
	available_periods = get_available_execution_times(execution, now)
	chosen_time = choose_execution_time(execution, available_periods, strategy)

	if strategy is PEAK_SHAVING:
		if chosen_time == now:
			print("Enough available power.")
			start_execution(execution, None, debug)
			check_high_demand(now, calculate_execution_end_time(execution, now), now, debug)
			return 1
		elif ext.is_battery_discharge_available(execution, now):
			print("Activating battery storage system.")
			ext.schedule_battery_discharge_on_consumption_above_threshold(execution, now, now, debug)
			start_execution(execution, None, debug)
			return 1
		else:
			print("Unable to activate immediately. Attempting to shift lower priority running executions...")
			success = shift_executions(execution, now, debug)
			if success:
				ext.schedule_battery_discharge_on_high_demand(now, debug)
				return 2
			else:
				print("Unable to shift running executions.")
				if chosen_time is not None and chosen_time != INF_DATE:
					start_execution(execution, chosen_time, debug)
					check_high_demand(chosen_time, calculate_execution_end_time(execution, chosen_time), now, debug)
					return 3
				else:
					print("Unable to schedule execution within acceptable delay. Consider raising threshold or stopping appliances.")
					ext.schedule_battery_discharge_on_high_demand(now, debug)
					return 4

def schedule_later(execution, debug=False):
	now = timezone.now()
	available_periods = get_available_execution_times(execution, now)
	chosen_time = choose_execution_time(execution, available_periods)
	start_execution(execution, chosen_time, debug)

def shift_executions(execution, start_time, debug=False):
	priority = calculate_weighted_priority(execution)
	rated_power = execution.profile.rated_power
	end_time = calculate_execution_end_time(execution, start_time)
	success, interrupted = interrupt_shiftable_executions(start_time, end_time, rated_power, priority)
	if success:
		print("Lower priority running executions found.")
		start_execution(execution, None, debug)
		for execution in interrupted:
			#TODO: if it's battery, schedule with lower wattage
			if not BatteryStorageSystem.compare_appliance(execution.appliance):
				new = Execution.objects.create(
					appliance=execution.appliance,
					profile=execution.profile,
					previous_progress_time=execution.end_time-execution.start_time+execution.previous_progress_time,
					previous_waiting_time=execution.start_time-execution.request_time+execution.previous_waiting_time)
				schedule_later(new, debug)
		return success

def interrupt_shiftable_executions(start_time, end_time, rated_power, priority):
	running_executions = get_running_executions_within(start_time, end_time)
	shiftable_executions = get_lower_priority_shiftable_executions_within(start_time, end_time, rated_power, priority)
	minimum_power_available = AppVals.get_consumption_threshold() - get_maximum_consumption_within(start_time, end_time, running_executions)
	maximum_shiftable_power = get_maximum_consumption_within(start_time, end_time, shiftable_executions)

	if minimum_power_available + maximum_shiftable_power < rated_power:
		return False, []
	interrupted = []
	for execution in shiftable_executions:
		interrupt_execution(execution)
		running_executions = get_running_executions_within(start_time, end_time).exclude(id=execution.id)
		minimum_power_available = AppVals.get_consumption_threshold() - get_maximum_consumption_within(start_time, end_time, running_executions)
		interrupted.append(execution)
		if minimum_power_available >= rated_power:
			break

	return True, interrupted

def check_high_demand(start_time, end_time, current_time, debug=False):
	if BatteryStorageSystem.get_system() is not None and \
		get_maximum_consumption_within(start_time, end_time) > ext.get_power_available_within(start_time, end_time) * 0.7:
		print("Attempting to schedule battery discharge on high demand.")
		ext.schedule_battery_discharge_on_high_demand(current_time, debug)

def calculate_weighted_priority(execution):
	maximum_delay = execution.profile.maximum_delay
	start_time = execution.start_time if execution.start_time is not None else timezone.now()
	waiting_time = start_time - execution.request_time + execution.previous_waiting_time

	if execution.profile.priority is IMMEDIATE:
		base_priority = 7
	elif execution.profile.priority is NORMAL: 
		base_priority = 3
	elif execution.profile.priority is LOW_PRIORITY:
		base_priority = 1

	if maximum_delay is not None:
		multiplier = 8 # steepness of curve: 6, 8, 10 are viable
		time_until_deadline = maximum_delay - waiting_time
		minutes_until_deadline = time_until_deadline.seconds/60 if maximum_delay > waiting_time else 0
		priority = base_priority + floor(60*multiplier/(minutes_until_deadline+60))
	else:
		priority = base_priority
	return priority if priority < 10 else 10

def anticipate_pending_executions(debug=False):
	pending_executions = sorted(list(get_pending_executions()), key=lambda e: calculate_weighted_priority(e), reverse=True)
	for execution in pending_executions:
		print(f"Attempting to anticipate execution {execution.id}.")
		now = timezone.now()
		available_periods = get_available_execution_times(execution, now)
		chosen_time = choose_execution_time(execution, available_periods)
		if chosen_time == now:
			start_execution(execution, None, debug)
		elif chosen_time < execution.start_time:
			start_execution(execution, chosen_time, debug)
		else:
			print("Unable to anticipate execution.")

def anticipate_high_priority_executions(debug=False):
	pending_executions = sorted(list(get_pending_executions()), key=lambda e: calculate_weighted_priority(e), reverse=True)
	for execution in pending_executions:
		if calculate_weighted_priority(execution) > 7:
			now = timezone.now()
			success = shift_executions(execution, now, debug)
			if not success:
				print("Unable to anticipate execution.")

def start():
	aps.start()
	bgsched.add_job(
		anticipate_high_priority_executions_job,
		trigger=CronTrigger(minute=f"*/{step}"),
		id="anticipate_high_priority_executions",
		replace_existing=True)
	if BatteryStorageSystem.get_system() is not None:
		bgsched.add_job(
			schedule_battery_charge_job,
			trigger=CronTrigger(hour=0),
			id="schedule_battery_charge",
			replace_existing=True
		)
	AppVals.set_running(True)
	print("Start process complete.")

step = 15
bgsched = aps.scheduler