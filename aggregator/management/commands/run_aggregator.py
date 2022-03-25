import os
import django

from django.core.management.base import BaseCommand
import processor.aggregator_server as aggregator

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Aggregator running. Receiving requests.")
        while True:
            aggregator.receive_request()