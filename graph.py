import asyncio

import aiohttp
from bs4 import BeautifulSoup


async def create_graph(cities):
    """
    Функция, создающая матрицу для графа
     с вершинами в городах из переданного списка

    :param cities: Список городов, для которого создаётся граф
    :return:
    """
    graph = dict()
    distances = await create_distances(cities)
    for index, i in enumerate(cities[:len(cities) - 1]):
        graph[i] = {j[0]: j[1]
                    for j in distances[index * (len(cities) - 1)
                                       :(index + 1) * (len(cities) - 1)]
                    if not (j[0] in graph and i in graph[j[0]])}
    return graph


async def create_distances(cities):
    """
    Функция, возвращающая список расстояний между каждыми двумя городами из
    переданного списка

    :param cities: списка городов, для которых нужно рассчитать расстояния
    :return: Список конечных городов + расстояния до них
    """
    distances = [asyncio.create_task(create_distance(i, j)) for i in cities
                 for j in cities if i != j]
    await asyncio.gather(*distances)
    distances = [j.result() for j in distances]
    return distances


async def create_distance(start_city, end_city):
    """
    Функция запрашивающая у внешнего сайта расстояние между start_city, и end_city

    :param start_city: Город, откуда выезжаем
    :param end_city: Город, куда едем
    :return: Список:
            end_city, расстояние между городами
    """
    url = 'https://www.travelmath.com/drive-distance/from/' + start_city + '/to/' + end_city
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    div = soup.find(id="drivedist")
    if len(div) < 3:
        return None
    temp = str(div.contents[2].string)
    if len(temp) == 9:
        temp = temp[1:2] + temp[3:]
    if len(temp) == 10:
        temp = temp[1:3] + temp[4:]
    if len(temp) == 11:
        temp = temp[1:4] + temp[5:]
    return [end_city, int(temp[:len(temp) - 2])]