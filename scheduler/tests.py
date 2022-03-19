from django.test import TestCase, tag

from scheduler.settings import IMMEDIATE, INF_DATE, INTERRUPTIBLE, LOW_PRIORITY, NONINTERRUPTIBLE, NORMAL, PEAK_SHAVING
from .models import AppVals, BatteryStorageSystem, Execution, Appliance, PhotovoltaicSystem, ProductionData, Profile
import processor.test_core as core
import processor.test_external_energy as ext
from django.utils import timezone
import time

# Create your tests here.

""" Test the priority formula by simulating executions created at different moments in the past. """
class PriorityTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core 
        p1 = Profile.objects.create(name="Low priority profile", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, maximum_delay=timezone.timedelta(seconds=43200), rated_power=0)
        p2 = Profile.objects.create(name="Normal priority profile", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=timezone.timedelta(seconds=3600), rated_power=0)
        p3 = Profile.objects.create(name="Immediate priority profile", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, maximum_delay=timezone.timedelta(seconds=900), rated_power=0)
        p4 = Profile.objects.create(name="Infinite delay normal priority profile", schedulability=NONINTERRUPTIBLE, priority=NORMAL, maximum_delay=None, rated_power=0)
        a1 = Appliance.objects.create(name="Test")
        a1.profiles.set([p1, p2, p3, p4])
        a1.save()

    def test_low_priority_calculation(self):
        rt1 = timezone.now() # 12 hours remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=21600) # 6 hours remaining 
        rt3 = timezone.now()-timezone.timedelta(seconds=32400) # 3 hours remaining
        rt4 = timezone.now()-timezone.timedelta(seconds=39600) # 1 hour remaining
        rt5 = timezone.now()-timezone.timedelta(seconds=41400) # 15 minutes remaining 
        rt6 = timezone.now()-timezone.timedelta(seconds=43190) # 10 seconds remaining 
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=1))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=1)) 
        e4 = Execution.objects.create(request_time=rt4,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=1)) 
        e5 = Execution.objects.create(request_time=rt5,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=1)) 
        e6 = Execution.objects.create(request_time=rt6,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=1)) 
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1), 1) # expected priority: 1
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2), 2) # expected priority: 2
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3), 3) # expected priority: 3
        self.assertEqual(self.scheduler.calculate_weighted_priority(e4), 5) # expected priority: 5
        self.assertEqual(self.scheduler.calculate_weighted_priority(e5), 6) # expected priority: 6
        self.assertEqual(self.scheduler.calculate_weighted_priority(e6), 8) # expected priority: 8

    def test_normal_priority_calculation(self):
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=3550) # 10 seconds remaining 
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))       
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1), 7) # expected priority: 7
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2), 9) # expected priority: 9
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3), 10) # expected priority: 10

    def test_immediate_priority_calculation(self):
        rt1 = timezone.now() # 15 minutes remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=600) # 5 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=890) # 10 seconds remaining 
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=3))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=3))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=3))      
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1), 10) # expected priority: 10
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2), 10) # expected priority: 10
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3), 10) # expected priority: 10

    def test_get_lower_priority_shiftable_executions(self):
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e1) # Interruptible, priority: 7
        self.scheduler.schedule_execution(e2) # Interruptible, priority: 9
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 0, 4)), 0)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 0, 7)), 0)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 0, 9)), 1)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 0, 10)), 2)

    def test_infinite_execution_priority_calculation(self):
        rt1 = timezone.now()
        rt2 = timezone.now()-timezone.timedelta(seconds=3600)
        rt3 = timezone.now()-timezone.timedelta(seconds=14400)
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=4))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=4))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=4))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1), 3) # expected priority: 3
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2), 3) # expected priority: 3
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3), 3) # expected priority: 3

