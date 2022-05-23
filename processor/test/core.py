import processor.core as core

def start_execution_job(id):
    return core.start_execution_job(id)

def finish_execution_job(id):
    return core.finish_execution_job(id)

def get_unfinished_executions():
    return core.get_unfinished_executions()

def get_pending_executions():
    return core.get_pending_executions()

def get_running_executions():
    return core.get_running_executions()

def get_running_executions_within(start_time, end_time):
    return core.get_running_executions_within(start_time, end_time)

def get_lower_priority_shiftable_executions_within(start_time, end_time, target_priority):
    return core.get_lower_priority_shiftable_executions_within(start_time, end_time, target_priority)

def get_power_consumption(time, queryset=None):
    return core.get_power_consumption(time, queryset)

def get_maximum_consumption_within(start_time, end_time, queryset=None):
    return core.get_maximum_consumption_within(start_time, end_time, queryset)

def calculate_execution_end_time(execution, start_time, duration=None):
    return core.calculate_execution_end_time(execution, start_time, duration)

def choose_execution_time(execution, minimum_start_time=None):
    return core.choose_execution_time(execution, minimum_start_time)

def get_available_execution_times(execution, minimum_start_time=None, include_bss=False, include_shiftable=False):
    return core.get_available_execution_times(execution, minimum_start_time, include_bss, include_shiftable)

def get_consumption_reference_times_within(start_time, end_time, queryset=None):
    return core.get_consumption_reference_times_within(start_time, end_time, queryset)

def start_execution(execution, start_time):
    return core.start_execution(execution, start_time, debug=True)

def interrupt_execution(execution):
    return core.interrupt_execution(execution)

def finish_execution(execution):
    return core.finish_execution(execution, debug=True)

def propose_schedule_execution(execution, request_time=None):
    return core.propose_schedule_execution(execution, request_time)

def schedule_execution(execution, request_time=None):
    return core.schedule_execution(execution, request_time, debug=True)

def shift_executions(execution, start_time, request_time=None):
    return core.shift_executions(execution, start_time, request_time, debug=True)

def interrupt_shiftable_executions(start_time, end_time, rated_power, priority):
    return core.interrupt_shiftable_executions(start_time, end_time, rated_power, priority)

def get_shiftable_power(start_time, end_time, priority):
    return core.get_shiftable_power(start_time, end_time, priority)

def check_high_demand(start_time, end_time, current_time):
    return core.check_high_demand(start_time, end_time, current_time, debug=True)

def calculate_weighted_priority(execution, current_time):
    return core.calculate_weighted_priority(execution, current_time)

def anticipate_pending_executions(current_time):
    return core.anticipate_pending_executions(current_time, debug=True)

def start_aggregator_client(accept_recommendations):
    return core.start_aggregator_client(accept_recommendations)

def send_consumption_schedule():
    return core.send_consumption_schedule()
    
def change_threshold(threshold):
    return core.change_threshold(threshold)

def set_id(id):
    return core.set_id(id)