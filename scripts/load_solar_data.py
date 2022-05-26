import csv
import django
import os
import re
from math import floor
from coordinator.models import PhotovoltaicSystem, ProductionData
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coordinator.settings")
django.setup()

directory = f'{django.conf.settings.BASE_DIR}/solardata'
pv = PhotovoltaicSystem.objects.last()

for filename in os.listdir(directory):
    f = os.path.join(directory, filename)
    if os.path.isfile(f):
        with open(f, newline='') as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            header = next(csv_reader)
            month_name = re.sub("[\(\)]", "", header[0]).split()[3]
            month = timezone.datetime.strptime(month_name, "%B").month
            for row in csv_reader:
                watts = floor(float(row[1])*1000)
                ProductionData.objects.create(system=pv, month=month, hour=row[0], average_power_generated=watts)
            print(f"Imported data from {filename}.")