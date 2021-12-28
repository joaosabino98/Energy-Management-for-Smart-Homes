from django.core.management.base import BaseCommand
from scheduler.scheduler import Scheduler
from scheduler.models import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        Scheduler()
        print("Scheduler running.")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Shutting down Scheduler...")
            AppVals.set_running(False)
