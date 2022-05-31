from django.contrib import admin, messages
from django.utils.translation import ngettext
import processor.core as core
from .models import Home, BatteryStorageSystem, PhotovoltaicSystem, Appliance, Execution, Profile
from .filters import StatusFilter, HiddenFilter

# Register your models here.

class ExecutionAdmin(admin.ModelAdmin):
    @admin.action(description="Schedule execution")
    def schedule_execution(self, request, queryset):
        updated = 0
        for execution in queryset:
            res = core.schedule_execution(execution, execution.request_time)
            if res != -1:
                updated += 1
        self.message_user(request, ngettext(
                '%d execution was successfully scheduled.',
                '%d executions were successfully scheduled.',
                updated,
            ) % updated, messages.SUCCESS)

    @admin.action(description="Finish execution")
    def finish_execution(self, request, queryset):
        updated = 0
        for execution in queryset:
            core.finish_execution(execution)
            updated += 1

        self.message_user(request, ngettext(
                '%d execution was successfully marked as finished.',
                '%d executions were successfully marked as finished.',
                updated,
            ) % updated, messages.SUCCESS)

    search_fields = ['appliance__name']
    list_filter = [StatusFilter]
    list_display = ('appliance', 'profile', 'start_time', 'end_time', 'status')
    fields = ['home', 'request_time', 'appliance', 'profile']
    actions = [schedule_execution, finish_execution]

class ProfileAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = [HiddenFilter]
    list_display = ['name', 'schedulability', 'priority', 'maximum_duration_of_usage', 'rated_power']
    fields = ['name', 'schedulability', 'priority', 'maximum_duration_of_usage', 'rated_power']

class ApplianceAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'maximum_delay']

class HomeAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'consumption_threshold', 'accept_recommendations']
    fields = ['consumption_threshold']
    actions = ['connect_to_aggregator', 'disconnect_from_aggregator']

    @admin.action(description="Connect to aggregator")
    def connect_to_aggregator(self, request, queryset):
        for home in queryset:
            core.start_aggregator_client(home.id, True)

    @admin.action(description="Disconnect from aggregator")
    def disconnect_from_aggregator(self, request, queryset):
        for home in queryset:
            core.stop_aggregator_client(home.id)

    def has_delete_permission(self, request, obj=None):
            return False
    
    def has_add_permission(self, request, obj=None):
        return False

class BatteryStorageSystemAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'total_energy_capacity', 'last_full_charge_time']
    fields = ['total_energy_capacity', 'continuous_power', 'last_full_charge_time', 'depth_of_discharge']

    def has_delete_permission(self, request, obj=None):
            return False

    def has_add_permission(self, request, obj=None):
            return False

class PhotovoltaicSystemAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'latitude', 'longitude']
    fields = ['latitude', 'longitude', 'tilt', 'azimuth', 'capacity']
    def has_delete_permission(self, request, obj=None):
            return False

    def has_add_permission(self, request, obj=None):
            return False

admin.site.register(BatteryStorageSystem, BatteryStorageSystemAdmin)
admin.site.register(PhotovoltaicSystem, PhotovoltaicSystemAdmin)
admin.site.register(Home, HomeAdmin)
admin.site.register(Appliance, ApplianceAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Execution, ExecutionAdmin)
