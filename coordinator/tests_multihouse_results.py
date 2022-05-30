from django.test import TestCase
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import processor.core as coordinator

from django.test import TestCase, tag
from django.utils import timezone
from coordinator.settings import NONINTERRUPTIBLE, NORMAL
from coordinator.models import Home, Execution, Appliance, Profile

deviation = np.random.normal(0, 60, 6)
print(deviation)

class MultiHouse1TestCase(TestCase):
    fixtures = ['coordinator/fixtures/three_houses_profiles.json', 'coordinator/fixtures/three_houses_data.json']

    def setUp(self):
        self.midnight = midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        home = Home.objects.get(pk=1)
        self.title = ""
        for i in [1, 2, 3]:
            coordinator.start_aggregator_client(Home.objects.get(pk=i), False)
        self.executions = []
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Fridge"),
            profile=Profile.objects.get(pk=6),
            request_time=midnight
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            profile=Profile.objects.get(pk=24),
            request_time=midnight + timezone.timedelta(hours=8, minutes=5)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=midnight + timezone.timedelta(hours=8, minutes=22)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Toaster"),
            profile=Profile.objects.get(pk=27),
            request_time=midnight + timezone.timedelta(hours=8, minutes=24)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Microwave"),
            profile=Profile.objects.get(pk=1),
            request_time=midnight + timezone.timedelta(hours=13, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Television (Living Room)"),
            profile=Profile.objects.get(pk=37),
            request_time=midnight + timezone.timedelta(hours=17, minutes=30)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Vacuum Cleaner"),
            profile=Profile.objects.get(pk=12),
            request_time=midnight + timezone.timedelta(hours=17, minutes=50)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Oven"),
            profile=Profile.objects.get(pk=4),
            request_time=midnight + timezone.timedelta(hours=18, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Dishwasher"),
            profile=Profile.objects.get(pk=7),
            request_time=midnight + timezone.timedelta(hours=22, minutes=20)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Washing Machine"),
            profile=Profile.objects.get(pk=35),
            request_time=midnight + timezone.timedelta(hours=22, minutes=23)
        ))

        home = Home.objects.get(pk=2)
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Fridge"),
            profile=Profile.objects.get(pk=6),
            request_time=midnight
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=midnight + timezone.timedelta(hours=7, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=midnight + timezone.timedelta(hours=7, minutes=34)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Microwave"),
            profile=Profile.objects.get(pk=1),
            request_time=midnight + timezone.timedelta(hours=7, minutes=37)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Water Heater"),
            profile=Profile.objects.get(pk=19),
            request_time=midnight + timezone.timedelta(hours=7, minutes=40)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            profile=Profile.objects.get(pk=25),
            request_time=midnight + timezone.timedelta(hours=8, minutes=0)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Television (Kitchen)"),
            profile=Profile.objects.get(pk=20),
            request_time=midnight + timezone.timedelta(hours=8, minutes=15)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            profile=Profile.objects.get(pk=13),
            request_time=midnight + timezone.timedelta(hours=8, minutes=22)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Washing Machine"),
            profile=Profile.objects.get(pk=10),
            request_time=midnight + timezone.timedelta(hours=9, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=15),
            request_time=midnight + timezone.timedelta(hours=12, minutes=15)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Air Conditioner"),
            profile=Profile.objects.get(pk=5),
            request_time=midnight + timezone.timedelta(hours=14, minutes=00)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Vacuum Cleaner"),
            profile=Profile.objects.get(pk=12),
            request_time=midnight + timezone.timedelta(hours=15, minutes=50)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Oven"),
            profile=Profile.objects.get(pk=4),
            request_time=midnight + timezone.timedelta(hours=19, minutes=10)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Induction Cooker"),
            profile=Profile.objects.get(pk=14),
            request_time=midnight + timezone.timedelta(hours=19, minutes=55)
        ))
        self.executions.append(
            Execution.objects.create(
            home=home,
            appliance=Appliance.objects.get(home=home, name="Dishwasher"),
            profile=Profile.objects.get(pk=7),
            request_time=midnight + timezone.timedelta(hours=22, minutes=00)
        ))

        home = Home.objects.get(pk=3)
        exec(open("scripts/load_solar_data.py").read())
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
        self.executions.sort(key=lambda e: e.request_time)

        coordinator.ext.create_battery_execution(
            home,
            self.midnight + timezone.timedelta(hours=0),
            self.midnight + timezone.timedelta(hours=4),
            -4500
        )

    @tag('unmanaged')
    def test_scenario_unmanaged_1(self):
        for i in [1, 2, 3]:
            home = Home.objects.get(pk=i)
            home.set_consumption_threshold(12000)
            if i == 3:
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

        self.title = "Baseline aggregate consumption for 3 houses"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('singlehouse')
    def test_scenario_singlehouse_managed_1(self):
        home = Home.objects.get(pk=3)
        coordinator.ext.schedule_battery_charge(home, self.midnight + timezone.timedelta(hours=5), True)

        self.title = "Managed aggregate consumption for 3 houses (Single-House Mode)"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('multihouse')
    def test_scenario_multihouse_managed_1(self):
        for i in [1, 2, 3]:
            home = Home.objects.get(pk=i)
            home.set_accept_recommendations(True)
            if i == 3:
                home.set_consumption_threshold(5175)
                coordinator.ext.schedule_battery_charge(home, self.midnight + timezone.timedelta(hours=5), True)

        self.title = "Managed aggregate consumption for 3 houses (Multi-House Mode)"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    def tearDown(self):
        for i in [1, 2, 3]:
            home = Home.objects.get(pk=i)
            executions = coordinator.get_pending_executions(home, self.midnight)
            delay_to_max = [(e.start_time - e.request_time).seconds / e.appliance.maximum_delay.seconds for e in executions]
            max_delay_to_max = np.amax(delay_to_max)
            print(f"DAWR: {max_delay_to_max}")
        coordinator.cli.send_create_plot(self.title)

