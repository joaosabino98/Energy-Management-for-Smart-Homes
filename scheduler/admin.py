from django.contrib import admin

# Register your models here.
from .models import Appliance, Execution, Profile

class ExecutionAdmin(admin.ModelAdmin):
    fields = ['home', 'request_time', 'appliance', 'profile']

class ProfileAdmin(admin.ModelAdmin):
    fields = ['name', 'schedulability', 'priority', 'maximum_duration_of_usage', 'rated_power']

admin.site.register(Appliance)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Execution, ExecutionAdmin)
