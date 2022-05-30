import zmq
import json

from django.utils import timezone

import processor.core as core
import processor.external_energy as ext
from processor.tools import compact_periods
from coordinator.models import NoAggregatorException

context = zmq.Context()
socket = None
started = False

def start():
    print("Connecting to aggregator…")
    global socket
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    global started
    started = True

def stop():
    global started
    started = False
    context.term()

def get_consumption_periods(home, current_time):
    lower_bound = current_time - timezone.timedelta(days=3)
    upper_bound = current_time + timezone.timedelta(days=3)
    consumption_periods = {}
    reference_times = core.get_consumption_reference_times_within(home, lower_bound, upper_bound)
    prev_time = None
    for time in reference_times:
        if prev_time is not None:
            power_from_grid = core.get_power_consumption(home, prev_time) - ext.get_power_production(home, prev_time)
            if power_from_grid != 0:
                consumption_periods[(prev_time, time)] = power_from_grid
        prev_time = time
    consumption_periods = compact_periods(consumption_periods)
    return consumption_periods

# Convert from {(start_time, end_time): power } to {start_time: {end_time: X, power: Y}}
def format_time_periods(periods, include_value=True):
    formatted_periods = {}
    i = 1
    for period in periods:
        details = {}
        if period[1] is not None:
            details["end_time"] = period[1].strftime("%Y-%m-%d %H:%M:%S:%f %z")
        if include_value:
            details["power"] = periods[period]
        formatted_periods[period[0].strftime("%Y-%m-%d %H:%M:%S:%f %z")] = details
        i += 1
    return formatted_periods

def send_choice_request(available_periods):
    if not started:
        raise NoAggregatorException()
    formatted_periods = format_time_periods(available_periods, False)
    str = f"choose {json.dumps(formatted_periods)}".encode("utf-8")
    socket.send(str)
    response = socket.recv().decode("utf-8")
    # print("Received reply: %s" % response)
    return response

def send_update_schedule(home, request_time=None):
    if request_time is None:
        request_time = timezone.now()
    if started:
        consumption_periods = get_consumption_periods(home, request_time)
        formatted_periods = format_time_periods(consumption_periods, True)
        str = f"update {home.outside_id} {json.dumps(formatted_periods)}".encode("utf-8")
        socket.send(str)
        response = socket.recv().decode("utf-8")
        print("Received reply: %s" % response)

def send_create_plot(graph_title):
    str = f"plot {graph_title}".encode("utf-8")
    socket.send(str)
    response = socket.recv().decode("utf-8")
    print("Received reply: %s" % response)
