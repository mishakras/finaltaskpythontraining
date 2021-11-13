import datetime
import json

import csv
import mock
import pytest

from main import (complete_course, create_course_with_middle_cities,
                  create_excursion_city, get_excursions,
                  put_middle_city, write_course, City, Excursion)
from courses import (create_courses, count_course)
from datetime_handle import create_datetime
from graph import create_graph


def test_read_configs():
    """
    Тест чтения конфигурации из json файла
    """
    with open('config.json') as f:
        configs = json.load(f)
    assert configs['velocity'] == 70


def test_read_excursions():
    """
    Тест чтения экскурсий из csv файла
    """
    excursions = get_excursions("excursions.csv")
    assert excursions[0].name == "Best churches"


def test_write_course():
    """
    Тест записи городов в csv файла
    """
    current_course = [City("Berlin", 8, 8, "starting point")]
    write_course(current_course, 'output2.csv')
    with open('output2.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for i in reader:
            current_course.append(City(i['Название города'],
                                       i['Время приезда'],
                                       i['Время убытия'],
                                       i['Экскурсия/остановка']))
    assert current_course[0].name == "Berlin"


@pytest.mark.asyncio
async def test_graph_creation():
    """
    Тест создания матрицы графа городов
    """
    with mock.patch('graph.create_distances') as AsyncMock:
        AsyncMock.return_value = [[1, 2, 20], [1, 3, 30], [2, 3, 10]]
        cities = [1, 2, 3]
        graph = await create_graph(cities)
        assert graph[1][2] == 20


def test_create_courses_one():
    """
    Тест генерации случайной последовательности городов
    """
    cities = [1, 2, 3]
    temp = create_courses(cities)
    assert next(temp) == [3, 2, 1]


def test_create_courses_amount():
    """
    Тест общего количества последовательностей городов
    """
    cities = [1, 2, 3]
    for index, _ in enumerate(create_courses(cities)):
        pass
    assert index == 5


@pytest.mark.asyncio
async def test_count_course():
    """
    Тест рачёта длительности тура
    """
    with mock.patch('graph.create_distances') as AsyncMock:
        AsyncMock.return_value = [[1, 2, 20], [1, 3, 50], [1, 4, 10],
                                  [2, 3, 10], [2, 4, 30], [3, 4, 100]]
        cities = [1, 2, 3, 4]
        graph = await create_graph(cities)
        assert count_course([1, 2, 3, 4], graph) == 140


def test_create_datetime():
    """
    Тест задания времени в формате часы, минуты по времени в часах
    """
    assert create_datetime(
        datetime.datetime(year=1, month=1, day=1),
        6.5
    ).minute == 30


@pytest.mark.asyncio
async def test_put_middle_city_in_finish_course():
    """
    Тест нахождения завершающего тур города
    """
    middle_city = await put_middle_city("A", "B", 0, 8, 70, starting_city="B",
                                        current_datetime=datetime.datetime(
                                            year=1, month=1, day=1))
    assert middle_city[0].name == 'B'


@pytest.mark.asyncio
async def test_put_middle_city_distance_less_than_max():
    """
    Тест нахождения города с экскурсией
    """
    with mock.patch('main.create_excursion_city') as MockClass:
        MockClass.return_value = 1
        middle_city = await put_middle_city("A", "B", 0, 8, 70, None)
        assert middle_city == 1


@pytest.mark.asyncio
async def test_put_middle_city_distance_more_than_max_distance_next_less_than_max():
    """
    Тест нахождения промежуточного города
    """
    with mock.patch('main.find_middle_city') as MockClass:
        MockClass.return_value = City(1, 1, 1, 1)
        middle_city = await put_middle_city("A", "B", 6, 8, 280,
                                            current_datetime=datetime.datetime(
                                                year=1, month=1, day=1))
        assert middle_city[0].name == 1


@pytest.mark.asyncio
async def test_put_middle_city_in_distance_more_than_max_distance_next_more_than_max():
    """
    Тест нахождения промежуточного города, при наличии следющего промежуточного города
    """
    with mock.patch('main.find_middle_city') as MockClass:
        MockClass.side_effect = [City(1, 1, 1, 1), City(2, 2, 2, 2)]
        middle_city = await put_middle_city("A", "B", 6, 8, 280,
                                            current_datetime=datetime.datetime(
                                                year=1, month=1, day=1))
        assert middle_city[0].name == 1


@pytest.mark.asyncio
async def test_put_middle_city_in_finish_course_distance_more_than_max_distance_finish_course():
    """
    Тест нахождения завершающего тур города на следующий день
    """
    with mock.patch('main.find_middle_city') as MockClass:
        MockClass.return_value = None
        middle_city = await put_middle_city("A", "B", 6, 8, 140,
                                            starting_city="B",
                                            current_datetime=datetime.datetime(
                                                year=1, month=1, day=1))
        assert middle_city[0].name == 'B'


@pytest.mark.asyncio
async def test_put_middle_city_distance_more_than_max_distance_nonreachable_next_city():
    """
    Тест нахождения промежуточного города на следующий день, так как в текущем
    промежуточные не достижимы
    """
    with mock.patch('main.find_middle_city') as MockClass:
        MockClass.side_effect = [None, City(2, 2, 2, 2)]
        middle_city = await put_middle_city("A", "B", 6, 8, 140,
                                            current_datetime=
                                            datetime.datetime(
                                                            year=1,
                                                            month=1,
                                                            day=1))
        assert middle_city[0] == 2


@pytest.mark.asyncio
async def test_put_middle_city_distance_more_than_max_distance_reachable_next_city():
    """
    Тест нахождения следующего города на следующий день
    """
    with mock.patch('main.find_middle_city') as MockClass1:
        MockClass1.return_value = None
        with mock.patch('main.create_excursion_city') as MockClass:
            MockClass.return_value = [1]
            middle_city = await put_middle_city("A", "B", 6, 8, 140,
                                                current_datetime=
                                                datetime.datetime(
                                                                year=1,
                                                                month=1,
                                                                day=1))
            assert middle_city[0] == 1


def test_create_excursion_city():
    """
    Тест создания информации о городе с экскурсией
    """
    excursions = [Excursion('Best churches', 'Berlin', '09:00, 14:00, 16:00',
                            '4h')]
    city = create_excursion_city("Berlin", excursions, 10, 70, 3,
                                 datetime.datetime(year=1, month=1, day=1))
    assert city[0].name == 'Berlin'


@pytest.mark.asyncio
async def test_create_course_without_middle_cities():
    """
    Тест создания информации о городе с экскурсией
    """
    with mock.patch('main.put_middle_city') as MockClass:
        MockClass.return_value = City(2,1,1,'B')
        current_course = [1, 2]
        current_course = await create_course_
        with_middle_cities(current_course, None, None,
                                        current_datetime =
                                        datetime.datetime(
                                            year=1,
                                            month=1,
                                            day=1),
                                        current_time=8)
        assert current_course[1].name == 2


@pytest.mark.asyncio
async def test_create_course_with_middle_cities():
    """
    Тест задания тура с промежуточным городом
    """
    with mock.patch('main.put_middle_city') as MockClass:
        MockClass.side_effect = [City(3, 1, 1, 'Stop'), City(2,1,1,'B')]
        current_course = [1, 2]
        current_course = await create_course_
        with_middle_cities(current_course, None, None,
                           current_datetime=
                           datetime.datetime(
                               year=1,
                               month=1,
                               day=1),
                           current_time=8)
        assert current_course[1].name == 3


@pytest.mark.asyncio
async def test_complete_course_without_middle_city():
    """
    Тест завершения тура без промежуточных городов
    """
    with mock.patch('graph.create_distances') as AsyncMock:
        AsyncMock.return_value = [[1, 2, 20], [1, 3, 30], [2, 3, 10]]
        cities = [1, 2, 3]
        graph = await create_graph(cities)
        with mock.patch('main.put_middle_city') as MockClass1:
            MockClass1.return_value = (City(1, 1, 1, 1), 3)
            current_course = [City(2, 1, 1, 1)]
            current_course = await complete_course(current_course, 0, 8, 1,
                                                   graph, None)
            assert current_course[1].name == 1


@pytest.mark.asyncio
async def test_complete_course_with_middle_cities():
    """
    Тест завершения тура с промежуточным городом
    """
    with mock.patch('graph.create_distances') as AsyncMock:
        AsyncMock.return_value = [[1, 2, 20], [1, 3, 30], [2, 3, 10]]
        cities = [1, 2, 3]
        graph = await create_graph(cities)
        with mock.patch('main.put_middle_city') as MockClass1:
            MockClass1.side_effect = ([City(3, 1, 1, 1), [3, None, None,
                                                          None]],
                                      [City(1, 1, 1, 1), None])
            current_course = [City(1, 1, 1, 1), City(2, 1, 1, 1)]
            current_course = await complete_course(current_course, 0,
                                                   8, 1, graph, None)
            assert current_course[2].name == 3
