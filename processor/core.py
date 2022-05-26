import os
import django
from math import floor
from django.utils import timezone
from apscheduler.triggers.cron import CronTrigger
import processor.tools as tools
import processor.background as aps
import processor.external_energy as ext
import processor.aggregator.client as cli

from home.settings import INF_DATE
from coordinator.settings import INTERRUPTIBLE, LOW_PRIORITY, NORMAL, URGENT
from coordinator.models import Home, Execution

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coordinator.settings")
# django.setup()

def start_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if execution.is_started is False:
		execution.set_started()
	print("Execution of " + execution.appliance.name + " started at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))

def finish_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if execution.is_finished is False and execution.is_interrupted is False:
		execution.set_finished()
	home = execution.home
	if home.compare_BSS_appliance(execution.appliance):
		battery = home.batterystoragesystem
		energy_stored = ext.get_battery_energy(home, execution.end_time)
		if energy_stored >= battery.total_energy_capacity * 0.99:
			battery.set_last_full_charge_time(execution.end_time)
		elif energy_stored < battery.total_energy_capacity * (1.1 - battery.depth_of_discharge) and \
			id == ext.get_last_battery_execution(home).id:
			ext.schedule_battery_charge(home)
	print("Execution of " + execution.appliance.name + " finished by the system at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))

def schedule_battery_charge_job(id):
	home = Home.objects.get(pk=id)
	ext.schedule_battery_charge(home)

def send_consumption_schedule_job(id):
	home = Home.objects.get(pk=id)
	send_consumption_schedule(home)

def get_unfinished_executions(home):
	date_limit = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=2)
	return Execution.objects.filter(home=home, request_time__gt=date_limit).exclude(end_time__lt=timezone.now()).order_by('end_time')

def get_pending_executions(home):
	unfinished = get_unfinished_executions(home)
	return unfinished.filter(start_time__gt=timezone.now())

def get_running_executions(home):
	unfinished = get_unfinished_executions(home)
	return unfinished.filter(start_time__lte=timezone.now())

def get_running_executions_within(home, start_time, end_time):
	unfinished = get_unfinished_executions(home)
	if end_time is None:
		return unfinished.filter(end_time__gt=start_time)
	return unfinished.filter(start_time__lte=end_time).filter(end_time__gt=start_time)

def get_lower_priority_shiftable_executions_within(home, start_time, end_time, target_priority):
	shiftable_executions = []
	for execution in get_running_executions_within(home, start_time, end_time):
		priority = calculate_weighted_priority(execution, start_time)
		if priority < target_priority and execution.profile.schedulability is INTERRUPTIBLE:
			if home.compare_BSS_appliance(execution.appliance) and execution.profile.rated_power > 0:
				if ext.is_battery_charge_interruptible(execution):
					shiftable_executions.append(execution)
			else:
				shiftable_executions.append(execution)
	# sorted_keys = sorted(shiftable_executions, key=lambda e: get_maximum_consumption_within(e.start_time, e.end_time), reverse=True)
	# 	sorted_keys = sorted(shiftable_executions,
	#	key=lambda e: (calculate_weighted_priority(e, start_time), tools.positive_power_difference(e.profile.rated_power, target_power)))
	sorted_keys = sorted(shiftable_executions, key=lambda e: (calculate_weighted_priority(e, start_time)))
	return sorted_keys

def get_power_consumption(home, time, queryset=None):
	rated_power = 0
	if queryset is None:
		queryset = get_running_executions_within(home, time, time)
	for execution in queryset:
		rated_power += execution.profile.rated_power
	return rated_power

def get_maximum_consumption_within(home, start_time, end_time, queryset=None):
	peak_consumption = 0
	if queryset is None:
		queryset = get_running_executions_within(home, start_time, end_time)
	reference_times = get_consumption_reference_times_within(home, start_time, end_time, queryset)
	for time in reference_times:
		power_consumption = get_power_consumption(home, time, queryset)
		if power_consumption > peak_consumption:
			peak_consumption = power_consumption
	return peak_consumption

def calculate_execution_end_time(execution, start_time, duration=None):
	if execution.profile.maximum_duration_of_usage is None and duration is None:
		end_time = INF_DATE
	elif duration is not None:
		remaining_execution_time = duration - execution.previous_progress_time
		end_time = start_time + remaining_execution_time
	else:
		remaining_execution_time = execution.profile.maximum_duration_of_usage - execution.previous_progress_time
		end_time = start_time + remaining_execution_time
	return end_time

def choose_execution_time(execution, available_periods):
	chosen_time = None
	maximum_delay = execution.appliance.maximum_delay
	home = execution.home
	if maximum_delay is not None:
		available_periods = dict(filter(lambda e: e[0][0] - execution.request_time < maximum_delay, available_periods.items()))
	if available_periods:
		priority = execution.profile.priority
		if priority is LOW_PRIORITY and home.accept_recommendations:
			chosen_index = int(cli.send_choice_request(available_periods))
			start_time = list(available_periods.keys())[chosen_index][0]
		elif priority is LOW_PRIORITY:
			sorted_periods = {k: v for k, v in sorted(available_periods.items(), key=lambda item: item[1], reverse=True)}
			start_time = next(iter(sorted_periods))[0]
		else:
			start_time = next(iter(available_periods))[0]
		if start_time != INF_DATE:
			chosen_time = start_time
	return chosen_time

def get_available_execution_times(execution, minimum_start_time=None, include_bss=False, include_shiftable=False):
	if minimum_start_time is None:
		minimum_start_time = timezone.now()
	home = execution.home
	available_periods = {}
	reference_times = get_consumption_reference_times_within(home, minimum_start_time, None)
	for proposed_start_time in reference_times:
		proposed_end_time = calculate_execution_end_time(execution, proposed_start_time)
		power_consumption = get_maximum_consumption_within(home, proposed_start_time, proposed_end_time)
		power_available = ext.get_power_threshold_within(home, proposed_start_time, proposed_end_time) - power_consumption
		if include_bss:
			power_available += ext.get_battery_discharge_available(home, proposed_start_time, proposed_end_time)
		if include_shiftable:
			priority = calculate_weighted_priority(execution, proposed_start_time)
			power_available += get_shiftable_executions_power(home, proposed_start_time, proposed_end_time, priority)
		if power_available >= execution.profile.rated_power:
			available_periods[(proposed_start_time, proposed_end_time)] = power_available
	return available_periods

# Slight hack: returned list includes hourly references for at most two days
# This means PV production times are included and periods can be found after timespan of running executions
def get_consumption_reference_times_within(home, start_time, end_time, queryset=None):
	time_list = [start_time]
	if end_time is not None and end_time != INF_DATE:
		time_list.append(end_time)
	if start_time != INF_DATE:
		hour_break = start_time.replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=1)
		date_limit = start_time.replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=2)
		while end_time is not None and hour_break < end_time and hour_break < date_limit:
			time_list.append(hour_break)
			hour_break += timezone.timedelta(hours=1)
	if queryset is None:
		queryset = get_running_executions_within(home, start_time, end_time)
	for execution in queryset:
		if execution.start_time >= start_time:
			time_list.append(execution.start_time)
		if execution.end_time is not None and (end_time is None or execution.end_time < end_time):
				time_list.append(execution.end_time)
	time_list = sorted(list(dict.fromkeys(time_list)))
	return time_list

