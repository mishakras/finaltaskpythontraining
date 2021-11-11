import datetime
import math


def create_datetime(current_datetime: datetime.datetime,
                    travel_time):
    """
    Функция, создающая текущую дату и время в формате год, месяц, день,
     часы: минуты, на основе переданных параметров
    :param current_datetime: текущая дата в формате год, месяц, день
    :param travel_time: текущее время в часах
    :return:
    """
    arrival_hours = math.floor(travel_time)
    arrival_minutes = math.floor((travel_time - arrival_hours) * 60)
    arrival_seconds = math.floor((travel_time - arrival_hours - arrival_minutes/60) * 60)
    arrival_timedelta = datetime.timedelta(hours=arrival_hours,
                                           minutes=arrival_minutes,
                                           seconds=arrival_seconds)
    return current_datetime + arrival_timedelta
