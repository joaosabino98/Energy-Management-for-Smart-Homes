import logging

from django.conf import settings

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

logger = logging.getLogger(__name__)

logger.info("Creating scheduler...")
scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")
logger.info("Scheduler created.")

@util.close_old_connections
def delete_old_job_executions(max_age=604800):
	DjangoJobExecution.objects.delete_old_job_executions(max_age)

def start():
	logger.info("Starting scheduler...")
	scheduler.add_job(
		delete_old_job_executions,
		trigger=CronTrigger(day_of_week="mon", hour="00", minute="00"),
		id="delete_old_job_executions",
		max_instances=1,
		replace_existing=True
	)
	scheduler.start()

def stop():
	logger.info("Stopping scheduler...")
	scheduler.shutdown()
	logger.info("Scheduler shut down successfully!")
