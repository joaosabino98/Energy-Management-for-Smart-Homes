import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import processor.core as coordinator

from django.test import TestCase, tag
from django.utils import timezone
from coordinator.settings import NONINTERRUPTIBLE, NORMAL
from coordinator.models import Home, Execution, Appliance, Profile

@tag('house1')
class SingleHouse1TestCase(TestCase):
    fixtures = ['coordinator/fixtures/three_houses_profiles.json', 'coordinator/fixtures/three_houses_data.json']

    def setUp(self):
        self.midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        home = Home.objects.get(pk=1)
        
        self.title = ""
        self.executions = []
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Fridge"),
            profile=Profile.objects.get(pk=6),
            request_time=self.midnight
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            profile=Profile.objects.get(pk=24),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=5)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=22)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Toaster"),
            profile=Profile.objects.get(pk=27),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=24)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Microwave"),
            profile=Profile.objects.get(pk=1),
            request_time=self.midnight + timezone.timedelta(hours=13, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Television (Living Room)"),
            profile=Profile.objects.get(pk=37),
            request_time=self.midnight + timezone.timedelta(hours=17, minutes=30)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Vacuum Cleaner"),
            profile=Profile.objects.get(pk=12),
            request_time=self.midnight + timezone.timedelta(hours=17, minutes=50)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Oven"),
            profile=Profile.objects.get(pk=4),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Dishwasher"),
            profile=Profile.objects.get(pk=7),
            request_time=self.midnight + timezone.timedelta(hours=22, minutes=20)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Washing Machine"),
            profile=Profile.objects.get(pk=35),
            request_time=self.midnight + timezone.timedelta(hours=22, minutes=23)
        ))

    def test_scenario_baseline_house_1(self):
        home = Home.objects.get(pk=1)
        home.set_consumption_threshold(10000)
        Profile.objects.all().update(schedulability=NONINTERRUPTIBLE, priority=NORMAL)
        self.title = "Baseline consumption for household 1"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('managed')
    def test_scenario_scheduled_single_house_1(self):
        self.title = 'Managed consumption for household 1'

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

        
    def tearDown(self):
        home = Home.objects.get(pk=1)
        myFmt = mdates.DateFormatter('%H:%M')
        morning_before = self.midnight + timezone.timedelta(days=0, hours=6)
        morning_after = self.midnight + timezone.timedelta(days=1, hours=6)
        reference_times = coordinator.get_consumption_reference_times_within(home, morning_before, morning_after)
        x = np.array([get_np_time(time) for time in reference_times])
        y = np.array([coordinator.get_power_consumption(home, time) for time in reference_times])
        _, ax = plt.subplots(constrained_layout=True)
        ax.step(x, y, where='post')
        ax.set_title(self.title)
        ax.set_xlabel('Time (hh:mm)')
        ax.set_ylabel('Consumption (W)')
        ax.xaxis.set_major_formatter(myFmt)
        ax.xaxis.set_tick_params(rotation=40)

        executions = coordinator.get_unfinished_executions(home, morning_before)
        delay_to_max = [(e.start_time - e.request_time).seconds / e.appliance.maximum_delay.seconds for e in executions]
        weights = []
        for i in range(0, len(reference_times) - 1):
            time = (reference_times[i+1] - reference_times[i]).seconds
            weights.append(time)

        peak = np.amax(y)
        average = np.average(y[0:-1], weights=weights)
        max_delay_to_max = np.average(delay_to_max)
        print(f"Peak: {peak}\nAverage: {average}\nPAR: {peak/average}\nAverage DAWR: {max_delay_to_max}")

        plt.show()

