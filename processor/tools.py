from math import floor
from django.utils import timezone

def is_now(date):
    now = timezone.now()
    difference = (date - now).total_seconds()
    if abs(difference) < 5:
        return True
    return False

def compact_periods(periods):
    new_periods = {}
    if periods:
        block_start_time = next(iter(periods))[0]
        block_end_time = next(iter(periods))[1]
        block_energy = periods[next(iter(periods))]
        for period in periods:
            if periods[period] == block_energy:
                block_end_time = period[1]
            else:
                new_periods[(block_start_time, block_end_time)] = block_energy
                block_start_time = period[0]
                block_end_time = period[1]
                block_energy = periods[period]
        new_periods[(block_start_time, block_end_time)] = block_energy
    return new_periods

def positive_power_difference(rated_power, target_power):
	return rated_power - target_power if rated_power < target_power else float("inf")

def power_to_energy(start_time, end_time, power):
    return floor(power * (end_time - start_time).seconds/3600)

def energy_to_power(start_time, end_time, energy):
    return floor(energy / ((end_time - start_time).seconds/3600)) if (end_time - start_time).seconds != 0 else 0