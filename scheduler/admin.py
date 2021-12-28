from django.contrib import admin

# Register your models here.
from .models import Appliance, Execution, Profile

admin.site.register(Appliance)
admin.site.register(Profile)
admin.site.register(Execution)
