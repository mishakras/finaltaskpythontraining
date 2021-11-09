import argparse
import asyncio
import csv
import datetime
import json
import math

import aiohttp
from bs4 import BeautifulSoup

from courses import create_courses, count_course
from graph import create_graph


class Excursion:
    """
    Класс хранящий информацию об экскурсии
    """
    def __init__(self, name, city, start_time, duration):
        """
        Конструктор для класса Excursion
        :param name:
        :param city:
        :param start_time:
        :param duration:
        """
        self.name = name
        self.city = city
        self.start_time = start_time
        self.duration = duration


class City:
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
    args = parser.parse_args()
    excursions = get_excursions(args.input_file)
    cities = [i.city for i in excursions]
    cities.append(args.starting_city)
    graph = await create_graph(cities)
    all_courses = create_courses(cities[:len(cities) - 1])
    min_distance = math.inf
    for i in all_courses:
        i.insert(0, args.starting_city)
        distance = count_course(i, graph)
        if distance < min_distance:
            current_course = i
            min_distance = distance
    current_course, current_drive_time, current_time \
        = await create_course_with_middle_cities(current_course, excursions, graph)
    current_course = \
        await complete_course(current_course, current_drive_time,
                              current_time, args.starting_city, graph)
    write_course(current_course, args.output_file)
    for i in current_course:
        print(i)


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


async def create_course_with_middle_cities(current_course, excursions, graph):
    """
    Функция, заполняющая переданный маршрут промежуточными городами

    :param graph: Матрица расстояний между городами
    :param current_course: Изначальный маршрут поездки
    :param excursions: Список экскурсий в изначальных городах
    :return: Маршрут поездки с промежуточными городами, кроме возвращения
            в стартовый город
    """
    current_drive_time = 0
    current_time = configs['start']
    current_course[0] = [current_course[0], configs['start'],
                         configs['start'], "starting point"]
    distance = None
    for index, i in enumerate(current_course):
        if index == len(current_course) - 1:
            break

        possible_middle_city, current_drive_time \
            = await \
            put_middle_city(i[0], current_course[index + 1],
                            current_drive_time, current_time,
                            distance, graph, excursions)
        current_time = possible_middle_city[2]
        distance = None
        if possible_middle_city[0] == current_course[index + 1]:
            current_course[index + 1] = possible_middle_city
        else:
            current_course.insert(index + 1, possible_middle_city)
            distance = possible_middle_city[4]
    return current_course, current_drive_time, current_time


async def put_middle_city(start_city, end_city, current_drive_time,
                          current_time, distance, graph, current_datetime: datetime.datetime, excursions=None,
                          starting_city=None):
    """
    Асинхронная функция, возвращающая данные либо о промежуточном городе,
    либо о городе с экскурсией через функцию create_excursion_city.
    Если вызванна из функции complete_course возвращает данные
    либо о промежуточном городе, либо о времени приезда в стартовый город

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
            arrival = distance / configs["velocity"]
            current_time = current_time + arrival
            arrival_hours = math.floor(arrival)
            arrival_minutes = math.floor((arrival - arrival_hours)*60)
            arrival_timedelta = datetime.timedelta(hours=arrival_hours,
                                                   minutes=arrival_minutes)
            current_datetime += arrival_timedelta

            City(end_city, current_datetime)
            return [end_city, current_time + distance / configs["velocity"],
                    8, "Ending point"], None
        return create_excursion_city(end_city, excursions, current_time,
                                     distance, current_drive_time)
    middle_city = await find_middle_city(start_city, end_city,
                                         max_driving_distance)
    if middle_city:
        arrival = current_time + middle_city[1] / configs["velocity"]
        current_time = 8
        current_drive_time = 0
        if distance - middle_city[1] > \
                configs['driving time'] * configs["velocity"]:
            second_city = await find_middle_city(middle_city[0], end_city,
                                                 configs['driving time']
                                                 * configs["velocity"])
            if second_city:
                return [middle_city[0], arrival, current_time,
                        "Stopping point", distance - middle_city[1]], \
                       current_drive_time
        else:
            return [middle_city[0], arrival, current_time,
                    "Stopping point", distance - middle_city[1]], \
                   current_drive_time
    max_driving_distance = configs['driving time'] * configs["velocity"]
    current_time = 8
    current_drive_time = 0
    if distance < max_driving_distance:
        if end_city == starting_city:
            return [end_city, current_time + distance / configs["velocity"],
                    8, "Ending point"], None
        return create_excursion_city(end_city, excursions, current_time,
                                     distance, current_drive_time)
    middle_city = await find_middle_city(start_city, end_city,
                                         max_driving_distance)
    arrival = current_time + middle_city[1] / configs["velocity"]
    return [middle_city[0], arrival, current_time, "Stopping point",
            distance - middle_city[1]], current_drive_time


def create_excursion_city(excursion_city, excursions, current_time,
                          distance, current_drive_time):
    """
    Функция генерирует данные о городе с экскурсией на основе входных параметров

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
            break
        excursion_start_time = times[0]
        new_current_drive_time = 0
    duration = excursion[0].duration
    current_time = excursion_start_time + int(duration[:len(duration) - 1])
    stop_name = excursion[0].name
    return [excursion_city, arrival, current_time,
            stop_name], new_current_drive_time


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


async def complete_course(current_course, current_drive_time,
                          current_time, start_city, graph):
    """
    Функция, завершающая маршрут, добавляя промежуточные города
    между стартовым городом и последним городом в маршруте

    :param graph: Матрица расстояний между городами
    :param current_course: Маршрут движения
    :param current_drive_time: Время за рулем в текущий день
    :param current_time: Время отбытия из города, откуда выезжаем
    :param start_city: Стартовы1 город
    :return: Завершённый маршрут движения
    """
    end_city = current_course[len(current_course) - 1][0]
    if start_city in graph and end_city in graph[start_city]:
        distance = graph[start_city][end_city]
    else:
        distance = graph[end_city][start_city]
    while True:
        city, current_drive_time = \
            await put_middle_city(end_city, start_city, current_drive_time,
                                  current_time, distance, graph,
                                  starting_city=start_city)
        end_city = city[0]
        current_course.append(city)
        if city[0] != start_city:
            current_time = city[2]
            distance = city[4]
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
        current_course.insert(0, ['Название города', 'Время приезда',
                                  'Время убытия', 'Экскурсия/остановка'])
        writer = csv.writer(output)
        writer.writerows(current_course)


with open('config.json') as f:
    configs = json.load(f)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
