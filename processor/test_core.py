import processor.core as core
from django.utils import timezone

def start_execution_job(id):
    return core.start_execution_job(id)

def finish_execution_job(id):
    return core.finish_execution_job(id)

def find_anticipable_executions_job():
    return core.anticipate_pending_executions_job()

def change_threshold(threshold):
    return core.change_threshold(threshold)

def get_unfinished_executions():
    return core.get_unfinished_executions()

def get_running_executions():
    return core.get_running_executions()

def get_running_executions_within(start_time, end_time):
    return core.get_running_executions_within(start_time, end_time)

def get_lower_priority_shiftable_executions_within(start_time, end_time, target_power, target_priority):
    return core.get_lower_priority_shiftable_executions_within(start_time, end_time, target_power, target_priority)

def get_pending_executions():
    return core.get_pending_executions()

def get_energy_consumption(time, queryset=None):
    return core.get_energy_consumption(time, queryset)

def get_maximum_consumption_within(start_time, end_time, queryset=None):
    return core.get_maximum_consumption_within(start_time, end_time, queryset)

def get_positive_energy_difference(rated_power, target_power):
    return core.get_positive_energy_difference(rated_power, target_power)

def get_available_execution_time(execution, minimum_start_time=timezone.now()):
    return get_available_execution_time(execution, minimum_start_time)

def get_available_fractioned_execution_time(execution, minimum_start_time=timezone.now()):
    return get_available_fractioned_execution_time(execution, minimum_start_time)

def get_reference_times_within(start_time, end_time, queryset=None):
    return get_reference_times_within(start_time, end_time, queryset)

def start_execution(execution, start_time=None):
    return core.start_execution(execution, start_time, debug=True)

def interrupt_execution(execution):
    return core.interrupt_execution(execution)

def finish_execution(execution):
    return core.finish_execution(execution)

def schedule_execution(execution):
    return core.schedule_execution(execution, debug=True)

def schedule_later(execution):
    return core.schedule_later(execution, debug=True)

def shift_executions(start_time, end_time, rated_power, priority):
    return core.shift_executions(start_time, end_time, rated_power, priority)

def calculate_weighted_priority(execution):
    return core.calculate_weighted_priority(execution)

def anticipate_pending_executions():
    return core.anticipate_pending_executions(debug=True)