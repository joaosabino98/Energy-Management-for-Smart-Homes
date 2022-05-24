from django.test import TestCase, tag
from home.settings import INF_DATE
from scheduler.settings import INTERRUPTIBLE, LOW_PRIORITY, NONINTERRUPTIBLE, NORMAL, PEAK_SHAVING, URGENT
from .models import Home, BatteryStorageSystem, Execution, Appliance, PhotovoltaicSystem, ProductionData, Profile
import processor.test.core as core
import processor.test.external_energy as ext
from django.utils import timezone
import time

# Create your tests here.

""" Test the priority formula by simulating executions created at different moments in the past. """
class PriorityTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core 
        core.set_id(1)
        p1 = Profile.objects.create(name="Low priority profile", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, rated_power=0)
        p2 = Profile.objects.create(name="Normal priority profile", schedulability=INTERRUPTIBLE, priority=NORMAL, rated_power=0)
        p3 = Profile.objects.create(name="Immediate priority profile", schedulability=INTERRUPTIBLE, priority=URGENT, rated_power=0)
        p4 = Profile.objects.create(name="Infinite delay normal priority profile", schedulability=NONINTERRUPTIBLE, priority=NORMAL, rated_power=0)
        a1 = Appliance.objects.create(home=self.h1, name="Low priority appliance", maximum_delay=timezone.timedelta(seconds=43200))
        a2 = Appliance.objects.create(home=self.h1, name="Normal priority appliance", maximum_delay=timezone.timedelta(seconds=3600))
        a3 = Appliance.objects.create(home=self.h1, name="Immediate priority appliance", maximum_delay=timezone.timedelta(seconds=900))
        a4 = Appliance.objects.create(home=self.h1, name="Infinite delay normal priority appliance", maximum_delay=None)
        a1.profiles.set([p1])
        a2.profiles.set([p2])
        a3.profiles.set([p3])
        a4.profiles.set([p4])
        a1.save()
        a2.save()
        a3.save()
        a4.save()

    def test_low_priority_calculation(self):
        rt1 = timezone.now() # 12 hours remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=21600) # 6 hours remaining 
        rt3 = timezone.now()-timezone.timedelta(seconds=32400) # 3 hours remaining
        rt4 = timezone.now()-timezone.timedelta(seconds=39600) # 1 hour remaining
        rt5 = timezone.now()-timezone.timedelta(seconds=41400) # 15 minutes remaining 
        rt6 = timezone.now()-timezone.timedelta(seconds=43190) # 10 seconds remaining 
        e1 = Execution.objects.create(home=self.h1, request_time=rt1,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, request_time=rt2,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e3 = Execution.objects.create(home=self.h1, request_time=rt3,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1)) 
        e4 = Execution.objects.create(home=self.h1, request_time=rt4,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1)) 
        e5 = Execution.objects.create(home=self.h1, request_time=rt5,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1)) 
        e6 = Execution.objects.create(home=self.h1, request_time=rt6,appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1)) 
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1, rt1), 1) # expected priority: 1
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2, rt1), 2) # expected priority: 2
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3, rt1), 3) # expected priority: 3
        self.assertEqual(self.scheduler.calculate_weighted_priority(e4, rt1), 5) # expected priority: 5
        self.assertEqual(self.scheduler.calculate_weighted_priority(e5, rt1), 6) # expected priority: 6
        self.assertEqual(self.scheduler.calculate_weighted_priority(e6, rt1), 8) # expected priority: 8

    def test_normal_priority_calculation(self):
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=3550) # 10 seconds remaining 
        e1 = Execution.objects.create(home=self.h1, request_time=rt1,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(home=self.h1, request_time=rt2,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(home=self.h1, request_time=rt3,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))       
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1, rt1), 7) # expected priority: 7
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2, rt1), 9) # expected priority: 9
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3, rt1), 10) # expected priority: 10

    def test_immediate_priority_calculation(self):
        rt1 = timezone.now() # 15 minutes remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=600) # 5 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=890) # 10 seconds remaining 
        e1 = Execution.objects.create(home=self.h1,request_time=rt1,appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e2 = Execution.objects.create(home=self.h1,request_time=rt2,appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e3 = Execution.objects.create(home=self.h1,request_time=rt3,appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))      
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1, rt1), 10) # expected priority: 10
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2, rt1), 10) # expected priority: 10
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3, rt1), 10) # expected priority: 10

    def test_get_lower_priority_shiftable_executions(self):
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        e1 = Execution.objects.create(home=self.h1,request_time=rt1,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(home=self.h1,request_time=rt2,appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e1, rt1) # Interruptible, priority: 7
        self.scheduler.schedule_execution(e2, rt1) # Interruptible, priority: 9
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 4)), 0)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 7)), 0)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 9)), 1)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions_within(rt2, rt2 + timezone.timedelta(hours=3), 10)), 2)

    def test_infinite_execution_priority_calculation(self):
        rt1 = timezone.now()
        rt2 = timezone.now()-timezone.timedelta(seconds=3600)
        rt3 = timezone.now()-timezone.timedelta(seconds=14400)
        e1 = Execution.objects.create(home=self.h1, request_time=rt1,appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        e2 = Execution.objects.create(home=self.h1, request_time=rt2,appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        e3 = Execution.objects.create(home=self.h1, request_time=rt3,appliance=Appliance.objects.get(pk=4),profile=Profile.objects.get(pk=4))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1, rt1), 3) # expected priority: 3
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2, rt1), 3) # expected priority: 3
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3, rt1), 3) # expected priority: 3

