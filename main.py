import asyncio
import copy
import csv
import aiohttp
from bs4 import BeautifulSoup
import argparse
import json

graph = dict()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("starting_city")
    with open('config.json') as f:
        configs = json.load(f)
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
                    for j in tasks[index*(len(cities)-1):(index+1)*(len(cities)-1)]
                    if not (j.result()[2] in graph and i in graph[j.result()[2]])}

    courses = course(cities)
    current_course = next(courses)
    print(current_course)
    print(count_tour(current_course))
    long_drives = []
    for index, i in enumerate(current_course[:len(current_course)-1]):
        if i in graph and current_course[index+1] in i:
            distance = graph[i][current_course[index+1]]
        else:
            distance = graph[current_course[index+1]][i]
        if distance > configs['driving time']*configs["velocity"]:
            long_drives.append([i, current_course[index+1]])
            print(i, current_course[index+1])
    tasks = [asyncio.create_task
             (middle_cities(drive[0], drive[1],
                            'https://citiesbetween.com/' + drive[0] +
                            '-and-' + drive[1]))
             for drive in long_drives]
    await asyncio.gather(*tasks)
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
    return [i, 'to', j, int(temp[:len(temp)-3])]


def count_tour(tour):
    if tour[0] in graph and tour[len(tour)-1] in graph[tour[0]]:
        distance = graph[tour[0]][tour[len(tour)-1]]
    else:
        distance = graph[tour[len(tour) - 1]][tour[0]]
    for index, i in enumerate(tour[:len(tour)-1]):
        if i in graph and tour[index+1] in i:
            distance += graph[i][tour[index+1]]
        else:
            distance += graph[tour[index+1]][i]
    return distance


async def middle_cities(start, finish, url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find_all(class_="cityinfo")
    for index, i in div:
        print(str(i.contents[0].string), str(i.contents[1].contents[1].string), i.contents[2].contents[0])


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
