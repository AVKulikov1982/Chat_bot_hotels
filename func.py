from datetime import date

import requests
import json
import os
from dotenv import load_dotenv
import logging

import db

load_dotenv()
logger = logging.getLogger(__name__)


class City:
	"""

	"""

	def __init__(self, name: str, id_destination_group: str):
		self.__name = name
		self.__id_destination = id_destination_group

	@property
	def id_destination(self):
		return self.__id_destination

	@property
	def name(self):
		return self.__name


def get_start() -> str:
	"""
	The function returns a welcome message
	:return: welcome message
	"""
	return "Привет!\nДля демонстрации возможностей бота введите команду /help"


def get_help() -> str:
	"""
	The function returns a help message
	:return: help message
	"""
	return 'Этот бот выполняет следующие команды:\n' \
		   '<b>/start</b> - запуск бота,\n' \
		   '<b>/help</b> - вызов справочного сообщения,\n' \
		   '<b>/lowprice</b> - топ самых дешёвых отелей в городе,\n' \
		   '<b>/highprice</b> - топ самых дорогих отелей в городе,\n' \
		   '<b>/bestdeal</b> - топ отелей, наиболее подходящих по цене и расположению от центра,\n' \
		   '<b>/history</b> - история поиска\n'


def get_district(city: str) -> list:
	"""
	The function makes a request through the rapidapi service and
	returns a list of districts of the city specified in the request
	:param city: the city in which the user is looking for hotels
	:return: list of districts of the city specified in the request
	"""
	list_class_cities = []
	url_location = os.getenv('url_api') + "locations/v2/search"
	headers = {
		'x-rapidapi-host': os.getenv('x-rapidapi-host'),
		'x-rapidapi-key': os.getenv('HOTELS_RU_TOKEN3')
	}
	querystring_location = {"query": city.lower(), "locale": "en_EN", "currency": "USD"}

	response_location = requests.request("GET", url_location, headers=headers, params=querystring_location)

	try:
		if response_location.status_code == 200:
			data_location = json.loads(response_location.text)
			if data_location.get('suggestions'):
				for value in data_location['suggestions']:
					if value.get('group') and value['group'] == 'CITY_GROUP' and value['entities']:
						for district in value['entities']:
							list_class_cities.append(City(district['name'], district['destinationId']))
						return list_class_cities
			else:
				raise ValueError
	except ValueError as ex:
		logger.error(f'Ошибка GET запроса к сервису rapidapi.com/locations/v2/search. Нет данных', exc_info=ex)


def get_properties(id_destination: int, date_from: date, date_to: date, order_by: str, min_cost=None,
				   max_cost=None) -> list:
	"""
	The function makes a request through the rapidapi service and
	returns a list of hotels suitable on request
	:param id_destination: unique destination number
	:param date_from: arrival date
	:param date_to: departure date
	:param order_by: hotel sorting method
	:param min_cost: minimal price
	:param max_cost: maximal price
	:return: list of hotels suitable on request
	"""
	list_result = []
	url_properties_list = os.getenv('url_api') + "properties/list"
	headers_properties_list = {'x-rapidapi-key': os.getenv('HOTELS_RU_TOKEN3'),
							   'x-rapidapi-host': os.getenv('x-rapidapi-host')}
	if min_cost and max_cost:
		querystring_properties_list = {"adults1": "1", "pageNumber": "1", "destinationId": id_destination, "pageSize": "15",
									   "checkOut": date_to, "checkIn": date_from, "priceMin": min_cost, "priceMax": max_cost,
									   "sortOrder": order_by, "locale": "en_EN", "currency": "USD"}
	else:
		querystring_properties_list = {"adults1": "1", "pageNumber": "1", "destinationId": id_destination, "pageSize": "15",
									   "checkOut": date_to, "checkIn": date_from, "sortOrder": order_by,
									   "locale": "en_EN", "currency": "USD"}
	response_properties_list = requests.request("GET", url_properties_list,
												headers=headers_properties_list,
												params=querystring_properties_list)
	try:
		if response_properties_list.status_code == 200:
			data_properties_list = json.loads(response_properties_list.text)
			if data_properties_list.get('data') and data_properties_list['data'].get('body') and \
					data_properties_list['data']['body'].get('searchResults') and \
					data_properties_list['data']['body']['searchResults'].get('results'):
				for hotel in data_properties_list['data']['body']['searchResults']['results']:
					tmp_dict = {'id': '', 'name': '', 'current': 'нет данных', 'address': 'нет данных',
								'distance': 'нет данных', 'url': 'нет данных'}
					if hotel.get('id'):
						tmp_dict['id'] = str(hotel['id'])
					if hotel.get('name'):
						tmp_dict['name'] = hotel['name']
					if hotel.get('ratePlan'):
						if hotel['ratePlan'].get('price'):
							if hotel['ratePlan']['price'].get('exactCurrent'):
								tmp_dict['current'] = hotel['ratePlan']['price']['exactCurrent']
					if hotel.get('address'):
						if hotel['address'].get('locality') and hotel['address'].get('streetAddress'):
							tmp_dict['address'] = ', '.join([hotel['address']['locality'],
															 hotel['address']['streetAddress']])
					if hotel.get('landmarks'):
						if hotel['landmarks'][0].get('distance'):
							tmp_dict['distance'] = hotel['landmarks'][0]['distance']
					tmp_dict['url'] = f'https://ru.hotels.com/ho{tmp_dict["id"]}'
					list_result.append(tmp_dict)
	except:
		logger.error(f'Ошибка GET запроса к сервису rapidapi.com/properties/list. Нет данных по отелям')

	return list_result


