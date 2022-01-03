from django.core.management.base import BaseCommand
from manager.schedule_manager import ScheduleManager
from scheduler.models import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        ScheduleManager()
        print("Scheduler running.")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Shutting down Scheduler...")
            AppVals.set_running(False)
