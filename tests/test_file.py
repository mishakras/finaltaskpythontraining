import json

import mock
import pytest

from main import (complete_course, create_course_with_middle_cities,
                  create_excursion_city, create_graph, get_excursions,
                  put_middle_city, write_course)


def test_read_configs():
    with open('config.json') as f:
        configs = json.load(f)
    assert configs['velocity'] == 70


def test_read_excursions():
    excursions = get_excursions("excursions.csv")
    assert excursions[0]['Name'] == "Best churches"


def test_write_excursions():
    current_course = [["Berlin", 8, 8, "starting point"]]
    write_course(current_course, 'output2.csv')
    excursions = get_excursions("output2.csv")
    assert excursions[0]['Название города'] == "Berlin"


@pytest.mark.asyncio
async def test_graph_creation():
    with mock.patch('main.create_distances') as AsyncMock:
        AsyncMock.return_value = [[2, 20], [3, 30], [1, 20], [3, 10], [1, 30], [2, 10]]
        cities = [1, 2, 3]
        graph = await create_graph(cities)
        assert graph[1][2] == 20


def test_excursion_city():
    excursions = [{'Name': 'Best churches', 'City': 'Berlin', 'Start time': '09:00, 14:00, 16:00', 'Duration': '4h'}]
    city = create_excursion_city("Berlin", excursions, 10, 70, 3)
    assert city == (['Berlin', 11.0, 18.0, 'Best churches'], 4.0)


@pytest.mark.asyncio
async def test_put_middle_city_in_finish_course():
    middle_city = await put_middle_city("A", "B", 0, 8, 70, starting_city="B")
    assert middle_city == (['B', 9.0, 8, 'Ending point'], None)


@pytest.mark.asyncio
async def test_put_middle_city_distance_less_than_max_default():
    with mock.patch('main.create_excursion_city') as MockClass:
        MockClass.return_value = 1
        middle_city = await put_middle_city("A", "B", 0, 8, 70)
        assert middle_city == 1


@pytest.mark.asyncio
async def test_put_middle_city_in_finish_course_distance_more_than_max_distance():
    with mock.patch('main.find_middle_city') as MockClass:
        MockClass.return_value = None
        middle_city = await put_middle_city("A", "B", 6, 8, 140, starting_city="B")
        assert middle_city == (['B', 10.0, 8, 'Ending point'], None)


@pytest.mark.asyncio
async def test_put_middle_city_distance_more_than_max_distance_reachable_end_city():
    with mock.patch('main.find_middle_city') as MockClass1:
        MockClass1.return_value = None
        with mock.patch('main.create_excursion_city') as MockClass:
            MockClass.return_value = 1
            middle_city = await put_middle_city("A", "B", 6, 8, 140)
            assert middle_city == 1


@pytest.mark.asyncio
async def test_put_middle_city_distance_more_than_max_distance_unreachable_end_city():
    with mock.patch('main.find_middle_city') as MockClass1:
        MockClass1.return_value = ["C", 280]
        with mock.patch('main.create_excursion_city') as MockClass:
            MockClass.return_value = 1
            middle_city = await put_middle_city("A", "B", 6, 8, 140)
            assert middle_city == (['C', 12.0, 8, 'Stopping point', -140], 0)


@pytest.mark.asyncio
async def test_complete_course_without_middle_city():
    with mock.patch('main.create_distances') as AsyncMock:
        AsyncMock.return_value = [[2, 20], [3, 30], [1, 20], [3, 10], [1, 30], [2, 10]]
        cities = [1, 2, 3]
        await create_graph(cities)
        with mock.patch('main.put_middle_city') as MockClass1:
            MockClass1.return_value = ([1], 3)
            current_course = [[2]]
            current_course = await complete_course(current_course, 0, 8, 1)
            assert current_course[1] == [1]


@pytest.mark.asyncio
async def test_create_course_with_middle_cities_one_city():
    current_course = [1]
    current_course = await create_course_with_middle_cities(current_course, 1)
    assert current_course[0][0] == [1, 8, 8, "starting point"]
