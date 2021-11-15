import argparse
import asyncio
import csv
import datetime
import json
import math

import aiohttp
from bs4 import BeautifulSoup

from courses import create_courses, count_course
from datetime_handle import create_datetime
from graph import create_graph


class Excursion:
    """
    Класс хранящий информацию об экскурсии
    """

    def __init__(self, name, city, start_time, duration):
        self.name = name
        self.city = city
        self.start_time = start_time
        self.duration = duration


class City:
    """
    Класс хранящий информацию о посещенном городе
    """
    def __init__(self, name, arrival, leaving, stop_name):
        self.name = name
        self.arrival = arrival
        self.leaving = leaving
        self.stop_name = stop_name


async def main():
    """
    Основная функция модуля, запускающая расчёт оптимального маршрута
    для экскурсий из входного файла, стартующего и возвращающегося
    в входной город, с записью в выходной файл
    Все параметры указываются во командной строке при запуске модуля
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    parser.add_argument("starting_city")
    parser.add_argument("--start_date", default=None)
    args = parser.parse_args()
    if args.start_date:
        current_datetime = args.start_date.split(',')
        current_time = current_datetime[3].split(':')
        current_time = int(current_time[0])+int(current_time[1])/60
        current_datetime = datetime.datetime(year=int(current_datetime[0]),
                                             month=int(current_datetime[1]),
                                             day=int(current_datetime[2]))

    else:
        dt = datetime.datetime.now()
        current_datetime = datetime.datetime(dt.year, dt.month, dt.day)
        current_time = dt.hour+dt.minute/60+dt.second/3600
    excursions = get_excursions(args.input_file)
    cities = [i.city for i in excursions]
    cities.append(args.starting_city)
    graph = await create_graph(cities)
    if len(cities) != 2:
        all_courses = create_courses(cities[:len(cities) - 1])
        min_distance = math.inf
        for i in all_courses:
            i.insert(0, args.starting_city)
            distance = count_course(i, graph)
            if distance < min_distance:
                current_course = i
                min_distance = distance
    else:
        current_course = [cities[1], cities[0]]
    current_course, current_parameters \
        = await create_course_with_middle_cities(current_course, excursions,
                                                 graph, current_datetime,
                                                 current_time)
    current_course = \
        await complete_course(current_course, current_parameters[0],
                              current_parameters[1], args.starting_city, graph,
                              current_parameters[2])
    write_course(current_course, args.output_file)


def get_excursions(input_file):
    """
    Функция, возвращающая спискок экскурсий из переданного файла

    :param input_file: Путь к файлу, содержащему список экскурсий
    :return: Список экскурсий
    """
    excursions = []
    with open(input_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for i in reader:
            excursions.append(Excursion(i['Name'], i['City'],
                                        i['Start time'], i['Duration']))
    return excursions


async def create_course_with_middle_cities(current_course, excursions, graph,
                                           current_datetime, current_time):
    """
    Функция, заполняющая переданный маршрут промежуточными городами

    :param current_time: Время отбытия из стартового города
    :param current_datetime: Текущая дата в формате год, месяц, день
    :param graph: Матрица расстояний между городами
    :param current_course: Изначальный маршрут поездки
    :param excursions: Список экскурсий в изначальных городах
    :return: Маршрут поездки с промежуточными городами, кроме возвращения
            в стартовый город
    """
    current_drive_time = 0
    current_course[0] = City(current_course[0], None,
                             create_datetime(current_datetime, current_time),
                             "starting point")
    distance = None
    for index, i in enumerate(current_course):
        if index == len(current_course) - 1:
            break

        possible_middle_city \
            = await \
            put_middle_city(i.name, current_course[index + 1],
                            current_drive_time, current_time,
                            distance, current_datetime, graph, excursions)
        current_drive_time = possible_middle_city[1][0]
        current_datetime = possible_middle_city[1][1]
        current_time = possible_middle_city[1][2]
        distance = None
        if possible_middle_city[0].name == current_course[index + 1]:
            current_course[index + 1] = possible_middle_city[0]
        else:
            current_course.insert(index + 1, possible_middle_city[0])
            distance = possible_middle_city[1][3]
        if len(possible_middle_city) == 3:
            current_course[index].leaving =\
                create_datetime(current_datetime, 8)
    return current_course, [current_drive_time, current_time, current_datetime]


async def put_middle_city(start_city, end_city, current_drive_time,
                          current_time, distance, current_datetime, graph=None,
                          excursions=None, starting_city=None):
    """
    Асинхронная функция, возвращающая данные либо о промежуточном городе,
    либо о городе с экскурсией через функцию create_excursion_city.
    Если вызванна из функции complete_course возвращает данные
    либо о промежуточном городе, либо о времени приезда в стартовый город

    :param current_datetime: Текущая дата в формате год, месяц, день
    :param graph: Матрица расстояний между городами
    :param start_city: Город, откуда выезжаем
    :param end_city: Город, куда пытаемся приехать
    :param current_drive_time: Время за рулем в текущий день
    :param current_time: Время отбытия из города, откуда выезжаем
    :param distance: Расстояние между городами, может отсутствовать
    :param excursions: Список экскурсий, может отстутствовать
    :param starting_city: Параметр из функции complete_course,
            стартовый город маршрута
    :return: Данные о городе с экскурсией функции create_excursion_city, либо
            данные о промежуточном городе в виде списка:
            Название, время прибытия, время отбытия, название экскурсии в городе
            и обновлённое время за рулем в текущий день
            либо если вызванна из функции complete_course и достигнут стартовый
            город маршрута, данные о времени достижения этого города
    """
    if not distance:
        if start_city in graph and end_city in graph[start_city]:
            distance = graph[start_city][end_city]
        elif end_city in graph and start_city in graph[end_city]:
            distance = graph[end_city][start_city]
    max_driving_distance = min(
        configs['driving time'] - current_drive_time,
        configs['end'] - current_time
    ) * configs["velocity"]

    if distance < max_driving_distance:
        if end_city == starting_city:
            arrival_datetime = create_datetime(current_datetime,
                                               current_time + distance
                                               / configs["velocity"])
            return City(end_city, arrival_datetime, None,
                        "Ending point"), None
        return create_excursion_city(end_city, excursions, current_time,
                                     distance, current_drive_time,
                                     current_datetime)
    middle_city = await find_middle_city(start_city, end_city,
                                         max_driving_distance)
    current_drive_time = 0
    if middle_city:
        if distance - middle_city[1] > \
                configs['driving time'] * configs["velocity"]:
            second_city = await find_middle_city(middle_city[0], end_city,
                                                 configs['driving time']
                                                 * configs["velocity"])
            if second_city:
                return create_middle_city(middle_city[0], distance,
                                          middle_city[1],
                                          current_time, current_datetime,
                                          current_drive_time)
        else:
            return create_middle_city(middle_city[0], distance, middle_city[1],
                                      current_time, current_datetime,
                                      current_drive_time)
    current_datetime = current_datetime + datetime.timedelta(days=1)
    max_driving_distance = configs['driving time'] * configs["velocity"]
    if distance < max_driving_distance:
        current_time = 8
        if end_city == starting_city:
            arrival_datetime = create_datetime(current_datetime,
                                               current_time + distance
                                               / configs["velocity"])
            return [City(end_city, arrival_datetime, None,
                         "Ending point"), None, True]
        create_excursion_city_dec = decorator(create_excursion_city)
        return create_excursion_city_dec(end_city, excursions, current_time,
                                         distance, current_drive_time,
                                         current_datetime)
    middle_city = await find_middle_city(start_city, end_city,
                                         max_driving_distance)
    create_middle_city_dec = decorator(create_middle_city)
    return create_middle_city_dec(middle_city[0], distance, middle_city[1],
                                  current_time, current_datetime,
                                  current_drive_time)


def create_excursion_city(excursion_city, excursions, current_time,
                          distance, current_drive_time, current_datetime):
    """
    Функция генерирует данные о городе с экскурсией на основе входных параметров

    :param current_datetime: Текущая дата в формате год, месяц, день
    :param excursion_city: Город в котором проходит экскурсия
    :param excursions: Список всех экскурсий
    :param current_time: Время отбытия из предудущего города
    :param distance: Расстояние между предудущим городом и текущим
    :param current_drive_time: Время за рулем в текущий день
    :return: Список хранящий данные о посещенном городе:
        Название, время прибытия, время отбытия, название экскурсии в городе
        и обновлённое время за рулем в текущий день
    """
    excursion = [i for i in excursions if i.city == excursion_city]
    arrival = current_time + distance / configs["velocity"]
    times = excursion[0].start_time.strip().split(',')
    for index2, time in enumerate(times):
        time = time.split(':')
        time = int(time[0]) + int(time[1]) / 60
        times[index2] = time
    for time in times:
        if time > arrival:
            excursion_start_time = time
            new_current_drive_time = \
                current_drive_time + distance / configs["velocity"]
            new_current_datetime = current_datetime
            break
        excursion_start_time = times[0]
        new_current_drive_time = 0
        new_current_datetime = current_datetime + datetime.timedelta(days=1)
    duration = excursion[0].duration
    current_time = excursion_start_time + int(duration[:len(duration) - 1])
    stop_name = excursion[0].name
    arrival_datetime = create_datetime(current_datetime, arrival)
    leaving_datetime = create_datetime(current_datetime, current_time)
    return [City(excursion_city, arrival_datetime, leaving_datetime,
                stop_name), [new_current_drive_time,
                             new_current_datetime, current_time]]


def create_middle_city(city_name, distance, travel_distance, current_time,
                       current_datetime, current_drive_time):
    """
    Функция генерирует данные о городе с экскурсией на основе входных параметров

    :param current_datetime: Текущая дата в формате год, месяц, день
    :param city_name: Название промежуточного города
    :param travel_distance: Расстояние до промежуточного города
    :param current_time: Время отбытия из предудущего города
    :param distance: Расстояние между предудущим городом и текущим
    :param current_drive_time: Время за рулем в текущий день
    :return: Список хранящий данные о посещенном городе:
        Название, время прибытия, время отбытия, название экскурсии в городе
        и обновлённое время за рулем в текущий день
    """
    arrival = current_time + travel_distance / configs["velocity"]
    current_time = 8
    arrival_datetime = create_datetime(current_datetime, arrival)
    current_datetime = current_datetime + datetime.timedelta(days=1)
    leaving_datetime = create_datetime(current_datetime, current_time)
    return [City(city_name, arrival_datetime, leaving_datetime,
                 "Stopping point"), [current_drive_time, current_datetime,
                                     current_time, distance - travel_distance]]


async def find_middle_city(start_city, end_city, max_driving_distance):
    """
    Функция, запрашивающая у внешнего сайта список всех городов между
    start_city и end_city и самый дальний,
    расстояние до которого не превосходит max_driving_distance

    :param start_city: Город, откуда выезжаем
    :param end_city: Город, куда едем
    :param max_driving_distance: Максимальная дальность поездки в текущий день
    :return:
    """
    url = 'https://citiesbetween.com/' + start_city + '-and-' + end_city
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find_all(class_="cityinfo")
    for index, i in enumerate(div):
        distance = i.contents[2].contents[0]
        if int(distance[:len(distance) - 3]) > max_driving_distance:
            distance = div[index - 1].contents[2].contents[0]
            return [str(div[index - 1].contents[0].string),
                    int(distance[:len(distance) - 3])]


def decorator(func):
    """
    Декоратор принимающий на вход функцию, возвращающий функцию,
    которая к результату исходной добавляет True
    :param func:
    :return:
    """
    def wrapped(*args, **kwargs):
        temp = list(func(*args, **kwargs))
        temp.append(True)
        return temp
    return wrapped


async def complete_course(current_course, current_drive_time,
                          current_time, start_city, graph, current_datetime):
    """
    Функция, завершающая маршрут, добавляя промежуточные города
    между стартовым городом и последним городом в маршруте

    :param current_datetime: Текущая дата в формате год, месяц, день
    :param graph: Матрица расстояний между городами
    :param current_course: Маршрут движения
    :param current_drive_time: Время за рулем в текущий день
    :param current_time: Время отбытия из города, откуда выезжаем
    :param start_city: Стартовы1 город
    :return: Завершённый маршрут движения
    """
    end_city = current_course[len(current_course) - 1].name
    if start_city in graph and end_city in graph[start_city]:
        distance = graph[start_city][end_city]
    else:
        distance = graph[end_city][start_city]
    while True:
        city = \
            await put_middle_city(end_city, start_city, current_drive_time,
                                  current_time, distance, current_datetime,
                                  graph, starting_city=start_city)
        end_city = city[0].name
        current_course.append(city[0])
        if len(city) == 3:
            current_course[len(current_course)-2].leaving =\
                create_datetime(current_datetime +
                                datetime.timedelta(days=1), 8)
        if end_city != start_city:
            current_drive_time = city[1][0]
            current_datetime = city[1][1]
            current_time = city[1][2]
            distance = city[1][3]
        else:
            break
    return current_course


def write_course(current_course, output_file):
    """
    Функция, записывающая переданный маршрут в переданный файл

    :param current_course: Завершеный маршрут движения
    :param output_file: Путь к файлу для записи
    """
    with open(output_file, 'w') as output:
        writer = csv.writer(output)
        writer.writerow(['Название города', 'Время приезда',
                        'Время убытия', 'Экскурсия/остановка'])
        for i in current_course:
            print(i.name, i.arrival, i.leaving, i.stop_name)
            writer.writerow([i.name, i.arrival, i.leaving, i.stop_name])


with open('config.json') as f:
    configs = json.load(f)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