""" Test execution lifecycle """
class LifecycleTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        core.set_id(1)
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=URGENT, rated_power=2000, maximum_duration_of_usage=timezone.timedelta(seconds=3))
        p2 = Profile.objects.create(name="Test 2", schedulability=NONINTERRUPTIBLE, priority=NORMAL, rated_power=6000)
        a1 = Appliance.objects.create(home=self.h1, name="Test 1")
        a2 = Appliance.objects.create(home=self.h1, name="Test 2")
        a1.profiles.set([p1])
        a2.profiles.set([p2])
        a1.save()
        a2.save()

    def test_execution_creation(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.assertEqual(Execution.objects.get(pk=1), e1)

    def test_execution_simple_scheduling(self):
        e = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        status = self.scheduler.schedule_execution(e)
        e.refresh_from_db()
        self.assertEqual(status, 0)
        self.assertEqual(e.status(), "Started")

    def test_infinite_execution_simple_scheduling(self):
        e = Execution.objects.create(home=self.h1, appliance=Appliance.objects.last(),profile=Profile.objects.last())
        status = self.scheduler.schedule_execution(e)
        e.refresh_from_db()
        self.assertEqual(status, 0)
        self.assertEqual(e.status(), "Started")
        self.assertEqual(e.end_time, INF_DATE)

    def test_multiple_repeated_execution_simple_scheduling(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e4 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        status1 = self.scheduler.schedule_execution(e1)
        status2 = self.scheduler.schedule_execution(e2)
        status3 = self.scheduler.schedule_execution(e3)
        status4 = self.scheduler.schedule_execution(e4)  
        e1.refresh_from_db()
        e2.refresh_from_db()
        e3.refresh_from_db()      
        e4.refresh_from_db()
        self.assertEqual(status1, 0)
        self.assertEqual(status2, 0)
        self.assertEqual(status3, 0)
        self.assertEqual(status4, 0)
        self.assertEqual(e1.status(), "Started")
        self.assertEqual(e2.status(), "Started")
        self.assertEqual(e3.status(), "Started")
        self.assertEqual(e4.status(), "Started")

    @tag('slow')
    def test_execution_finish(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.scheduler.schedule_execution(e1)
        time.sleep(2)
        self.scheduler.finish_execution(e1)
        e1.refresh_from_db()
        e1_time = e1.end_time - e1.start_time 
        self.assertEqual(e1.status(), "Finished")
        self.assertEqual(e1_time.seconds, 2)        

    @tag('slow')
    def test_execution_interrupt(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.scheduler.schedule_execution(e1)
        time.sleep(2)
        self.scheduler.interrupt_execution(e1)
        e1.refresh_from_db()
        e1_time = e1.end_time - e1.start_time 
        self.assertEqual(e1.status(), "Interrupted")
        self.assertEqual(e1_time.seconds, 2)        

class FullSchedulingTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        core.set_id(1)
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=NORMAL, rated_power=2000, maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=URGENT, rated_power=400, maximum_duration_of_usage=timezone.timedelta(seconds=300))
        p3 = Profile.objects.create(name="Test 3", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, rated_power=2000, maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a1 = Appliance.objects.create(home=self.h1, name="Test 1", maximum_delay=None)
        a2 = Appliance.objects.create(home=self.h1, name="Test 2", maximum_delay=None)
        a3 = Appliance.objects.create(home=self.h1, name="Test 3", maximum_delay=timezone.timedelta(seconds=7000))
        a1.profiles.set([p1])
        a2.profiles.set([p2])
        a3.profiles.set([p3])
        a1.save()        
        a2.save() 
        a3.save() 

        # Fill whole schedule (assuming 8000W threshold)
        e1 = Execution.objects.create(home=self.h1, appliance=a1, profile=p1)
        e2 = Execution.objects.create(home=self.h1, appliance=a1, profile=p1)
        e3 = Execution.objects.create(home=self.h1, appliance=a1, profile=p1)
        e4 = Execution.objects.create(home=self.h1, appliance=a1, profile=p1)
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)

    """
    e5 should have higher priority than e1-e4, and thus, displace e1 with shift_executions.
    """
    def test_shift_executions(self):
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
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
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.first(),profile=Profile.objects.first())
        status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        self.assertEqual(status5, 0)  
        self.assertEqual(e1.status(), "Started")
        self.assertEqual(e5.status(), "Pending")
        self.assertGreaterEqual(e5.start_time, e1.end_time)

    def test_schedule_after_maximum_delay(self):
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.last(),profile=Profile.objects.last())
        status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        self.assertEqual(status5, -1)  
        self.assertEqual(e1.status(), "Started")
        self.assertEqual(e5.status(), "Pending")

    @tag('slow')
    def test_previous_progress_time(self):
        time.sleep(2)
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e6 = Execution.objects.get(pk=6)
        self.assertGreater(e6.previous_progress_time.seconds, 0)
        self.assertEqual((e1.end_time - e1.start_time).seconds, e6.previous_progress_time.seconds)

class ComplexSchedulingTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        core.set_id(1)
        p1 = Profile.objects.create(name="Test 1", schedulability=NONINTERRUPTIBLE, priority=NORMAL,
            maximum_duration_of_usage=timezone.timedelta(seconds=7200), rated_power=4000)
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=NORMAL,
            maximum_duration_of_usage=timezone.timedelta(seconds=3600), rated_power=1600)
        p3 = Profile.objects.create(name="Test 3", schedulability=INTERRUPTIBLE, priority=URGENT,
            maximum_duration_of_usage=timezone.timedelta(seconds=300), rated_power=400)
        p4 = Profile.objects.create(name="Test 4", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY,
            maximum_duration_of_usage=timezone.timedelta(seconds=3000), rated_power=2000)
        p5 = Profile.objects.create(name="Test 5", schedulability=NONINTERRUPTIBLE, priority=NORMAL,
            maximum_duration_of_usage=None, rated_power=6000)
        p6 = Profile.objects.create(name="Test 6", schedulability=INTERRUPTIBLE, priority=NORMAL,
            maximum_duration_of_usage=timezone.timedelta(seconds=3000), rated_power=2000)
        a1 = Appliance.objects.create(home=self.h1, name="Test 1", maximum_delay=None)
        a2 = Appliance.objects.create(home=self.h1, name="Test 2", maximum_delay=timezone.timedelta(seconds=3600))
        a3 = Appliance.objects.create(home=self.h1, name="Test 3", maximum_delay=timezone.timedelta(seconds=9600))
        a1.profiles.set([p1, p2, p3, p4, p5, p6])
        a2.profiles.set([p1, p2, p3, p4, p5, p6])
        a3.profiles.set([p1, p2, p3, p4, p5, p6])
        a1.save()
        a2.save()
        a3.save()

    def test_simple_scheduling(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=3))
        e4 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=4))
        status1 = self.scheduler.schedule_execution(e1)
        status2 = self.scheduler.schedule_execution(e2)
        status3 = self.scheduler.schedule_execution(e3)
        status4 = self.scheduler.schedule_execution(e4)
        self.assertEqual(status1, 0)
        self.assertEqual(status2, 0)
        self.assertEqual(status3, 0)
        self.assertEqual(status4, 0)
    
    def test_shift_noninterruptible_executions(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        status1 = self.scheduler.schedule_execution(e1)
        status2 = self.scheduler.schedule_execution(e2)
        self.assertEqual(status1, 0)
        self.assertEqual(status2, 0)
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=3))
        status3 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status3, -1)
  
    def test_shift_executions(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=3))
        e4 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=6))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=6))
        status5 = self.scheduler.schedule_execution(e5)
        self.assertEqual(status5, 2)
        e4.refresh_from_db()
        e5.refresh_from_db()
        e6 = Execution.objects.get(pk=6)
        self.assertEqual(e4.status(), "Interrupted")
        self.assertEqual(e5.status(), "Started")
        self.assertEqual(e6.status(), "Pending")

    def test_schedule_before_low_priority(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=3))
        e4 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=4))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=3))
        status5 = self.scheduler.schedule_execution(e5)
        self.assertEqual(status5, 0)
        e4.refresh_from_db()
        e5.refresh_from_db()
        self.assertEqual(e4.status(), "Pending")
        self.assertEqual(e5.status(), "Started")

    def test_schedule_later(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=6))
        status5 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status5, 0)
        self.assertEqual(e3.status(), "Pending")

    def test_infinite_execution_schedule_later(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=5))
        status3 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status3, 0)
        self.assertEqual(e3.status(), "Pending")

    def test_infinite_execution_shift_non_interruptible_executions(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=2),profile=Profile.objects.get(pk=6))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=5))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=5))
        status3 = self.scheduler.schedule_execution(e3)
        self.assertEqual(status3, -1)

    def test_schedule_after_infinite_execution(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=5))
        self.scheduler.schedule_execution(e1)
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=5))
        status2 = self.scheduler.schedule_execution(e2)
        self.assertEqual(status2, -1)

    def test_anticipate_pending_executions(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=1))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e3 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=2))
        e4 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e5 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=2))
        e6 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=3),profile=Profile.objects.get(pk=3))
        e7 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1),profile=Profile.objects.get(pk=6))
        self.scheduler.schedule_execution(e3)
        self.scheduler.schedule_execution(e4)
        self.scheduler.schedule_execution(e5)
        self.scheduler.schedule_execution(e6)
        self.scheduler.schedule_execution(e7)
        self.scheduler.finish_execution(e1)
        e1.refresh_from_db()
        e3.refresh_from_db()
        e4.refresh_from_db()
        e5.refresh_from_db()
        e6.refresh_from_db()
        e7.refresh_from_db()
        self.assertEqual(e1.status(), "Finished")
        self.assertEqual(e3.status(), "Started")
        self.assertEqual(e4.status(), "Started")
        self.assertEqual(e5.status(), "Started")
        self.assertEqual(e6.status(), "Started")
        self.assertEqual(e7.status(), "Pending")

class BSSystemTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        core.set_id(1)
        p1 = Profile.objects.create(name="Test 1", schedulability=NONINTERRUPTIBLE, priority=NORMAL, maximum_duration_of_usage=timezone.timedelta(seconds=7200), rated_power=3600)
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_duration_of_usage=timezone.timedelta(seconds=3600), rated_power=4000)
        a1 = Appliance.objects.create(home=self.h1, name="Test 1", maximum_delay=None)
        a1.profiles.set([p1, p2])
        a1.save()
        BatteryStorageSystem.objects.create(home=self.h1, total_energy_capacity=18000, continuous_power=5500, last_full_charge_time=timezone.now() - timezone.timedelta(days=1))

    def test_bss_appliance_exists(self):
        battery = self.h1.batterystoragesystem
        self.assertIsNotNone(battery)
        appliance = battery.appliance
        self.assertIsNotNone(appliance)

    def test_schedule_battery_discharge_on_high_demand(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        e1.refresh_from_db()
        e2.refresh_from_db()
        e3 = ext.get_last_battery_execution()
        self.assertNotEqual(e3, Execution.objects.none())
        self.assertEqual(e3.profile.name, "BSS 2000W Discharge")
        self.assertEqual(e3.profile.rated_power, -2000)
        self.assertLess(ext.get_battery_energy(e2.end_time), ext.get_battery_energy(timezone.now()))
        self.assertEqual(ext.get_battery_energy(e2.end_time), ext.get_battery_energy(e1.end_time))

    def test_schedule_battery_charge(self):
        battery = self.h1.batterystoragesystem
        start_time = timezone.now() - timezone.timedelta(hours=4)
        end_time = timezone.now()
        e1 = ext.create_battery_execution(start_time, end_time, -4500)  
        ext.schedule_battery_charge()
        e2 = ext.get_last_battery_execution()
        self.assertLessEqual(ext.get_battery_energy(e1.end_time), battery.total_energy_capacity * 0.01)
        self.assertGreaterEqual(ext.get_battery_energy(e2.end_time), battery.total_energy_capacity * 0.99)

    def test_schedule_battery_charge_at_full(self):
        battery = self.h1.batterystoragesystem
        start_time = timezone.now()
        ext.schedule_battery_charge()
        e2 = ext.get_last_battery_execution()
        self.assertIsNone(e2)
        self.assertEqual(ext.get_maximum_possible_battery_energy_discharge(start_time), battery.total_energy_capacity)

    def test_schedule_battery_charge_with_busy_schedule(self):
        battery = self.h1.batterystoragesystem
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        ext.schedule_battery_charge(ext.get_last_battery_execution().end_time)
        self.assertEqual(ext.get_battery_energy(e2.end_time), 16000)
        self.assertGreaterEqual(ext.get_battery_energy(ext.get_last_battery_execution().end_time), battery.total_energy_capacity * 0.99)

    def test_schedule_battery_charge_before_discharge(self):
        e1 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=1))
        e2 = Execution.objects.create(home=self.h1, appliance=Appliance.objects.get(pk=1), profile=Profile.objects.get(pk=2))
        self.scheduler.schedule_execution(e1)
        self.scheduler.schedule_execution(e2)
        ext.schedule_battery_charge()
        self.assertEqual(ext.get_battery_energy(e2.end_time), ext.get_battery_energy(ext.get_last_battery_execution().end_time))

    def test_consecutive_schedule_battery_charge(self):
        start_time = timezone.now() - timezone.timedelta(hours=4)
        end_time = timezone.now()
        e1 = ext.create_battery_execution(start_time, end_time, -4500)
        ext.schedule_battery_charge()
        e2 = ext.get_last_battery_execution()
        ext.schedule_battery_charge(e2.end_time)
        e3 = ext.get_last_battery_execution()
        self.assertEqual(e2, e3)
        self.assertEqual(ext.get_battery_energy(e2.end_time), ext.get_battery_energy(e3.end_time))

class PVSystemTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.scheduler = core
        core.set_id(1)
        PhotovoltaicSystem.objects.create(home=self.h1, latitude=38.762, longitude=-9.155, tilt=20, azimut=180, capacity=6400)
        exec(open("scripts/load_solar_data.py").read())

    def test_load_solar_data(self):
        self.assertTrue(ProductionData.objects.all())

    def test_battery_charge_on_solar_march(self):
        march_day = timezone.now().replace(month=3, day=21, hour=0, minute=0, second=0, microsecond=0)
        start_time = march_day - timezone.timedelta(hours=4)
        end_time = march_day
        day_before = march_day - timezone.timedelta(days=1)
        day_after = march_day + timezone.timedelta(days=1)
        BatteryStorageSystem.objects.create(home=self.h1, total_energy_capacity=18000, continuous_power=5500, last_full_charge_time=day_before)
        e1 = ext.create_battery_execution(start_time, end_time, -4500)
        ext.schedule_battery_charge(day_after)
        for execution in ext.get_battery_charge_within(day_after, None):
            self.assertLessEqual(execution.profile.rated_power, ext.get_power_production(execution.start_time))
        
    def test_battery_charge_on_solar_december(self):
        december_day = timezone.now().replace(month=12, day=21, hour=0, minute=0, second=0, microsecond=0)
        start_time = december_day - timezone.timedelta(hours=4)
        end_time = december_day
        day_before = december_day - timezone.timedelta(days=1)
        day_after = december_day + timezone.timedelta(days=1)
        BatteryStorageSystem.objects.create(home=self.h1, total_energy_capacity=18000, continuous_power=5500, last_full_charge_time=day_before)
        e1 = ext.create_battery_execution(start_time, end_time, -4500)
        ext.schedule_battery_charge(day_after)
        for execution in ext.get_battery_charge_within(day_after, None):
            self.assertGreaterEqual(execution.profile.rated_power, ext.get_power_production(execution.start_time))   

