import asyncio
import copy
import csv
import aiohttp
from bs4 import BeautifulSoup
import argparse
import json

graph = dict()
with open('config.json') as f:
    configs = json.load(f)


async def main():
    current_drive_time = 0
    current_time = configs['start']
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("starting_city")
    args = parser.parse_args()
    excursions = get_excursions(args.input_file)
    cities = [i['City'] for i in excursions]
    cities.append(args.starting_city)
    tasks = [asyncio.create_task(create_distance(i, j)) for i in cities for j in cities if i != j]
    await asyncio.gather(*tasks)
    for index, i in enumerate(cities[:len(cities)-1]):
        graph[i] = {j.result()[0]: j.result()[1]
                    for j in tasks[index * (len(cities) - 1):(index + 1) * (len(cities) - 1)]
                    if not (j.result()[0] in graph and i in graph[j.result()[0]])}
    courses = course(cities)
    current_course = next(courses)
    print(current_course)
    current_course[0] = [current_course[0], configs['start'], configs['start'], "starting point"]
    for index, i in enumerate(current_course):
        if index == len(current_course) - 1:
            break
        if i[0] in graph and current_course[index + 1] in graph[i[0]]:
            distance = graph[i[0]][current_course[index + 1]]
        elif current_course[index + 1] in graph and i[0] in graph[current_course[index + 1]]:
            distance = graph[current_course[index + 1]][i[0]]
        else:
            distance = await create_distance(i[0], current_course[index+1])
            distance = distance[1]
        max_driving_distance = min(
                configs['driving time'] - current_drive_time,
                configs['end'] - current_time
                ) * configs["velocity"]
        if distance > max_driving_distance:
            task = await middle_city(max_driving_distance, 'https://citiesbetween.com/' + i[0] + '-and-' + current_course[index + 1])
            if not task:
                current_time = configs['start']
                i[2] = 8
                task = await middle_city(configs['driving time'], 'https://citiesbetween.com/' + i[0] + '-and-' + current_course[index + 1])
            current_course.insert(index + 1, task[0])
            distance = task[1]
            arrival = current_time + distance / configs["velocity"]
            current_time = configs['start']
            stop_name = "Stopping point"
            current_drive_time = 0
        else:
            excursion = [i for i in excursions if i['City'] == current_course[index+1]]
            arrival = current_time + distance/configs["velocity"]
            times = excursion[0]['Start time'].strip().split(',')
            for index2, time in enumerate(times):
                time = time.split(':')
                time = int(time[0])+int(time[1])/60
                times[index2] = time
            for time in times:
                if time > arrival:
                    excursion_start_time = time
                    current_drive_time = distance / configs["velocity"]
                    break
                excursion_start_time = times[0]
                current_drive_time = 0
            duration = excursion[0]['Duration']
            current_time = excursion_start_time+int(duration[:len(duration) - 1])
            stop_name = excursion[0]['Name']
        current_course[index+1] = [current_course[index+1], arrival, current_time, stop_name]
    for i in current_course:
        print(i)
    print(current_course[0][0])
    end_city = current_course[len(current_course)-1][0]
    starting_city = current_course[0][0]
    if starting_city in graph and end_city in graph[starting_city]:
        distance = graph[starting_city][end_city]
    else:
        distance = graph[end_city][starting_city]
    max_driving_distance = min(
        configs['driving time'] - current_drive_time,
        configs['end'] - current_time
    ) * configs["velocity"]
    while distance > max_driving_distance:
        task = await middle_city(max_driving_distance, 'https://citiesbetween.com/' + end_city + '-and-' + starting_city)

    return


def course(cities: list):
    for city in cities:
        temp = copy.copy(cities)
        temp.remove(city)
        if len(temp) > 1:
            temp = course(temp)
            for temp2 in temp:
                temp2.append(city)
                yield temp2
        else:
            yield [temp[0], city]


async def create_distance(i, j):
    url = 'https://www.travelmath.com/drive-distance/from/' + i + '/to/' + j
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find(id="drivedist")
    temp = str(div.contents[2].string)
    return [j, int(temp[:len(temp) - 3])]


def count_tour(tour):
    if tour[0] in graph and tour[len(tour) - 1] in graph[tour[0]]:
        distance = graph[tour[0]][tour[len(tour) - 1]]
    else:
        distance = graph[tour[len(tour) - 1]][tour[0]]
    for index, i in enumerate(tour[:len(tour) - 1]):
        if i in graph and tour[index + 1] in i:
            distance += graph[i][tour[index + 1]]
        else:
            distance += graph[tour[index + 1]][i]
    return distance


async def middle_city(max_driving_distance, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find_all(class_="cityinfo")
    for index, i in enumerate(div):
        distance = i.contents[2].contents[0]
        if int(distance[:len(distance) - 3]) > max_driving_distance:
            distance = div[index - 1].contents[2].contents[0]
            return [str(div[index - 1].contents[0].string), int(distance[:len(distance) - 3])]


def get_excursions(input_file):
    excursions = []
    with open(input_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for i in reader:
            excursions.append(i)
    return excursions


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
