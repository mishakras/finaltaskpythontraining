import datetime
import math


def create_arrival_datetime(current_datetime: datetime.datetime,
                            travel_time, next_day=0):
    arrival_hours = math.floor(travel_time)
    arrival_minutes = math.floor((travel_time - arrival_hours) * 60)
    arrival_timedelta = datetime.timedelta(days=next_day, hours=arrival_hours,
                                           minutes=arrival_minutes)
    return current_datetime + arrival_timedelta
