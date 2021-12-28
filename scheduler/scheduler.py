import re
from math import floor, log10
from django.db import transaction
from django.utils import timezone
from apscheduler.triggers.cron import CronTrigger
import scheduler.apsched as aps

from scheduler.settings import IMMEDIATE, INTERRUPTIBLE, LOW_PRIORITY, NONSCHEDULABLE, NORMAL
from .models import AppVals, Execution

def start_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if (execution.is_started is False):
		execution.set_started()
		Scheduler().add_running_execution(execution)
	print("Execution of " + execution.appliance.name + " started at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

def finish_execution_job(id):
	execution = Execution.objects.get(pk=id)
	if (execution.is_finished is False and execution.is_interrupted is False):
		execution.set_finished()
		Scheduler().running.pop(execution, None)
	print("Execution of " + execution.appliance.name + " finished by the system at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

def update_schedule_table_job():
	Scheduler().populate_schedule()

def update_queue_priorities_job():
	Scheduler().update_priorities()

class Singleton(type):
	def __init__(self, name, bases, mmbs):
		super(Singleton, self).__init__(name, bases, mmbs)
		self._instance = super(Singleton, self).__call__()

	def __call__(self, *args, **kw):
		return self._instance

class Scheduler(metaclass = Singleton):
	threshold = None
	bgsched = None
	step = 5      # 5 minutes
	pending = {}  # { Execution: priority }
	running = {}  # { Execution: priority }
	schedule = {} # { Datetime: energy available }
	
	def __init__(self):
		print("Initializing schedule table and queues.")
		self.threshold = AppVals.get_consumption_threshold()
		self.bgsched = aps.scheduler
		self.populate_schedule()
		self.populate_queues()
		self.start_aps()
		print("Initialization complete.")

	def start_aps(self):
		self.bgsched.add_job(
			update_schedule_table_job,
			trigger=CronTrigger(day="*", hour="00", minute="00"),
			id="update_schedule_table",
			replace_existing=True)

		self.bgsched.add_job(
			update_queue_priorities_job,
			trigger=CronTrigger(minute=f"*/{self.step}"),
			id="update_queue_priorities",
			replace_existing=True)
			
		aps.start()
		AppVals.set_running(True)

	def update_priorities(self):
		print("Updating priority of executions in queue.")
		running = list(self.running)
		pending = list(self.pending)
		for execution in running:
			priority = self.calculate_weighted_priority(execution)
			self.running[execution] = priority
		for execution in pending:
			priority = self.calculate_weighted_priority(execution)
			self.pending[execution] = priority
			if (priority > 8):
				print("Pending execution with high priority found. Attempting to shift lower priority running executions...")
				rated_power = execution.profile.rated_power
				result, interrupted = self.shift_executions(rated_power, priority)
				if (result == True):
					print("Lower priority running executions found.")
					self.remove_executions_from_schedule([execution])
					self.start_execution(execution)
					
					for execution in interrupted:
						new = Execution.objects.create(appliance=execution.appliance, profile=execution.profile)
						self.schedule_later(new)
				else:
					print("Unable to shift running executions. Attempting to reschedule earlier.")
					now = self.get_current_schedule_slot()
					start_time = self.get_available_time(now, execution)
					if (start_time is not None and start_time < execution.start_time):
						self.remove_executions_from_schedule([execution])
						self.schedule_later(execution)
					else:
						print("Unable to reschedule earlier.")

	"""
	def schedule_execution(self, execution) -> None

	Schedule executions.
	1. While enough power is available, schedule for immediate execution.
	2. Else, if lower priority executions can be shifted, schedule for immediate execution
	and schedule shifted executions for nearest available time (sorted by priority).
	3. If previous conditions can't be met, schedule for nearest available time.
	TODO: Handle night activations
	TODO: Handle energy production
	"""
	def schedule_execution(self, execution):
		rated_power = execution.profile.rated_power
		now = self.get_current_schedule_slot()
		available_time = self.get_available_time(now, execution)

		if (available_time == now):
			print("Enough available power.")
			self.start_execution(execution)
		else:
			print("Unable to activate immediately. Attempting to shift lower priority running executions...")
			priority = self.calculate_weighted_priority(execution)
			result, interrupted = self.shift_executions(rated_power, priority)
			if (result == True):
				print("Lower priority running executions found.")
				self.start_execution(execution)

				for execution in interrupted:
					new = Execution.objects.create(appliance=execution.appliance, profile=execution.profile)
					self.schedule_later(new)
			else:
				print("Unable to shift running executions.")
				self.schedule_later(execution)

	"""
	schedule_later(self, execution, prev_start) -> boolean

	Schedule to a later time.
	Return True if successful.
	Return False if unable to find slot.
	TODO different return if scheduled after maximum delay
	"""
	def schedule_later(self, execution):
		now = self.get_current_schedule_slot()
		start_time = self.get_available_time(now, execution)
		if (start_time is not None):
			self.start_execution(execution, start_time)
			return True
		else:
			print("Execution of " + execution.appliance.name + " can't be satisfied.")
			return False

	"""
	start_execution(self, execution, start_time) -> None

	Start execution, update schedule and add to running or pending dictionary. Start time can be specified.
	"""
	def start_execution(self, execution, start_time=None):
		if (start_time is None):
			execution.start()
			self.add_running_execution(execution)
			print("Execution of " + execution.appliance.name + " started at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))
		else:
			execution.set_start_time(start_time)
			self.add_pending_execution(execution)
			self.bgsched.add_job(start_execution_job, 'date', [execution.id],
				run_date=execution.start_time,
				id=str(execution.id) + "_start",
				max_instances=1,
				replace_existing=True)
			print("Execution of " + execution.appliance.name + " starting at " + start_time.strftime("%m/%d/%Y, %H:%M:%S."))
		self.add_executions_to_schedule([execution])
		self.bgsched.add_job(finish_execution_job, 'date', [execution.id],
			id=str(execution.id) + "_finish",
			run_date=execution.end_time,
			max_instances=1,
			replace_existing=True)

	def interrupt_execution(self, execution):
		execution.interrupt()
		self.running.pop(execution, None)
		print("Execution of " + execution.appliance.name + " interrupted at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

	def finish_execution(self, execution):
		execution.finish()
		self.running.pop(execution, None)
		print("Execution of " + execution.appliance.name + " finished by the user at " + timezone.now().strftime("%m/%d/%Y, %H:%M:%S."))

	"""
	def shift_executions(self, rated_power, priority) -> boolean, list

	Verify if enough running executions with lower priority can be interrupted to meet energy demand. Interrupt if so.
	Return True with list of interrupted devices in case of success.
	Return False with empty list if not enough devices can be interrupted.
	"""
	def shift_executions(self, rated_power, priority):
		# Shift running interruptible executions with lower priority until power necessity is met; return True if possible
		now = self.get_current_schedule_slot()
		power_available = self.schedule[now]
		shiftable_executions, shiftable_power = self.get_lower_priority_shiftable_executions(priority)

		if (power_available + shiftable_power < rated_power):
			return False, []

		interrupted = []

		for execution in shiftable_executions:
			self.interrupt_execution(execution)
			self.bgsched.remove_job(str(execution.id) + "_finish")
			interrupted.append(execution)
			power_available += execution.profile.rated_power
			if (power_available >= rated_power):
				break

		self.update_executions_in_schedule(interrupted)

		return True, interrupted

	"""
	def get_available_time(self, minimum_time, execution) -> Datetime

	Returns first slot in a series of consecutive slots with:
	1. equal or more available power than required by execution
	2. span of the execution's maximum duration of usage (if non-interruptible)
	TODO: If execution is interruptible, respecting maximum delay is preferred over maximum duration
	"""
	def get_available_time(self, minimum_time, execution):
		slots_needed = (-execution.appliance.maximum_duration_of_usage.seconds/60) // (-self.step) # ceiling division
		slot = None
		found = 0
		for time in self.schedule.keys():
			if time >= minimum_time and self.schedule[time] >= execution.profile.rated_power:
				if (found == 0):
					slot = time
				found += 1
				if (found == slots_needed):
					break
			else:
				found = 0
		return slot

	def get_lower_priority_shiftable_executions(self, priority):
		temp = {}
		shiftable_power = 0
		for execution in self.running:
			if (self.running[execution] < priority and execution.profile.schedulability is INTERRUPTIBLE):
				temp[execution] = self.running[execution]
				shiftable_power += execution.profile.rated_power
		sorted_keys = sorted(temp, key=temp.get)

		return sorted_keys, shiftable_power

	def add_running_execution(self, execution):
		priority = self.calculate_weighted_priority(execution)
		self.running[execution] = priority
		self.pending.pop(execution, None) # remove from pending if present

	def add_pending_execution(self, execution):
		priority = self.calculate_weighted_priority(execution)
		self.pending[execution] = priority
		self.running.pop(execution, None) # remove from running if present

	def get_current_schedule_slot(self):
		now = timezone.now()
		for time in self.schedule.keys():
			next = time + timezone.timedelta(minutes=self.step)
			if (next >= now):
				return time
	
	def calculate_weighted_priority(self, execution):
		maximum_delay = execution.profile.maximum_delay
		# # subtracting from start_time creates round-robin:
		# # - running executions maintain priority while pending executions increment
		# # - pending executions replace running executions on every priority recalculation
		# # subtracting from current time ensures stability
		# delay_since_request = execution.start_time - execution.request_time if execution.is_started \
		# 	else timezone.now() - execution.request_time
		delay_since_request = timezone.now() - execution.request_time
		remaining_acceptable_delay = maximum_delay - delay_since_request
		acc_delay_in_minutes = remaining_acceptable_delay.seconds/60 if maximum_delay > delay_since_request else 0

		if (execution.profile.priority is IMMEDIATE):
			priority = 10
		elif (execution.profile.priority is LOW_PRIORITY): 
			priority = 1
		else:
			# Formula: floor of exponential function transformed to fit
			# max priority (10) to delays < 8 minutes
			# lowest priority (1) to delays > 180 minutes
			priority = floor(10**(-(acc_delay_in_minutes/180 - 1)) + 1)

		return priority
	
	"""
	add_executions_to_schedule(self, list[]) -> None

	Add executions to schedule without requiring to repopulate schedule.
	CAN support shifted executions if schedule is first updated to subtract on end_time 
	"""
	def add_executions_to_schedule(self, list):
		for execution in list:
			for time in self.schedule.keys():
				next = time + timezone.timedelta(minutes=self.step)
				if (execution.start_time is not None and execution.start_time < next \
					and (execution.end_time is None or execution.end_time > time)):
					self.schedule[time] -= execution.profile.rated_power

	"""
	update_executions_in_schedule(self, list[]) -> None

	Update schedule with changes in selected executions.
	Called if executions were interrupted or finished before maximum duration of usage.
	"""
	def update_executions_in_schedule(self, list):
		for execution in list:
			if (execution.is_finished or execution.is_interrupted):
				for time in self.schedule.keys():             
					# restore available power to slots after real end-time and before expected end_time
					if (execution.end_time < time \
					and execution.start_time + execution.appliance.maximum_duration_of_usage > time):
						self.schedule[time] += execution.profile.rated_power    

	"""
	remove_executions_from_schedule(self, list[]) -> None

	Remove executions from schedule without requiring to repopulate schedule.
	Called for executions that were moved before start.
	"""
	def remove_executions_from_schedule(self, list):
		for execution in list:
			if (execution.is_started is False):
				for time in self.schedule.keys():
					next = time + timezone.timedelta(minutes=self.step)
					if (execution.start_time is not None and execution.start_time < next \
						and (execution.end_time is None or execution.end_time > time)):
						self.schedule[time] += execution.profile.rated_power

	"""
	RUN AT START
	"""
	def generate_timezone_aware_schedule(self):
		# generate sliding window of 36h (includes morning of next day)
		midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
		return {midnight + timezone.timedelta(minutes=self.step * slot): self.threshold for slot in range(36*60//self.step)}

	def populate_schedule(self):
		date_limit = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=2)
		self.schedule = self.generate_timezone_aware_schedule()
		for time in self.schedule.keys():
			next = time + timezone.timedelta(minutes=self.step)
			for execution in Execution.objects.filter(request_time__gt=date_limit):
				if (execution.start_time is not None and execution.start_time < next \
					and (execution.end_time is None or execution.end_time > time)):
					self.schedule[time] -= execution.profile.rated_power

	def populate_queues(self):
		date_limit = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=2)
		current_time = timezone.now()
		for execution in Execution.objects.filter(request_time__gt=date_limit):
			if (execution.start_time is not None and execution.start_time < current_time \
				and (execution.end_time is None or execution.end_time > current_time)):
				self.add_running_execution(execution)
			elif (execution.start_time is None or execution.start_time > current_time):
				self.add_pending_execution(execution)

	"""
	DEBUG
	"""
	def get_running_executions_in_slot(self, time):
		date_limit = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timezone.timedelta(days=2)
		slot = self.parse_time_to_slot(time)
		running = []
		for execution in Execution.objects.filter(request_time__gt=date_limit):
			if (execution.start_time is not None and execution.start_time < slot \
				and (execution.end_time is None or execution.end_time > slot)):
				running.append(execution)
		return running

	def parse_time_to_slot(self, time):
		tz = timezone.get_current_timezone()
		if (isinstance(time, str)):
			date_format = "%Y.%m.%d.%H.%M.%S"
			time = re.sub('(, )|[-:/ ]', ".", time)
			while (len(time.split(".")) < 6):
				time += ".00"
			slot = timezone.datetime.strptime(time, date_format).astimezone(tz)
		elif (isinstance(time, timezone.datetime)):
			slot = time.astimezone(tz) if time.tzinfo is None else time
		else:
			slot = None
		return slot

"""
		def calculate_weighted_priority(self, execution):
			maximum_delay = execution.profile.maximum_delay
			delay_since_request = timezone.now() - execution.request_time
			remaining_acceptable_delay = maximum_delay - delay_since_request
			acc_delay_in_minutes = remaining_acceptable_delay.seconds/60

			k = 0

			if (execution.profile.priority is IMMEDIATE):
				k = 0.1
			elif (execution.profile.priority is NORMAL):    
				k = 1
			elif (execution.profile.priority is LOW_PRIORITY): 
				k = 3

			# formula: floor of logarithmic regression to fit steps at 5, 20, 30, 60 minutes in normal mode
			priority = floor(10*k*log10(acc_delay_in_minutes/(20*k) +1) +1)

			return priority
"""