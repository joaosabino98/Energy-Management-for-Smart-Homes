from django.test import TestCase, tag

from scheduler.settings import IMMEDIATE, INTERRUPTIBLE, LOW_PRIORITY, NORMAL
from .models import Execution, Appliance, Profile
from manager.schedule_core import ScheduleManager
from django.utils import timezone
import time

# Create your tests here.

""" Test the priority formula by simulating executions created at different moments in the past. """
class PriorityTestCase(TestCase):
    def setUp(self):
        p1 = Profile.objects.create(name="Low priority profile", schedulability=INTERRUPTIBLE, priority=LOW_PRIORITY, maximum_delay=timezone.timedelta(seconds=43200), rated_power=0)
        p2 = Profile.objects.create(name="Normal priority profile", schedulability=INTERRUPTIBLE, priority=NORMAL, maximum_delay=timezone.timedelta(seconds=3600), rated_power=0)
        p3 = Profile.objects.create(name="Immediate priority profile", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, maximum_delay=timezone.timedelta(seconds=900), rated_power=0)
        a1 = Appliance.objects.create(name="Test")
        a1.profile.set([p1, p2, p3])
        a1.save()        

    def test_low_priority_calculation(self):
        s = ScheduleManager()
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
        self.assertEqual(s.calculate_weighted_priority(e1), 1) # expected priority: 1
        self.assertEqual(s.calculate_weighted_priority(e2), 1) # expected priority: 1
        self.assertEqual(s.calculate_weighted_priority(e3), 1) # expected priority: 1
        self.assertEqual(s.calculate_weighted_priority(e4), 1) # expected priority: 1
        self.assertEqual(s.calculate_weighted_priority(e5), 1) # expected priority: 1
        self.assertEqual(s.calculate_weighted_priority(e6), 1) # expected priority: 1

    def test_normal_priority_calculation(self):
        s = ScheduleManager()
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=3550) # 10 seconds remaining 
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))        
        self.assertEqual(s.calculate_weighted_priority(e1), 5) # expected priority: 5
        self.assertEqual(s.calculate_weighted_priority(e2), 9) # expected priority: 9
        self.assertEqual(s.calculate_weighted_priority(e3), 10) # expected priority: 10

    def test_immediate_priority_calculation(self):
        s = ScheduleManager()
        rt1 = timezone.now() # 15 minutes remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=600) # 5 minutes remaining
        rt3 = timezone.now()-timezone.timedelta(seconds=890) # 10 seconds remaining 
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=3))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=3))
        e3 = Execution.objects.create(request_time=rt3,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=3))        
        self.assertEqual(s.calculate_weighted_priority(e1), 10) # expected priority: 10
        self.assertEqual(s.calculate_weighted_priority(e2), 10) # expected priority: 10
        self.assertEqual(s.calculate_weighted_priority(e3), 10) # expected priority: 10

    def test_get_lower_priority_shiftable_executions(self):
        s = ScheduleManager()
        rt1 = timezone.now() # 1 hour remaining (maximum delay)
        rt2 = timezone.now()-timezone.timedelta(seconds=2700) # 15 minutes remaining
        e1 = Execution.objects.create(request_time=rt1,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        e2 = Execution.objects.create(request_time=rt2,appliance=Appliance.objects.first(),profile=Profile.objects.get(pk=2))
        s.schedule_execution(e1) # Interruptible, priority: 5
        s.schedule_execution(e2) # Interruptible, priority: 9
        self.assertEqual(len(s.get_lower_priority_shiftable_executions(4)[0]), 0)
        self.assertEqual(len(s.get_lower_priority_shiftable_executions(7)[0]), 1)
        self.assertEqual(len(s.get_lower_priority_shiftable_executions(9)[0]), 1)
        self.assertEqual(len(s.get_lower_priority_shiftable_executions(10)[0]), 2)


""" Test execution lifecycle """
class LifecycleTestCase(TestCase):
    def setUp(self):
        p1 = Profile.objects.create(name="Test 1", schedulability=INTERRUPTIBLE, priority=IMMEDIATE, rated_power=0)
        a1 = Appliance.objects.create(name="Test 1", maximum_duration_of_usage=timezone.timedelta(seconds=3))
        a1.profile.add(p1)

    def test_execution_creation(self):
        e1 = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        self.assertEqual(Execution.objects.get(pk=1), e1)

    def test_execution_simple_scheduling(self):
        s = ScheduleManager()
        e = Execution.objects.create(appliance=Appliance.objects.first(),profile=Profile.objects.first())
        success, status = s.schedule_execution(e)
        self.assertIn(e, s.running)
        self.assertEqual(success, True)
        self.assertEqual(status, 1)

"""  """



