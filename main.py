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
    current_time = 8
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("starting_city")
    print(configs)
    args = parser.parse_args()
    excursions = []
    with open(args.input_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for i in reader:
            excursions.append(i)
    cities = [i['City'] for i in excursions]
    cities.append(args.starting_city)
    tasks = [asyncio.create_task(create_distance(i, j)) for i in cities for j in cities if i != j]
    await asyncio.gather(*tasks)
    for index, i in enumerate(cities):
        graph[i] = {j.result()[2]: j.result()[3]
                    for j in tasks[index * (len(cities) - 1):(index + 1) * (len(cities) - 1)]
                    if not (j.result()[2] in graph and i in graph[j.result()[2]])}

    courses = course(cities)
    current_course = next(courses)
    print(current_course)
    print(count_tour(current_course))
    current_course[0] = [current_course[0], current_time, current_time, "starting point"]
    for index, i in enumerate(current_course):
        if index == len(current_course) - 1:
            break
        if i[0] in graph and current_course[index + 1] in graph[i[0]]:
            distance = graph[i[0]][current_course[index + 1]]
        else:
            print(i[0])
            print(current_course[index + 1])
            distance = graph[current_course[index + 1]][i[0]]
        if distance > configs['driving time'] * configs["velocity"]:
            task = await middle_city(i, current_course[index + 1],'https://citiesbetween.com/' + i[0] +'-and-' + current_course[index + 1])
            print(task)
        excursion = [i for i in excursions if i['City'] == current_course[index+1]]
        arrival = current_time+distance/configs["velocity"]
        times = excursion[0]['Start time'].strip().split(',')
        for index2, time in enumerate(times):
            time = time.split(':')
            time = int(time[0])+int(time[1])/60
            times[index2] = time
        for time in times:
            if time > arrival:
                excursion_start_time = time
                break
            excursion_start_time = times[0]
        duration = excursion[0]['Duration']
        current_course[index+1] = [current_course[index+1], arrival, excursion_start_time+int(duration[:len(duration) - 1]), excursion[0]['Name']]




    for i in current_course:
        print(i)
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
    return [i, 'to', j, int(temp[:len(temp) - 3])]


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


async def middle_city(start, finish, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find_all(class_="cityinfo")
    for index, i in enumerate(div):
        distance = i.contents[2].contents[0]
        if int(distance[:len(distance) - 3]) > configs['driving time'] * configs["velocity"]:
            distance = div[index - 1].contents[2].contents[0]
            return [str(div[index - 1].contents[0].string), int(distance[:len(distance) - 3])]


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