@tag('house2')
class SingleHouse2TestCase(TestCase):
    fixtures = ['coordinator/fixtures/three_houses_profiles.json', 'coordinator/fixtures/three_houses_data.json']

    def setUp(self):
        self.midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        home = Home.objects.get(pk=2)

        self.title = ""
        self.executions = []
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Fridge"),
            profile=Profile.objects.get(pk=6),
            request_time=self.midnight
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=34)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Microwave"),
            profile=Profile.objects.get(pk=1),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=37)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=40)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            profile=Profile.objects.get(pk=25),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=0)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Television (Kitchen)"),
            profile=Profile.objects.get(pk=20),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=15)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=22)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Washing Machine"),
            profile=Profile.objects.get(pk=10),
            request_time=self.midnight + timezone.timedelta(hours=9, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=15),
            request_time=self.midnight + timezone.timedelta(hours=12, minutes=15)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Air Conditioner"),
            profile=Profile.objects.get(pk=5),
            request_time=self.midnight + timezone.timedelta(hours=14, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Vacuum Cleaner"),
            profile=Profile.objects.get(pk=12),
            request_time=self.midnight + timezone.timedelta(hours=15, minutes=50)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Oven"),
            profile=Profile.objects.get(pk=4),
            request_time=self.midnight + timezone.timedelta(hours=19, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=14),
            request_time=self.midnight + timezone.timedelta(hours=19, minutes=55)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Dishwasher"),
            profile=Profile.objects.get(pk=7),
            request_time=self.midnight + timezone.timedelta(hours=22, minutes=00)
        ))

    def test_scenario_baseline_house_2(self):
        home = Home.objects.get(pk=2)
        home.set_consumption_threshold(10000)
        Profile.objects.all().update(schedulability=NONINTERRUPTIBLE, priority=NORMAL)
        self.title = "Baseline consumption for household 2"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('managed')
    def test_scenario_scheduled_single_house_2(self):
        self.title = 'Managed consumption for household 2'

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    def tearDown(self):
        home = Home.objects.get(pk=2)
        myFmt = mdates.DateFormatter('%H:%M')
        morning_before = self.midnight + timezone.timedelta(days=0, hours=6)
        morning_after = self.midnight + timezone.timedelta(days=1, hours=6)
        reference_times = coordinator.get_consumption_reference_times_within(home, morning_before, morning_after)
        x = np.array([get_np_time(time) for time in reference_times])
        y = np.array([coordinator.get_power_consumption(home, time) for time in reference_times])
        _, ax = plt.subplots(constrained_layout=True)
        ax.step(x, y, where='post')
        ax.set_title(self.title)
        ax.set_xlabel('Time (hh:mm)')
        ax.set_ylabel('Consumption (W)')
        ax.xaxis.set_major_formatter(myFmt)
        ax.xaxis.set_tick_params(rotation=40)

        executions = coordinator.get_unfinished_executions(home, morning_before)
        delay_to_max = [(e.start_time - e.request_time).seconds / e.appliance.maximum_delay.seconds for e in executions]
        weights = []
        for i in range(0, len(reference_times) - 1):
            time = (reference_times[i+1] - reference_times[i]).seconds
            weights.append(time)

        peak = np.amax(y)
        average = np.average(y[0:-1], weights=weights)
        max_delay_to_max = np.average(delay_to_max)
        print(f"Peak: {peak}\nAverage: {average}\nPAR: {peak/average}\nAverage DAWR: {max_delay_to_max}")

        plt.show()