def get_photo_hotel(q_photo: int, id_user: int) -> list:
	"""
	The function makes a request through the rapidapi service and
	returns a list of photo links for each hotel
	:param q_photo: number of photos required for issuance for each hotel
	:param id_user: unique user number
	:return: list of photo links for each hotel
	"""
	list_links_photo = []
	id_request = db.get_id_request(id_user)
	data_history = db.get_data_history(id_request)[6:]
	q_hotels = data_history[0]
	list_hotels = json.loads(data_history[1])[:q_hotels]
	for hotel in list_hotels:
		url_photo = os.getenv('url_api') + "properties/get-hotel-photos"
		querystring = {"id": hotel["id"]}
		headers = {
			'x-rapidapi-host': os.getenv('x-rapidapi-host'),
			'x-rapidapi-key': os.getenv('HOTELS_RU_TOKEN3')
		}
		response_photo = requests.request("GET", url_photo, headers=headers, params=querystring)
		try:
			if response_photo.status_code == 200:
				data = json.loads(response_photo.text)
				if data.get('hotelImages'):
					list_photo = data['hotelImages'][:q_photo]
					list_links = []
					for photo in list_photo:
						link = photo['baseUrl'].format(size='b')
						list_links.append(f'{link}')
					list_links_photo.append(list_links)
		except:
			list_links_photo.append('нет данных')
			logger.error(f'Ошибка GET запроса к сервису rapidapi.com/properties/get-hotel-photos Нет данных по фото')

	return list_links_photo


def form_message(id_user: int) -> list:
	"""
	The function receives the query result from the database and generates a message for output to the user
	:param id_user: unique user number
	:return: message for output to the user
	"""
	answer = []
	id_request = db.get_id_request(id_user)
	date_from, date_to, command, id_destination, name_destination, q_days, q_hotels, response = db.get_data_history(
		id_request)
	list_hotels = json.loads(response)[:q_hotels]
	if command == '/lowprice':
		answer.append(f'<b>Список отелей с минимальной стоимостью в $ за период: '
					  f'c {date_from} по {date_to}</b>\n')
	elif command == '/highprice':
		answer.append(f'<b>Список отелей с максимальной стоимостью в $ за выбранный период: '
					  f'c {date_from} по {date_to}</b>\n')
	elif command == '/bestdeal':
		answer.append(f'<b>Список отелей с минимальной стоимостью в $ ближайших к центру за выбранный период: '
					  f'c {date_from} по {date_to}</b>\n')

	for index, hotel in enumerate(list_hotels):
		if hotel["current"] != 'нет данных':
			price_day = round(int(hotel["current"]) / q_days, 2)
		else:
			price_day = 'нет данных'
		text = f'{hotel["name"]}\n' \
			   f'{hotel["address"]}\n' \
			   f'От центра - {hotel["distance"]}\n' \
			   f'Цена за сутки - {price_day}$.\n' \
			   f'Цена за период - {hotel["current"]}$.\n' \
			   f'{hotel["url"]}\n'
		answer.append(text)
	return answer


def get_another_message():
	"""
	The function returns a help message
	:return: help message
	"""
	return "Привет!\nДля демонстрации возможностей бота введите команду /help"