""" Test execution lifecycle """
class LifecycleTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, rated_power=2000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=3))
        a1.profiles.set([p1])

        p2 = Profile.objects.create(name="Test 2", schedulability=NONINTERRUPTIBLE, priority=NORMAL, rated_power=6000)
        a2 = Appliance.objects.create(name="Test 2")
        a2.profiles.set([p2])
        a2.save()

    def test_execution_creation(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.assertEqual(Execution.objects.get(pk=1), e1)

    def test_execution_simple_scheduling(self):
        e = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        status = self.scheduler.schedule_execution(e)
        e = Execution.objects.get(pk=1)
        self.assertEqual(status, 1)
        self.assertEqual(e.status(), "Started")

    def test_infinite_execution_simple_scheduling(self):
        e = Execution.objects.create(appliance=Appliance.objects.last(),profile=Profile.objects.last())
        status = self.scheduler.schedule_execution(e)
        e = Execution.objects.get(pk=1)
        self.assertEqual(status, 1)
        self.assertEqual(e.status(), "Started")
        self.assertEqual(e.end_time, INF_DATE)

    def test_multiple_repeated_execution_simple_scheduling(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e2 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e3 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e4 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        status1 = self.scheduler.schedule_execution(e1)
        status2 = self.scheduler.schedule_execution(e2)
        status3 = self.scheduler.schedule_execution(e3)
        status4 = self.scheduler.schedule_execution(e4)  
        e1 = Execution.objects.get(pk=1)
        e2 = Execution.objects.get(pk=2)
        e3 = Execution.objects.get(pk=3)       
        e4 = Execution.objects.get(pk=4)
        self.assertEqual(status1, 1)
        self.assertEqual(status2, 1)
        self.assertEqual(status3, 1)
        self.assertEqual(status4, 1)
        self.assertEqual(e1.status(), "Started")
        self.assertEqual(e2.status(), "Started")
        self.assertEqual(e3.status(), "Started")
        self.assertEqual(e4.status(), "Started")

    @tag('slow')
    def test_execution_finish(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.scheduler.schedule_execution(e1)
        time.sleep(2)
        self.scheduler.finish_execution(e1)
        e1 = Execution.objects.get(pk=1)
        e1_time = e1.end_time - e1.start_time 
        self.assertEqual(e1.status(), "Finished")
        self.assertEqual(e1_time.seconds, 2)        

    @tag('slow')
    def test_execution_interrupt(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.scheduler.schedule_execution(e1)
        time.sleep(2)
        self.scheduler.interrupt_execution(e1)
        e1 = Execution.objects.get(pk=1)
        e1_time = e1.end_time - e1.start_time 
        self.assertEqual(e1.status(), "Interrupted")
        self.assertEqual(e1_time.seconds, 2)        

class FullSchedulingTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=None, rated_power=2000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a1.profiles.set([p1])
        a1.save()        
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, maximum_delay=None, rated_power=400)
        a2 = Appliance.objects.create(name="Test 2", maximum_duration_of_usage=timezone.timedelta(seconds=300))
        a2.profiles.set([p2])
        a2.save() 
        p3 = Profile.objects.create(name="Test 3", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, maximum_delay=timezone.timedelta(seconds=7000), rated_power=2000)
        a3 = Appliance.objects.create(name="Test 3", maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a3.profiles.set([p3])
        a3.save() 

        # Fill whole schedule (assuming 8000W threshold)
        e1 = Execution.objects.create(appliance=a1,profile=p1)
        e2 = Execution.objects.create(appliance=a1,profile=p1)
        e3 = Execution.objects.create(appliance=a1,profile=p1)
        e4 = Execution.objects.create(appliance=a1,profile=p1)
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)

    """
    e5 should have higher priority than e1-e4, and thus, displace e1 with shift_executions.
    """
    def test_shift_executions(self):
        e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        e6 = Execution.objects.get(pk=6)
        self.assertEqual(status5, 2)  
        self.assertEqual(e1.status(), "Interrupted")
        self.assertEqual(e5.status(), "Started")
        self.assertEqual(e6.status(), "Pending")
        self.assertGreaterEqual(e5.start_time, e1.end_time)
        self.assertGreaterEqual(e6.start_time, e5.end_time)

    """
    e5 should have same priority as e1-e4, and thus, be scheduled later with schedule_later.
    """
    def test_schedule_later(self):
        e5 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        self.assertEqual(status5, 3)  
        self.assertEqual(e1.status(), "Started")
        self.assertEqual(e5.status(), "Pending")
        self.assertGreaterEqual(e5.start_time, e1.end_time)

    def test_schedule_after_maximum_delay(self):
        e5 = Execution.objects.create(appliance=Appliance.objects.last(),profile=Profile.objects.last())
        status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        self.assertEqual(status5, 4)  
        self.assertEqual(e1.status(), "Started")
        self.assertEqual(e5.status(), "Pending")

    @tag('slow')
    def test_previous_progress_time(self):
        time.sleep(2)
        e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e6 = Execution.objects.get(pk=6)
        self.assertGreater(e6.previous_progress_time.seconds, 0)
        self.assertEqual((e1.end_time - e1.start_time).seconds, e6.previous_progress_time.seconds)

class ComplexSchedulingTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        p1 = Profile.objects.create(name="Test 1", schedulability=NONINTERRUPTIBLE, priority=NORMAL,
            maximum_delay=None, rated_power=4000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a1.profiles.set([p1])
        a1.save()
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=NORMAL,
            maximum_delay=None, rated_power=1600)
        a2 = Appliance.objects.create(name="Test 2", maximum_duration_of_usage=timezone.timedelta(seconds=3600))
        a2.profiles.set([p2])
        a2.save()
        p3 = Profile.objects.create(name="Test 3", schedulability=INTERRUPTIBLE, priority=IMMEDIATE,
            maximum_delay=None, rated_power=400)
        a3 = Appliance.objects.create(name="Test 3", maximum_duration_of_usage=timezone.timedelta(seconds=300))
        a3.profiles.set([p3])
        a3.save()
        p4 = Profile.objects.create(name="Test 4", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY,
            maximum_delay=None, rated_power=2000)
        a4 = Appliance.objects.create(name="Test 4", maximum_duration_of_usage=timezone.timedelta(seconds=3000))
        a4.profiles.set([p4])
        a4.save()
        p5 = Profile.objects.create(name="Test 5", schedulability=NONINTERRUPTIBLE, priority=NORMAL,
            maximum_delay=None, rated_power=6000)
        a5 = Appliance.objects.create(name="Test 5", maximum_duration_of_usage=None)
        a5.profiles.set([p5])
        a5.save()

    def test_simple_scheduling(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        status1 = self.scheduler.schedule_execution(e1)
        status2 = self.scheduler.schedule_execution(e2)
        status3 = self.scheduler.schedule_execution(e3)
        status4 = self.scheduler.schedule_execution(e4)
        self.assertEqual(status1, 1)
        self.assertEqual(status2, 1)
        self.assertEqual(status3, 1)
        self.assertEqual(status4, 1)
    
    def test_shift_noninterruptible_executions(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        status1 = self.scheduler.schedule_execution(e1)
        status2 = self.scheduler.schedule_execution(e2)
        self.assertEqual(status1, 1)
        self.assertEqual(status2, 1)
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        status3 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status3, 3)
  
    def test_shift_executions(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)
        e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        status5 = self.scheduler.schedule_execution(e5)
        self.assertEqual(status5, 2)
        e4 = Execution.objects.get(pk=4)
        e5 = Execution.objects.get(pk=5)
        e6 = Execution.objects.get(pk=6)
        self.assertEqual(e4.status(), "Interrupted")
        self.assertEqual(e5.status(), "Started")
        self.assertEqual(e6.status(), "Pending")

    def test_schedule_later(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)
        e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        status5 = self.scheduler.schedule_execution(e5)
        self.assertEqual(status5, 3)
        self.assertEqual(e5.status(), "Pending")

    def test_infinite_execution_schedule_later(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=5))
        status3 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status3, 3)

    def test_infinite_execution_shift_non_interruptible_executions(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=5))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=5))
        status3 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status3, 4)

    def test_schedule_after_infinite_execution(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=5))
        self.scheduler.schedule_execution(e1)
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=5),profile=Profile.objects.get(pk=5))
        status2 = self.scheduler.schedule_execution(e2)
        self.assertEqual(status2, 4)

    def test_anticipate_pending_executions(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e4 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e5 = Execution.objects.create(appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e6 = Execution.objects.create(appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e7 = Execution.objects.create(appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)
        self.scheduler.schedule_execution(e5)
        self.scheduler.schedule_execution(e6)
        self.scheduler.schedule_execution(e7)
        self.scheduler.finish_execution(e1)
        e1 = Execution.objects.get(pk=1)
        e3 = Execution.objects.get(pk=3)
        e4 = Execution.objects.get(pk=4)
        e5 = Execution.objects.get(pk=5)
        e6 = Execution.objects.get(pk=6)
        e7 = Execution.objects.get(pk=7)
        self.assertEqual(e1.status(), "Finished")
        self.assertEqual(e3.status(), "Started")
        self.assertEqual(e4.status(), "Started")
        self.assertEqual(e5.status(), "Started")
        self.assertEqual(e6.status(), "Started")
        self.assertEqual(e7.status(), "Pending")

    def test_anticipate_high_priority_executions(self):
        pass

class BSSystemTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core

        BatteryStorageSystem.objects.create(total_energy_capacity=18000, continuous_power=5500)
        p1 = Profile.objects.create(name="Test 1", schedulability=NONINTERRUPTIBLE, priority=NORMAL, maximum_delay=None, rated_power=3600)
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=None, rated_power=2000)
        p3 = Profile.objects.create(name="Test 3", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=None, rated_power=4000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=7200)
        a2 = Appliance.objects.create(name="Test 2", maximum_duration_of_usage=3600)
        a1.profiles.set([p1, p2, p3])
        a2.profiles.set([p1, p2, p3])
        a1.save()
        a2.save()

    def test_bss_appliance_exists(self):
        battery = BatteryStorageSystem.get_system()
        self.assertIsNotNone(battery)
        appliance = battery.appliance
        self.assertIsNotNone(appliance)

    def test_schedule_battery_discharge(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(appliance=Appliance.objects.get(pk=2), profile=Profile.objects.get(pk=3))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        # self.assertTrue()

    def test_schedule_battery_charge(self):
        # drain battery first
        pass

    def test_schedule_battery_charge_at_full(self):
        pass

class PVSystemTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        PhotovoltaicSystem.objects.create(latitude=38.762, longitude=-9.155, tilt=20, azimut=180, capacity=6400)
        exec(open("scripts/load_solar_data.py").read())

    def test_load_solar_data(self):
        self.assertTrue(ProductionData.objects.all())

    