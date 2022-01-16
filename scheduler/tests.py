from django.test import TestCase, tag

from scheduler.settings import IMMEDIATE, INTERRUPTIBLE, LOW_PRIORITY, NORMAL
from .models import AppVals, Execution, Appliance, Profile
from manager.schedule_core import ScheduleManager
from django.utils import timezone
import time

# Create your tests here.

""" Test the priority formula by simulating executions created at different moments in the past. """
class PriorityTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, is_running=False)
        p1 = Profile.objects.create(name="Low priority profile", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, maximum_delay=timezone.timedelta(seconds=43200), rated_power=0)
        p2 = Profile.objects.create(name="Normal priority profile", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=timezone.timedelta(seconds=3600), rated_power=0)
        p3 = Profile.objects.create(name="Immediate priority profile", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, maximum_delay=timezone.timedelta(seconds=900), rated_power=0)
        a1 = Appliance.objects.create(name="Test")
        a1.profile.set([p1, p2, p3])
        a1.save()
        self.scheduler = ScheduleManager()
        self.scheduler.clean()        

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
        self.assertEqual(self.scheduler.calculate_weighted_priority(e2), 1) # expected priority: 1
        self.assertEqual(self.scheduler.calculate_weighted_priority(e3), 1) # expected priority: 1
        self.assertEqual(self.scheduler.calculate_weighted_priority(e4), 1) # expected priority: 1
        self.assertEqual(self.scheduler.calculate_weighted_priority(e5), 1) # expected priority: 1
        self.assertEqual(self.scheduler.calculate_weighted_priority(e6), 1) # expected priority: 1

    def test_normal_priority_calculation(self):
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=3550) # 10 seconds remaining 
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))        
        self.assertEqual(self.scheduler.calculate_weighted_priority(e1), 5) # expected priority: 5
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
        self.scheduler.schedule_execution(e1) # Interruptible, priority: 5
        self.scheduler.schedule_execution(e2) # Interruptible, priority: 9
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions(4)[0]), 0)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions(7)[0]), 1)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions(9)[0]), 1)
        self.assertEqual(len(self.scheduler.get_lower_priority_shiftable_executions(10)[0]), 2)

""" Test execution lifecycle """
class LifecycleTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, is_running=False)
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, rated_power=2000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=3))
        a1.profile.add(p1)
        self.scheduler = ScheduleManager()
        self.scheduler.clean()

    def test_execution_creation(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.assertEqual(Execution.objects.get(pk=1), e1)

    def test_execution_simple_scheduling(self):
        e = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        success, status = self.scheduler.schedule_execution(e)
        self.assertIn(e, self.scheduler.running)
        self.assertEqual(success, True)
        self.assertEqual(status, 1)

    def test_multiple_execution_simple_scheduling(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e2 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e3 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        e4 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        success1, status1 = self.scheduler.schedule_execution(e1)
        success2, status2 = self.scheduler.schedule_execution(e2)
        success3, status3 = self.scheduler.schedule_execution(e3)
        success4, status4 = self.scheduler.schedule_execution(e4)
        self.assertIn(e1, self.scheduler.running)
        self.assertIn(e2, self.scheduler.running)
        self.assertIn(e3, self.scheduler.running)
        self.assertIn(e4, self.scheduler.running)
        self.assertEqual(success1, True)
        self.assertEqual(success2, True)
        self.assertEqual(success3, True)
        self.assertEqual(success4, True)       
        self.assertEqual(status1, 1)
        self.assertEqual(status2, 1)
        self.assertEqual(status3, 1)
        self.assertEqual(status4, 1)

class ComplexSchedulingTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, is_running=False)
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=NORMAL, rated_power=2000)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=7200))
        a1.profile.set([p1])
        a1.save()        

        p2 = Profile.objects.create(name="Test 2", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, rated_power=400)
        a2 = Appliance.objects.create(name="Test 2", maximum_duration_of_usage=timezone.timedelta(seconds=300))
        a2.profile.set([p2])
        a2.save() 
        
        # Fill whole schedule (assuming 8000W threshold)
        self.scheduler = ScheduleManager()
        self.scheduler.clean()
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
        result5, status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        e6 = Execution.objects.get(pk=6)
        self.assertTrue(result5)
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
        result5, status5 = self.scheduler.schedule_execution(e5)
        e1 = Execution.objects.get(pk=1)
        e5 = Execution.objects.get(pk=5)
        self.assertTrue(result5)
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

class OtherFunctionsTestCase(TestCase):
    def setUp(self):
        AppVals.objects.create(consumption_threshold=8000, is_running=False)
        self.scheduler = ScheduleManager()
        self.scheduler.clean()

    def test_parse_time_to_slot(self):
        p1 = self.scheduler.parse_time_to_slot("2021, 12, 7, 11, 55")
        p2 = self.scheduler.parse_time_to_slot("2021-12-7 11:55:00")
        p3 = self.scheduler.parse_time_to_slot("2021/12/7 11:55:00")
        p4 = self.scheduler.parse_time_to_slot(timezone.datetime(2021, 12, 7, 11, 55))
        self.assertEqual(p1, p2)
        self.assertEqual(p1, p3)
        self.assertEqual(p1, p4)
    
    def test_get_current_schedule_slot(self):
        schedule_slot = self.scheduler.get_current_schedule_slot()
        now = timezone.now()
        current_slot = now.replace(minute=(now.minute//self.scheduler.step)*self.scheduler.step, second=0, microsecond=0)
        self.assertEqual(schedule_slot, current_slot)

