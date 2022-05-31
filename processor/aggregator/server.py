import zmq
import json
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from django.utils import timezone
from aggregator.models import ConsumptionData
from home.settings import INF_DATE

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

def get_scheduled_consumption():
	return ConsumptionData.objects.exclude(end_time__lt=timezone.now()).order_by('end_time')

def create_consumption_data(home_id, start_time, end_time, power):
    return ConsumptionData.objects.create(
        home_id=home_id,
        start_time=start_time,
        end_time=end_time,
        power=power
    )

def clean_consumption_data(home_id):
    ConsumptionData.objects.filter(home_id=home_id).delete()

def get_scheduled_consumption_within(start_time, end_time):
	scheduled = get_scheduled_consumption()
	if end_time is None:
		return scheduled.filter(end_time__gt=start_time)
	return scheduled.filter(start_time__lte=end_time).filter(end_time__gt=start_time)

def get_power_consumption(time):
	power_consumption = 0
	queryset = get_scheduled_consumption_within(time, time)
	for consumption in queryset:
		power_consumption += consumption.power
	return power_consumption

def get_consumption_reference_times_within(start_time, end_time):
    time_list = [start_time]
    if end_time is not None and end_time != INF_DATE:
        time_list.append(end_time)
    queryset = get_scheduled_consumption_within(start_time, end_time)
    for execution in queryset:
        if execution.start_time >= start_time:
            time_list.append(execution.start_time)
        if execution.end_time is not None and (end_time is None or execution.end_time < end_time):
            time_list.append(execution.end_time)
    time_list = sorted(list(dict.fromkeys(time_list)))
    return time_list

def get_maximum_power_consumption_within(start_time, end_time):
	peak_consumption = 0
	reference_times = get_consumption_reference_times_within(start_time, end_time)
	for time in reference_times:
		power_consumption = get_power_consumption(time)
		if power_consumption > peak_consumption:
			peak_consumption = power_consumption
	return peak_consumption

def handle_choose_time_request(period_string):
    available_periods = json.loads(period_string)
    minimum_consumption = None
    selected_index = index = 0
    for period in available_periods:
        start_time = timezone.datetime.strptime(period, '%Y-%m-%d %H:%M:%S:%f %z')
        end_time = timezone.datetime.strptime(available_periods[period]["end_time"], '%Y-%m-%d %H:%M:%S:%f %z')
        power_consumption = get_maximum_power_consumption_within(start_time, end_time)
        if minimum_consumption is None or power_consumption < minimum_consumption:
            minimum_consumption = power_consumption
            selected_index = index
        index += 1
    str = f"{selected_index}".encode("utf-8")
    socket.send(str)

def handle_update_schedule_request(home_id, period_string):
    clean_consumption_data(home_id)
    consumption_periods = json.loads(period_string)
    for period in consumption_periods:
        start_time = timezone.datetime.strptime(period, '%Y-%m-%d %H:%M:%S:%f %z')
        end_time = timezone.datetime.strptime(consumption_periods[period]["end_time"], '%Y-%m-%d %H:%M:%S:%f %z')
        power = consumption_periods[period]["power"]
        create_consumption_data(home_id, start_time, end_time, power)
    str = f"Consumption data updated.".encode("utf-8")
    socket.send(str)    

def handle_create_consumption_plot_request(title):
    myFmt = mdates.DateFormatter('%H:%M')
    morning_before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1,hours=6)
    morning_after = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=2, hours=6)
    # morning_before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1,hours=18)
    # morning_after = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=2, hours=12)
    reference_times = get_consumption_reference_times_within(morning_before, morning_after)
    x = np.array([get_np_time(time) for time in reference_times])
    y = np.array([get_power_consumption(time) for time in reference_times])
    _, ax = plt.subplots(constrained_layout=True)
    ax.step(x, y, where='post')
    ax.set_title(title)
    ax.set_xlabel('Time (hh:mm)')
    ax.set_ylabel('Consumption (W)')
    ax.xaxis.set_major_formatter(myFmt)
    ax.xaxis.set_tick_params(rotation=40)

    weights = []
    for i in range(0, len(reference_times) - 1):
        time = (reference_times[i+1] - reference_times[i]).seconds
        weights.append(time)

    peak = np.amax(y)
    average = np.average(y[0:-1], weights=weights)
    print(f"Peak: {peak}\nAverage: {average}\nPAR: {peak/average}")
    plt.show()
    str = f"OK.".encode("utf-8")
    socket.send(str)    

def parse_request(message):
    parsed_message = message.split(" ", 2)
    match parsed_message[0]:
        case 'choose': # ask for best available time
            handle_choose_time_request(message[7:])
        case 'update': # send all consumption periods
            handle_update_schedule_request(parsed_message[1], parsed_message[2])
        case 'plot': # debug
            parsed_message = message.split(" ", 1)
            handle_create_consumption_plot_request(parsed_message[1])


def receive_request():
    message = socket.recv().decode('utf-8')
    print("Received request: %s" % message)
    parse_request(message)

def get_np_num(time):
    return mdates.date2num(timezone.make_naive(time))

def get_np_time(time):
    return mdates.num2date(mdates.date2num(timezone.make_naive(time)))

