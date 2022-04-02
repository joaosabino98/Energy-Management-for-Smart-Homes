import zmq
import json

from django.utils import timezone

import processor.core as core
import processor.external_energy as ext
from processor.tools import compact_periods
from scheduler.models import NoAggregatorException

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

def get_consumption_periods(current_time):
    consumption_periods = {}
    reference_times = ext.get_day_reference_times(current_time)
    prev_time = None
    for time in reference_times:
        if prev_time is not None:
            power_from_grid = core.get_power_consumption(prev_time) - ext.get_power_production(prev_time)
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
    print("Received reply: %s" % response)
    return response

def send_update_schedule(home_id, current_time=timezone.now()):
    if started:
        consumption_periods = get_consumption_periods(current_time)
        formatted_periods = format_time_periods(consumption_periods, True)
        str = f"update {home_id} {json.dumps(formatted_periods)}".encode("utf-8")
        socket.send(str)
        response = socket.recv().decode("utf-8")
        print("Received reply: %s" % response)