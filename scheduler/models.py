from django.db import models, transaction
from .settings import PRIORITY_OPTIONS, SCHEDULABILITY_OPTIONS
from django.utils import timezone

# Create your models here.

class AppVals(models.Model):
    consumption_threshold = models.IntegerField(help_text="Consumption threshold (W)")
    is_running = models.BooleanField()

    @classmethod
    def get_consumption_threshold(cls):
        with transaction.atomic():
            val = cls.objects.select_for_update().first()
            return val.consumption_threshold
    
    @classmethod
    def set_consumption_threshold(cls, new_val):
        with transaction.atomic():
            val = cls.objects.select_for_update().first()
            val.consumption_threshold = new_val
            val.save()

    @classmethod
    def get_running(cls):
        with transaction.atomic():
            val = cls.objects.select_for_update().first()
            return val.is_running
    @classmethod
    def set_running(cls, new_val):
        with transaction.atomic():
            val = cls.objects.select_for_update().first()
            val.is_running = new_val
            val.save()

'''
Profile class
Generic profiles for appliances, with rated power and default priority.
Preloaded in the system.
'''
class Profile(models.Model):
    name = models.CharField(max_length=50, unique=True)
    schedulability = models.IntegerField(
        choices=SCHEDULABILITY_OPTIONS
    )
    priority = models.IntegerField(
        choices=PRIORITY_OPTIONS
    )
    maximum_delay = models.DurationField(default=timezone.timedelta(seconds=3600))
    rated_power = models.IntegerField(help_text="Rated power (W)")

    def __str__(self):
        return self.name

'''
Appliance class
Represent the appliances in the household.
Added by the user.
May require switching the profile for different uses.
'''
class Appliance(models.Model):
    name = models.CharField(max_length=100)
    profile = models.ManyToManyField(Profile)
    maximum_duration_of_usage = models.DurationField(default=timezone.timedelta(seconds=7200))

    def __str__(self):
        return self.name

'''
Execution class
Correspond to scheduling requests by appliances that need to run.
Life cycle:
 1. Requested
 2. Started
 3. Interrupted or Finished
If execution ends with interruption, a new execution needs to be created to restart its life cycle.
End time is by default the start time + maximum duration of usage.
'''
class Execution(models.Model):
    request_time = models.DateTimeField(default=timezone.now)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    previous_progress_time = models.DurationField(default=timezone.timedelta())
    previous_waiting_time = models.DurationField(default=timezone.timedelta())
    appliance = models.ForeignKey(Appliance, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    is_started = models.BooleanField(default=False)
    is_interrupted = models.BooleanField(default=False)
    is_finished = models.BooleanField(default=False)

    def start(self):
        with transaction.atomic():
            self.start_time = timezone.now()
            self.end_time = self.start_time + self.appliance.maximum_duration_of_usage - self.previous_progress_time
            self.is_started = True
            self.save()

    def interrupt(self):
        with transaction.atomic():
            self.end_time = timezone.now()
            self.is_interrupted = True
            self.save()

    def finish(self):
        with transaction.atomic():
            self.end_time = timezone.now()
            self.is_finished = True
            self.save()

    def set_started(self):
        with transaction.atomic():
            self.is_started = True
            self.save()

    def set_finished(self):
        with transaction.atomic():
            self.is_finished = True
            self.save()

    def set_start_time(self, start_time):
        with transaction.atomic():
            self.start_time = start_time
            self.end_time = start_time + self.appliance.maximum_duration_of_usage - self.previous_progress_time
            self.save()

    def status(self):
        if (self.is_finished):
            return "Finished"
        elif (self.is_interrupted):
            return "Interrupted"
        elif (self.is_started):
            return "Started"
        else:
            return "Pending"

    def __str__(self):
        request_time = self.request_time.strftime("%m/%d/%Y, %H:%M:%S")
        return f"Execution of {self.appliance.name} requested at {request_time}. Status: {self.status()}"

# Self-production: PV, batteries

class EnergyStorage(models.Model):
    capacity = models.IntegerField(help_text="Battery capacity (W)")

class PhotovoltaicSystem(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    tilt = models.IntegerField()
    azimut = models.IntegerField()
    capacity = models.IntegerField(help_text="System name plate capacity (Wdc)")

class ProductionData(models.Model):
    system = models.ForeignKey(PhotovoltaicSystem, on_delete=models.CASCADE)
    month_name = models.TextChoices("month_name", "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER")
    month = models.CharField(choices=month_name.choices, max_length=9)
    hour = models.IntegerField()
    average_power_generated = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['system', 'month', 'hour'], name='unique_system_hourly_value')]