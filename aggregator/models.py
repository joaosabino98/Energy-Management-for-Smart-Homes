from django.db import models

class ConsumptionData(models.Model):
    home_id = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    power = models.IntegerField()