@tag('household1')
class MultiHouse2TestCase(TestCase):
    fixtures = ['coordinator/fixtures/three_houses_profiles.json', 'coordinator/fixtures/three_houses_repeated_data.json']

    def setUp(self):
        self.midnight = midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(days=1)
        self.executions = []
        self.title = ""
        for i in [1, 2, 3, 4, 5]:
            home = Home.objects.get(pk=i)
            coordinator.start_aggregator_client(Home.objects.get(pk=i), False)
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Fridge"),
            #     profile=Profile.objects.get(pk=6),
            #     request_time=midnight
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Hair Dryer"),
            #     profile=Profile.objects.get(pk=24),
            #     request_time=midnight + timezone.timedelta(hours=8, minutes=5 + deviation[i])
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Coffee Machine"),
            #     profile=Profile.objects.get(pk=13),
            #     request_time=midnight + timezone.timedelta(hours=8, minutes=22 + deviation[i])
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Toaster"),
            #     profile=Profile.objects.get(pk=27),
            #     request_time=midnight + timezone.timedelta(hours=8, minutes=24 + deviation[i])
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Microwave"),
            #     profile=Profile.objects.get(pk=1),
            #     request_time=midnight + timezone.timedelta(hours=13, minutes=10 + deviation[i])
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Television (Living Room)"),
            #     profile=Profile.objects.get(pk=37),
            #     request_time=midnight + timezone.timedelta(hours=17, minutes=30 + deviation[i])
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Vacuum Cleaner"),
            #     profile=Profile.objects.get(pk=12),
            #     request_time=midnight + timezone.timedelta(hours=17, minutes=50 + deviation[i])
            # ))
            # self.executions.append(
            #     Execution.objects.create(
            #     home=home,
            #     appliance=Appliance.objects.get(home=home, name="Oven"),
            #     profile=Profile.objects.get(pk=4),
            #     request_time=midnight + timezone.timedelta(hours=18, minutes=00 + deviation[i])
            # ))
            self.executions.append(
                Execution.objects.create(
                home=home,
                appliance=Appliance.objects.get(home=home, name="Dishwasher"),
                profile=Profile.objects.get(pk=7),
                request_time=midnight + timezone.timedelta(hours=22, minutes=20 + deviation[i])
            ))
            self.executions.append(
                Execution.objects.create(
                home=home,
                appliance=Appliance.objects.get(home=home, name="Washing Machine"),
                profile=Profile.objects.get(pk=35),
                request_time=midnight + timezone.timedelta(hours=22, minutes=23 + deviation[i])
            ))
        self.executions.sort(key=lambda e: e.request_time)

    @tag('unmanaged')
    def test_scenario_unmanaged_1(self):
        for i in [1, 2, 3, 4, 5]:
            home = Home.objects.get(pk=i)
            home.set_consumption_threshold(12000)
        self.title = "Baseline aggregate consumption for 3 houses"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('singlehouse')
    def test_scenario_singlehouse_managed_1(self):
        self.title = "Managed aggregate consumption for 3 houses (Single-House Mode)"
        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    @tag('multihouse')
    def test_scenario_multihouse_managed_1(self):
        for i in [1, 2, 3, 4, 5]:
            home = Home.objects.get(pk=i)
            home.set_accept_recommendations(True)

        self.title = "Managed aggregate consumption for 3 houses (Multi-House Mode)"

        for execution in self.executions:
            execution.refresh_from_db()
            coordinator.schedule_execution(execution, execution.request_time, True)

    def tearDown(self):
        for i in [1, 2, 3, 4, 5]:
            home = Home.objects.get(pk=i)
            executions = coordinator.get_pending_executions(home, self.midnight)
            delay_to_max = [(e.start_time - e.request_time).seconds / e.appliance.maximum_delay.seconds for e in executions]
            max_delay_to_max = np.amax(delay_to_max)
            print(f"DAWR: {max_delay_to_max}")
        coordinator.cli.send_create_plot(self.title)