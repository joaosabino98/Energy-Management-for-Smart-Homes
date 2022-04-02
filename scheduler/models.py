from django.db import models, transaction
from home.settings import INF_DATE
from .settings import PRIORITY_OPTIONS, SCHEDULABILITY_OPTIONS, STRATEGY_OPTIONS
from django.utils import timezone
from math import floor
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class Home(models.Model):
    consumption_threshold = models.IntegerField(help_text="Consumption threshold (W)")
    accept_recommendations = models.BooleanField(default=False)
    strategy = models.IntegerField(choices=STRATEGY_OPTIONS)
    is_running = models.BooleanField()

    def set_consumption_threshold(self, new_val):
        with transaction.atomic():
            self.consumption_threshold = new_val
            self.save()

    def set_accept_recommendations(self, new_val):
        with transaction.atomic():
            self.accept_recommendations = new_val
            self.save()

    def set_strategy(self, new_val):
        with transaction.atomic():
            self.strategy = new_val
            self.save()        

    def set_running(self, new_val):
        with transaction.atomic():
            self.is_running = new_val
            self.save()

    def compare_BSS_appliance(self, appliance):
        if not hasattr(self, "batterystoragesystem"):
            return False
        else:
            return self.batterystoragesystem.appliance.id == appliance.id

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
    maximum_delay = models.DurationField(default=timezone.timedelta(seconds=3600), null=True)
    rated_power = models.IntegerField(help_text="Rated power (W)")
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return self.name

'''
Appliance class
Represent the appliances in the household.
Added by the user.
May require switching the profile for different uses.
'''
class Appliance(models.Model):
    home = models.ForeignKey(Home, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    profiles = models.ManyToManyField(Profile)
    maximum_duration_of_usage = models.DurationField(null=True)

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
    home = models.ForeignKey(Home, on_delete=models.CASCADE)
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
            if self.end_time is None:
                if self.appliance.maximum_duration_of_usage is not None:
                    self.end_time = self.start_time + self.appliance.maximum_duration_of_usage - self.previous_progress_time
                else:
                    self.end_time = INF_DATE
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
            if self.end_time is None:
                if self.appliance.maximum_duration_of_usage is not None:
                    self.end_time = self.start_time + self.appliance.maximum_duration_of_usage - self.previous_progress_time
                else:
                    self.end_time = INF_DATE
            self.save()

    def status(self):
        if self.is_finished:
            return "Finished"
        elif self.is_interrupted:
            return "Interrupted"
        elif self.is_started:
            return "Started"
        else:
            return "Pending"

    def __str__(self):
        request_time = self.request_time.strftime("%d/%m/%Y, %H:%M:%S")
        return f"Execution of {self.appliance.name} requested at {request_time}. Status: {self.status()}"

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(fields=['appliance', 'profile', 'start_time'], name='unique_appliance_start_time'),
    #         models.UniqueConstraint(fields=['appliance', 'profile', 'request_time'], name='unique_appliance_request_time')
    #     ]

# Self-production: PV, batteries

class BatteryStorageSystem(models.Model):
    home = models.OneToOneField(Home, on_delete=models.CASCADE)
    appliance = models.ForeignKey(Appliance, on_delete=models.CASCADE, null=True, blank=True)
    total_energy_capacity = models.IntegerField(help_text="Total energy capacity (Wh)")
    continuous_power = models.IntegerField(help_text="Continuous charge/discharge power (W)")
    last_full_charge_time = models.DateTimeField(default=timezone.now)
    depth_of_discharge = models.FloatField(help_text="Depth-of-Discharge", default=1)

    def set_last_full_charge_time(self, last_full_charge_time=timezone.now):
        with transaction.atomic():
            self.last_full_charge_time = last_full_charge_time
            self.save()

@receiver(post_save, sender=BatteryStorageSystem, dispatch_uid="create_bss_appliance")
def create_bss_appliance(sender, instance, created, **kwargs):
    if created:
        charge_time = timezone.timedelta(seconds=floor(instance.total_energy_capacity / instance.continuous_power * 3600))
        instance.appliance, _ = Appliance.objects.get_or_create(
                    home=instance.home,
                    name="Battery Storage System",
                    defaults={
                        "maximum_duration_of_usage": charge_time
                    }
                )
        instance.save()

class PhotovoltaicSystem(models.Model):
    home = models.OneToOneField(Home, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    tilt = models.IntegerField()
    azimut = models.IntegerField()
    capacity = models.IntegerField(help_text="System name plate capacity (Wdc)")

class ProductionData(models.Model):
    system = models.ForeignKey(PhotovoltaicSystem, on_delete=models.CASCADE)
    month_name = models.IntegerChoices("MONTH", "JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER NOVEMBER DECEMBER")
    month = models.IntegerField(choices=month_name.choices)
    hour = models.IntegerField()
    average_power_generated = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['system', 'month', 'hour'], name='unique_system_hourly_value')]

class NoBSSystemException(Exception):
    pass

class NoPVSystemException(Exception):
    pass

class NoAggregatorException(Exception):
    pass