import os
import django
import time
import zmq

from django.core.management.base import BaseCommand
from manager.schedule_core import ScheduleManager
from scheduler.models import *

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scheduler.settings")
django.setup()

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

def parse_request(socket, message):
    try:
        parsed_message = message.split(" ")
        match parsed_message[0]:
            case 'schedule':
                _, appliance_id, profile_id = parsed_message
                if (Appliance.objects.filter(pk=appliance_id).exists() and Profile.objects.filter(pk=profile_id).exists()):
                    execution = Execution.objects.create(
                        appliance=Appliance.objects.get(pk=appliance_id),
                        profile=Profile.objects.get(pk=profile_id))
                    result, _ = ScheduleManager().schedule_execution(execution)
                    if (result == True):
                        time = Execution.objects.get(pk=execution.id).start_time.strftime("%m/%d/%Y, %H:%M:%S")
                        message = f"Successful activation. Execution {execution.id} starting at {time}.".encode("utf-8")
                        socket.send(message)
                    else:
                        socket.send(b"Unable to activate.")
                else:
                    raise InvalidParametersException()
            case 'finish':
                _, execution_id = parsed_message
                if (Execution.objects.filter(pk=execution_id).exists()):
                    execution = Execution.objects.get(pk=execution_id)
                    ScheduleManager().finish_execution(execution)
                    message = f"Execution finished. {execution.appliance.name} stopped.".encode("utf-8")
                    socket.send(message)
                else:
                    raise InvalidParametersException()
            case 'threshold':
                _, threshold = parsed_message
                ScheduleManager().change_threshold(threshold)
                message = f"Threshold set to {threshold}.".encode("utf-8")
                socket.send(message)

            case 'exit':
                print("Shutting down Scheduler...")
                AppVals.set_running(False)
                socket.close()
                os._exit(0)
    except InvalidParametersException:
        socket.send(b"Error processing action.")

class InvalidParametersException(Exception):
    pass

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Scheduler running. Awaiting requests.")
        while True:
            message = socket.recv()
            print("Received request: %s" % message.decode('utf-8'))
            parse_request(socket, message.decode('utf-8'))

