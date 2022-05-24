from django.contrib import admin
from django.utils.encoding import force_str
from django.utils.translation import gettext as _

class DefaultListFilter(admin.SimpleListFilter):
    all_value = '_all'

    def default_value(self):
        raise NotImplementedError()

    def queryset(self, request, queryset):
        if self.parameter_name in request.GET and request.GET[self.parameter_name] == self.all_value:
            return queryset

        if self.parameter_name in request.GET:
            return queryset.filter(**{self.parameter_name:request.GET[self.parameter_name]})

        return queryset.filter(**{self.parameter_name:self.default_value()})

    def choices(self, cl):
        yield {
            'selected': self.value() == self.all_value,
            'query_string': cl.get_query_string({self.parameter_name: self.all_value}, []),
            'display': _('All'),
        }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == force_str(lookup) or (self.value() == None and force_str(self.default_value()) == force_str(lookup)),
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }

class HiddenFilter(DefaultListFilter):
    title = _("hidden")
    parameter_name = 'hidden'

    def lookups(self, request, model_admin):
        return (
            (1, True),
            (0, False),
        )

    def default_value(self):
        return 0

class StatusFilter(admin.SimpleListFilter):
    title = _('status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('Pending', _('Pending')),
            ('Started', _('Started')),
            ('Finished', _('Finished')),
            ('Interrupted', _('Interrupted'))
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        q_ids = [e.id for e in queryset if e.status() == value]
        return queryset.filter(id__in=q_ids)