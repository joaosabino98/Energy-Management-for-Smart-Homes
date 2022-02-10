from django.test import TestCase, tag

from scheduler.settings import IMMEDIATE, INF_DATE, INTERRUPTIBLE, LOW_PRIORITY, NONINTERRUPTIBLE, NORMAL, SIMPLE
from .models import AppVals, Execution, Appliance, Profile
import processor.test_core as core
from django.utils import timezone
import time

# Create your tests here.

""" Test the priority formula by simulating executions created at different moments in the past. """
class PriorityTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=SIMPLE, is_running=False)
        self.scheduler = core 
        p1 = Profile.objects.create(name="Low priority profile", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, maximum_delay=timezone.timedelta(seconds=43200), rated_power=0)
        p2 = Profile.objects.create(name="Normal priority profile", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=timezone.timedelta(seconds=3600), rated_power=0)
        p3 = Profile.objects.create(name="Immediate priority profile", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, maximum_delay=timezone.timedelta(seconds=900), rated_power=0)
        a1 = Appliance.objects.create(name="Test")
        a1.profile.set([p1, p2, p3])
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

""" Test execution lifecycle """
class LifecycleTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=SIMPLE, is_running=False)
        self.scheduler = core
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, rated_power=2000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=3))
        a1.profile.add(p1)

        p2 = Profile.objects.create(name="Test 2", schedulability=NONINTERRUPTIBLE, priority=NORMAL, rated_power=6000)
        a2 = Appliance.objects.create(name="Test 2")
        a2.profile.set([p2])
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
        AppVals.objects.create(consumption_threshold=8000, strategy=SIMPLE, is_running=False)
        self.scheduler = core
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=NORMAL, rated_power=2000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a1.profile.set([p1])
        a1.save()        
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, rated_power=400)
        a2 = Appliance.objects.create(name="Test 2", maximum_duration_of_usage=timezone.timedelta(seconds=300))
        a2.profile.set([p2])
        a2.save() 
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
        e5 = Execution.objects.create(appliance=Appliance.objects.last(),profile=Profile.objects.last())
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

    @tag('slow')
    def test_previous_progress_time(self):
        time.sleep(2)
        e5 = Execution.objects.create(appliance=Appliance.objects.last(),profile=Profile.objects.last())
        self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e6 = Execution.objects.get(pk=6)
        self.assertGreater(e6.previous_progress_time.seconds, 0)
        self.assertEqual((e1.end_time - e1.start_time).seconds, e6.previous_progress_time.seconds)

class ComplexSchedulingTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, strategy=SIMPLE, is_running=False)
        self.scheduler = core
        p1 = Profile.objects.create(name="Test 1", schedulability=NONINTERRUPTIBLE, priority=NORMAL,
            maximum_delay=timezone.timedelta(seconds=3600), rated_power=4000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a1.profile.set([p1])
        a1.save()
        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=NORMAL,
            maximum_delay=timezone.timedelta(seconds=3000), rated_power=1600)
        a2 = Appliance.objects.create(name="Test 2", maximum_duration_of_usage=timezone.timedelta(seconds=3600))
        a2.profile.set([p2])
        a2.save()
        p3 = Profile.objects.create(name="Test 3", schedulability=INTERRUPTIBLE, priority=IMMEDIATE,
            maximum_delay=timezone.timedelta(seconds=300), rated_power=400)
        a3 = Appliance.objects.create(name="Test 3", maximum_duration_of_usage=timezone.timedelta(seconds=300))
        a3.profile.set([p3])
        a3.save()
        p4 = Profile.objects.create(name="Test 4", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY,
            maximum_delay=timezone.timedelta(seconds=14400), rated_power=2000)
        a4 = Appliance.objects.create(name="Test 4", maximum_duration_of_usage=timezone.timedelta(seconds=3000))
        a4.profile.set([p4])
        a4.save()
        p5 = Profile.objects.create(name="Test 5", schedulability=NONINTERRUPTIBLE, priority=NORMAL,
            maximum_delay=timezone.timedelta(seconds=3000), rated_power=6000)
        a5 = Appliance.objects.create(name="Test 5")
        a5.profile.set([p5])
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
        pass

    def test_anticipate_high_priority_executions(self):
        pass

