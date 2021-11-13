import copy


def create_courses(cities: list):
    """
    Генератор перебирающий все возможные расстановки значений из списка cities

    :param cities: Список, расстановки которого нужно перебрать
    :return: Текущая расстановка
    """
    for city in cities:
        temp = copy.copy(cities)
        temp.remove(city)
        if len(temp) > 1:
            temp = create_courses(temp)
            for temp2 in temp:
                temp2.append(city)
                yield temp2
        else:
            yield [temp[0], city]


def count_course(course, graph):
    """
    Функция, оценивающая длину переданного маршрута
    :param graph: Матрица расстояний между городами
    :param course: Маршрут, для оценки
    :return: Длина переданного маршрута
    """
    if course[0] in graph and course[len(course) - 1] in graph[course[0]]:
        distance = graph[course[0]][course[len(course) - 1]]
    else:
        distance = graph[course[len(course) - 1]][course[0]]
    for index, i in enumerate(course[:len(course) - 1]):
        if i in graph and course[index + 1] in graph[i]:
            distance += graph[i][course[index + 1]]
        else:
            distance += graph[course[index + 1]][i]
    return distance