def start_execution(execution, start_time, debug=False):
	if debug:
		execution.start() if tools.is_now(start_time) else execution.set_start_time(start_time)
	else:
		if execution.start_time is None:
			execution.set_start_time(start_time)
		background.add_job(start_execution_job, 'date', [execution.id],
			run_date=execution.start_time,
			id=f"home_{execution.home.id}_execution_{execution.id}_start",
			max_instances=1,
			replace_existing=True)
		if execution.end_time is not None:
			background.add_job(finish_execution_job, 'date', [execution.id],
				id=f"home_{execution.home.id}_execution_{execution.id}_finish",
				run_date=execution.end_time,
				max_instances=1,
				replace_existing=True)
	print("Execution of " + execution.appliance.name + " starting at " + execution.start_time.strftime("%d/%m/%Y, %H:%M:%S."))

def interrupt_execution(execution):
	execution.interrupt()
	if background.get_job(f"home_{execution.home.id}_execution_{execution.id}_finish") is not None:
		background.remove_job(f"home_{execution.home.id}_execution_{execution.id}_finish")
	print("Execution of " + execution.appliance.name + " interrupted at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))

def finish_execution(execution, debug=False):
	execution.finish()
	if background.get_job(f"home_{execution.home.id}_execution_{execution.id}_finish") is not None:
		background.remove_job(f"home_{execution.home.id}_execution_{execution.id}_finish")
	print("Execution of " + execution.appliance.name + " finished by the user at " + timezone.now().strftime("%d/%m/%Y, %H:%M:%S."))
	home = execution.home
	now = timezone.now()
	anticipate_pending_executions(home, now, debug)

def propose_schedule_execution(execution, request_time):
	priority = execution.profile.priority
	start_times = [None, None, None]

	# for low priority device, any time is fine
	# for normal or immediate device, attempt to schedule immediately
	for i in range(0, len(start_times)):
		match i:
			case 0:
				available_periods = get_available_execution_times(execution, request_time, False, False)
			case 1:
				available_periods = get_available_execution_times(execution, request_time, True, False)
			case 2:
				available_periods = get_available_execution_times(execution, request_time, True, True)
		start_times[i] = choose_execution_time(execution, available_periods)
	
	if priority is LOW_PRIORITY:
		chosen_time = next((time for time in start_times if time is not None), None)
	else: 
		chosen_time = min((time for time in start_times if time is not None), default=None)

	chosen_strategy = start_times.index(chosen_time) if chosen_time is not None else -1
	return chosen_strategy, chosen_time

def schedule_execution(execution, request_time=None, debug=False):
	if request_time is None:
		request_time = timezone.now()
	home = execution.home
	chosen_strategy, chosen_time = propose_schedule_execution(execution, request_time)
	match chosen_strategy:
		case 0:
			print(f'[1] Enough available power found.')
			start_execution(execution, chosen_time, debug)
		case 1:
			print(f'[2] Activating Battery Storage System.')
			ext.schedule_battery_discharge_on_consumption_above_threshold(home, chosen_time,
				calculate_execution_end_time(execution, chosen_time), debug)
			start_execution(execution, request_time, debug)
		case 2:
			print(f'[3] Shifting lower priority executions.')
			if hasattr(home, "batterystoragesystem"):
				ext.schedule_battery_discharge_on_consumption_above_threshold(home, chosen_time,
					calculate_execution_end_time(execution, chosen_time), debug)
			shift_executions(execution, chosen_time, request_time, debug)
		case _:
			print(f'[{chosen_strategy}] Unable to schedule appliance. Consider raising power threshold or increasing maximum delay.')
	if chosen_time is not None:
		check_high_consumption(home, chosen_time, calculate_execution_end_time(execution, chosen_time), request_time, debug)
	send_consumption_schedule(home)
	return chosen_strategy
		
def shift_executions(execution, start_time, request_time=None, debug=False):
	if request_time is None:
		request_time = timezone.now()
	home = execution.home
	priority = calculate_weighted_priority(execution, request_time)
	rated_power = execution.profile.rated_power
	end_time = calculate_execution_end_time(execution, start_time)
	interrupted = interrupt_shiftable_executions(home, start_time, end_time, rated_power, priority)

	start_execution(execution, start_time, debug)
	for execution in interrupted:
		#TODO: if it's battery, schedule with lower wattage
		if not home.compare_BSS_appliance(execution.appliance):
			new = Execution.objects.create(
				home=home,
				appliance=execution.appliance,
				profile=execution.profile,
				previous_progress_time=execution.end_time-execution.start_time+execution.previous_progress_time,
				previous_waiting_time=execution.start_time-execution.request_time+execution.previous_waiting_time)
			schedule_execution(new, request_time, debug)

def interrupt_shiftable_executions(home, start_time, end_time, rated_power, priority):
	shiftable_executions = get_lower_priority_shiftable_executions_within(home, start_time, end_time, priority)
	interrupted = []
	for execution in shiftable_executions:
		interrupt_execution(execution)
		running_executions = get_running_executions_within(home, start_time, end_time).exclude(id=execution.id)
		minimum_power_available = ext.get_power_threshold_within(home, start_time, end_time) - \
			get_maximum_consumption_within(home, start_time, end_time, running_executions)
		interrupted.append(execution)
		if minimum_power_available >= rated_power:
			break

	return interrupted

def get_shiftable_executions_power(home, start_time, end_time, priority):
	shiftable_executions = get_lower_priority_shiftable_executions_within(home, start_time, end_time, priority)
	maximum_shiftable_power = get_maximum_consumption_within(home, start_time, end_time, shiftable_executions)
	return maximum_shiftable_power

def check_high_consumption(home, start_time, end_time, current_time, debug=False):
	if hasattr(home, "batterystoragesystem") and \
		get_maximum_consumption_within(home, start_time, end_time) > ext.get_power_threshold_within(home, start_time, end_time) * 0.7:
		print("Attempting to schedule battery discharge on high demand.")
		ext.schedule_battery_discharge_on_high_demand(home, current_time, debug)

def calculate_weighted_priority(execution, current_time):
	maximum_delay = execution.appliance.maximum_delay
	start_time = execution.start_time if execution.start_time is not None else current_time
	waiting_time = start_time - execution.request_time + execution.previous_waiting_time

	if execution.profile.priority is URGENT:
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

def anticipate_pending_executions(home, current_time, debug=False):
	pending_executions = sorted(list(get_pending_executions(home)), key=lambda e: calculate_weighted_priority(e, current_time), reverse=True)
	for execution in pending_executions:
		print(f"Attempting to anticipate execution {execution.id}.")
		_, chosen_time = propose_schedule_execution(execution, current_time)
		if chosen_time < execution.start_time:
			schedule_execution(execution, current_time, debug)
		else:
			print("Unable to anticipate execution.")

def start_aggregator_client(home):
	home.set_outside_id(home.id) # hack: home_id == outside_id only when simulating locally
	home.set_accept_recommendations(True)
	if not cli.started:
		cli.start()
	send_consumption_schedule(home)

def stop_aggregator_client(home):
	home.set_accept_recommendations(False)
	if cli.started and not Home.objects.filter(accept_recommendations=True):
		cli.stop()

def send_consumption_schedule(home):
	if cli.started and home.outside_id is not None:
		cli.send_update_schedule(home)

def change_threshold(home, threshold):
	home.set_consumption_threshold(threshold)
	now = timezone.now()
	anticipate_pending_executions(home, now)

def start():
	aps.start()
	for home in Home.objects.all():
		if hasattr(home, "batterystoragesystem"):
			background.add_job(
				schedule_battery_charge_job,
				args=[home.id],
				trigger=CronTrigger(hour=2),
				id=f"schedule_battery_charge_{home.id}",
				replace_existing=True
			)
		if cli.started and home.outside_id is not None:
			background.add_job(
				send_consumption_schedule_job,
				args=[home.id],
				trigger=CronTrigger(hour="*/4"),
				id=f"send_consumption_schedule_{home.id}",
				replace_existing=True
			)
		home.set_running(True)
	print("Start process complete.")

background = aps.scheduler