class ComplexBSSystemTestCase(TestCase):
    pass     

@tag('aggregator')
class MultihouseSystemTestCase(TestCase):
    def setUp(self):
        self.h1 = Home.objects.create(consumption_threshold=8000, strategy=PEAK_SHAVING, is_running=False)
        self.p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=URGENT, maximum_duration_of_usage=timezone.timedelta(seconds=3), rated_power=2000)
        self.a1 = Appliance.objects.create(home=self.h1, name="Test 1")
        self.a1.profiles.set([self.p1])
        self.scheduler = core
        core.set_id(1)

    def test_connect_to_aggregator_with_recommendations(self):
        self.scheduler.start_aggregator_client()

    def test_connect_to_aggregator_without_recommendations(self):
        self.scheduler.start_aggregator_client()
        self.h1.set_accept_recommendations(False)

    def test_choose_on_empty_data(self):
        self.scheduler.start_aggregator_client()
        e = Execution.objects.create(home=self.h1, appliance=self.a1, profile=self.p1)
        status = self.scheduler.schedule_execution(e)
        e.refresh_from_db()
        self.assertEqual(status, 0)
        self.assertEqual(e.status(), "Started")

    # Test manually: aggregator is not using test database
    def test_choose_on_single_house_data(self):
        pass

    def test_choose_on_multiple_house_data(self):
        pass