@tag('house3')
class SingleHouse3TestCase(TestCase):
    fixtures = ['coordinator/fixtures/three_houses_profiles.json', 'coordinator/fixtures/three_houses_data.json']

    def setUp(self):
        home = Home.objects.get(pk=3)
        exec(open("scripts/load_solar_data.py").read())
        self.midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        self.title = ""
        coordinator.ext.create_battery_execution(
            home,
            self.midnight + timezone.timedelta(hours=0),
            self.midnight + timezone.timedelta(hours=4),
            -4500
        )
        self.executions = []
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Fridge"),
            profile=Profile.objects.get(pk=6),
            request_time=self.midnight
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=20)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Toaster"),
            profile=Profile.objects.get(pk=27),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=36)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=39)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            profile=Profile.objects.get(pk=25),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=43)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=33),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=45)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=38),
            request_time=self.midnight + timezone.timedelta(hours=7, minutes=45)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Television (Living Room)"),
            profile=Profile.objects.get(pk=39),
            request_time=self.midnight + timezone.timedelta(hours=8, minutes=15)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Vacuum Cleaner"),
            profile=Profile.objects.get(pk=12),
            request_time=self.midnight + timezone.timedelta(hours=10, minutes=0)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Television (Living Room)"),
            profile=Profile.objects.get(pk=20),
            request_time=self.midnight + timezone.timedelta(hours=13, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Microwave"),
            profile=Profile.objects.get(pk=36),
            request_time=self.midnight + timezone.timedelta(hours=13, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=self.midnight + timezone.timedelta(hours=13, minutes=50)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Dishwasher"),
            profile=Profile.objects.get(pk=8),
            request_time=self.midnight + timezone.timedelta(hours=14, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Washing Machine"),
            profile=Profile.objects.get(pk=34),
            request_time=self.midnight + timezone.timedelta(hours=14, minutes=20)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=self.midnight + timezone.timedelta(hours=17, minutes=15)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Soundbar (Bedroom)"),
            profile=Profile.objects.get(pk=31),
            request_time=self.midnight + timezone.timedelta(hours=17, minutes=40)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Electric Vehicle"),
            profile=Profile.objects.get(pk=21),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Cake Mixer"),
            profile=Profile.objects.get(pk=32),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=7)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Oven"),
            profile=Profile.objects.get(pk=4),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=15),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=30)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=40)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Microwave"),
            profile=Profile.objects.get(pk=1),
            request_time=self.midnight + timezone.timedelta(hours=18, minutes=55)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            profile=Profile.objects.get(pk=24),
            request_time=self.midnight + timezone.timedelta(hours=19, minutes=3)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Gaming Computer"),
            profile=Profile.objects.get(pk=30),
            request_time=self.midnight + timezone.timedelta(hours=21, minutes=28)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Clothes Dryer"),
            profile=Profile.objects.get(pk=40),
            request_time=self.midnight + timezone.timedelta(hours=21, minutes=30)
        ))

    def test_scenario_baseline_house_3(self):
        home = Home.objects.get(pk=3)
        home.set_consumption_threshold(12000)
        Profile.objects.all().update(schedulability=NONINTERRUPTIBLE, priority=NORMAL)
        home.batterystoragesystem.delete()
        self.title = "Baseline consumption for household 3"

        coordinator.ext.create_battery_execution(
            home,
            self.midnight + timezone.timedelta(hours=10),
            self.midnight + timezone.timedelta(hours=14),
            4500
        )
        coordinator.ext.create_battery_execution(
            home,
            self.midnight + timezone.timedelta(hours=18),
            self.midnight + timezone.timedelta(hours=26),
            -2250
        )
        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    def test_scenario_baseline_house_3_no_bss(self):
        home = Home.objects.get(pk=3)
        home.set_consumption_threshold(12000)
        Profile.objects.all().update(schedulability=NONINTERRUPTIBLE, priority=NORMAL)
        home.batterystoragesystem.delete()
        self.title = "Baseline consumption for household 3 (no BSS)"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('managed')
    def test_scenario_scheduled_single_house_3(self):
        self.title = 'Managed consumption for household 3'
        home = Home.objects.get(pk=3)
        coordinator.ext.schedule_battery_charge(home, self.midnight + timezone.timedelta(hours=5), True)

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    def tearDown(self):
        home = Home.objects.get(pk=3)
        myFmt = mdates.DateFormatter('%H:%M')
        morning_before = self.midnight + timezone.timedelta(days=0, hours=6)
        morning_after = self.midnight + timezone.timedelta(days=1, hours=6)
        battery_left = coordinator.ext.get_battery_energy(home, morning_after)
        reference_times = coordinator.get_consumption_reference_times_within(home, morning_before, morning_after)
        x = np.array([get_np_time(time) for time in reference_times])
        y = np.array([coordinator.get_power_consumption(home, time) for time in reference_times])
        y_prod = np.array([coordinator.ext.get_power_production(home, time) for time in reference_times])
        y_sub = np.array([coordinator.get_power_consumption(home, time) - coordinator.ext.get_power_production(home, time) for time in reference_times])
        _, ax = plt.subplots(constrained_layout=True)
        ax.step(x, y, where='post')
        ax.step(x, y_prod, where='post', color='r')
        ax.set_title(self.title)
        ax.set_xlabel('Time (hh:mm)')
        ax.set_ylabel('Consumption (W)')
        ax.xaxis.set_major_formatter(myFmt)
        ax.xaxis.set_tick_params(rotation=40)

        executions = coordinator.get_unfinished_executions(home, morning_before)
        delay_to_max = [(e.start_time - e.request_time).seconds / e.appliance.maximum_delay.seconds for e in executions]
        weights = []
        for i in range(0, len(reference_times) - 1):
            time = (reference_times[i+1] - reference_times[i]).seconds
            weights.append(time)

        peak = np.amax(y_sub)
        average = np.average(y[0:-1], weights=weights)
        max_delay_to_max = np.average(delay_to_max)
        print(f"Peak: {peak}\nAverage: {average}\nPAR: {peak/average}\nAverage DAWR: {max_delay_to_max}\n")
        # Battery left(%): {battery_left/home.batterystoragesystem.total_energy_capacity
        plt.show()

def get_np_num(time):
    return mdates.date2num(timezone.make_naive(time))

def get_np_time(time):
    return mdates.num2date(mdates.date2num(timezone.make_naive(time)))

