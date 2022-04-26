import datetime
import json
import logging
import os
import time
import telebot
from typing import Any
from dotenv import load_dotenv
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from db import add_new_user, get_id_user, create_new_request, get_history, update_history_destination, get_id_request, \
	get_data_history, add_date_from_to_request, add_date_to_to_request, update_q_days, add_response_to_history, \
	add_q_hotels
from func import get_start, get_help, get_another_message, get_properties, get_district, get_photo_hotel, form_message

logger = logging.getLogger('bot_logger')
load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'), parse_mode='HTML')


@bot.message_handler(commands=['start'])
def start_message(message: Message) -> None:
	"""
	The function executes the bot command start and sends a welcome message
	:param message: start bot command
	:return: None
	"""
	add_new_user(message)
	id_user = get_id_user(message)
	bot.send_message(id_user, get_start())


@bot.message_handler(commands=['help'])
def help_message(message: Message) -> None:
	"""
	The function executes the bot command help and sends a help message
	:param message: help bot command
	:return: None
	"""
	id_user = get_id_user(message)
	bot.send_message(id_user, get_help())


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def action_message(message: Message) -> None:
	"""
	The function executes the bot command lowprice or highprice or bestdeal and sends a request to the search city
	:param message: lowprice bot command  or highprice bot command or bestdeal bot command
	:return: None
	"""
	id_user = get_id_user(message)
	create_new_request(message, id_user)
	bot.send_message(id_user, 'Введите город поиска на английском языке:')
	bot.register_next_step_handler(message, get_id_hotels)


@bot.message_handler(commands=['history'])
def history_message(message: Message) -> None:
	"""
	The function executes the bot command history and sends the history of the last 10 user requests
	:param message: history bot command
	:return: None
	"""
	logger.info(f'Start history query')
	id_user = get_id_user(message)
	list_history = get_history(message)
	if len(list_history) == 0:
		bot.send_message(message.chat.id, 'Пока пусто')
	else:
		for elem in list_history:
			text = ''
			text += f"<b>дата запроса - {elem[0]}</b> "
			text += f"<b>команда - {elem[1]}</b> "
			text += f"<b>город - {elem[2]}</b> "
			bot.send_message(id_user, text)
			try:
				json.loads(elem[3])
				for hotel in json.loads(elem[3]):
					text = ''
					text += f"<b>отель - {hotel['name']}</b>\n"
					text += f"<b>стоимость - {hotel['current']}</b>\n"
					text += f"<b>ссылка - {hotel['url']}</b>\n"
					bot.send_message(id_user, text, disable_web_page_preview=True)
					time.sleep(0.2)
			except:
				logger.error(f'No history')
				text = 'Ничего не нашлось'
				bot.send_message(id_user, text)
			time.sleep(0.5)
	logger.info(f'End history query')
	bot.send_message(id_user, 'Чем я еще могу вам помочь?')
	bot.send_message(id_user, get_help())


@bot.message_handler(content_types=['text'])
def another_message(message: Message) -> None:
	"""
	The function sends a help message
	:param message: any text or command for which no handler is defined
	:return: None
	"""
	id_user = get_id_user(message)
	bot.send_message(id_user, get_another_message())


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: CallbackQuery) -> None:
	"""
	The object handler function for incoming callback requests from built-in keyboard callback buttons
	:param call: object of type CallbackQuery of class telebot
	:return: None
	"""
	id_user = call.from_user.id
	if '***' in call.data:
		id_destination = int(call.data.split('***')[0])
		name_destination = call.data.split('***')[1]
		update_history_destination(id_destination, name_destination, id_user)
		calendar, step = DetailedTelegramCalendar(min_date=datetime.date.today(), locale='ru').build()
		bot.edit_message_text(f"Выберите дату заезда: {LSTEP[step]}",
							  id_user,
							  call.message.message_id,
							  reply_markup=calendar)
	elif 'да' in call.data or 'нет' in call.data:
		if 'да' in call.data:
			msg = bot.edit_message_text('Сколько фотографий для каждого отеля необходимо вывести (не более 5)',
										id_user, call.message.message_id)
			bot.register_next_step_handler(msg, get_photo, id_user)
		else:
			list_links_photo = []
			get_answer(id_user, list_links_photo, None)
	else:
		id_request = get_id_request(id_user)
		date_from, date_to, command, id_destination, name_destination = get_data_history(id_request)[:5]
		min_date = datetime.date.today() if not date_from else datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
		max_date = None if not date_from else (
				datetime.datetime.strptime(date_from, "%Y-%m-%d") + datetime.timedelta(days=28)).date()
		result, calendar, step = DetailedTelegramCalendar(min_date=min_date, max_date=max_date, locale='ru').process(
			call.data)

		if not result and calendar:
			bot.edit_message_text(f"{LSTEP[step]}",
								  id_user, call.message.message_id, reply_markup=calendar)
		elif result:
			if not date_from:
				add_date_from_to_request(id_request, result)
				calendar, step = DetailedTelegramCalendar(min_date=datetime.datetime.now().date(), locale='ru').build()
				bot.edit_message_text(f"Выберите дату отъезда: {LSTEP[step]}",
									  id_user,
									  call.message.message_id,
									  reply_markup=calendar)
			elif not date_to:
				date_to = result
				date_from = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
				add_date_to_to_request(id_request, result)
				if date_from != date_to:
					q_days = (date_to - date_from).days
					update_q_days(q_days, id_request)
				if command == '/bestdeal':
					msg = bot.send_message(call.message.chat.id, 'Введите минимальную стоимость отеля в сутки в $')
					bot.register_next_step_handler(msg, get_min_cost, id_user)
				else:
					bot.send_message(call.message.chat.id, 'Подождите, пожалуйста, запрашиваю для вас информацию...')
					get_count_hotel(id_user)


def get_keyboard_district(list_names_districts: list) -> InlineKeyboardMarkup:
	"""
	The function returns an inline keyboard to specify the area of the city
	:param list_names_districts: list of districts for the requested city
	:return: inline keyboard to specify the area of the city
	"""
	keyboard = telebot.types.InlineKeyboardMarkup()
	for name_district in list_names_districts:
		keyboard.row_width = 1
		keyboard.add(telebot.types.InlineKeyboardButton(name_district.name,
														callback_data='***'.join(
															[name_district.id_destination, name_district.name[:20]])))
	return keyboard


def get_id_hotels(message: Message) -> None:
	"""
	The function sends an inline keyboard to specify the area of the city, if a response is received
	from the rapidapi service, or requests the city again in case of a negative response
	:param message: object of type Message of class telebot
					message.text contains the city sent to the bot
	:return: None
	"""
	msg = bot.send_message(message.chat.id, 'Подождите, пожалуйста, запрашиваю для вас информацию...')
	list_class_cities = get_district(message.text)
	if len(list_class_cities) > 0:
		bot.edit_message_text('Уточните, пожалуйста, район:', chat_id=message.chat.id, message_id=msg.message_id,
							  reply_markup=get_keyboard_district(list_class_cities))
	else:
		bot.edit_message_text('Такого города нет!\nПопробуйте еще раз:', chat_id=message.chat.id,
							  message_id=msg.message_id)
		bot.register_next_step_handler(message, get_id_hotels)


def get_min_cost(message: Message, id_user: int):
	"""
	The function asks the client for the minimum desired cost of the hotel and checks the user's response
	:param message: object of type Message of class telebot
					message.text contains the desired minimum hotel price
	:param id_user: unique user number
	:return: None
	"""
	min_cost = message.text
	try:
		float(min_cost)
		msg = bot.send_message(id_user, 'Введите максимальную стоимость отеля в сутки в $')
		bot.register_next_step_handler(msg, get_max_cost, id_user, min_cost)
	except ValueError as ex:
		logger.error(f'Ошибка неверный тип данных минимальная стоимость отеля в сутки в $', exc_info=ex)
		msg = bot.send_message(id_user, f'Вы ввели неправильное число, попробуйте еще раз.\n'
										f'Введите минимальную стоимость отеля в сутки')
		bot.register_next_step_handler(msg, get_min_cost, id_user)


def get_max_cost(message: Message, id_user: int, min_cost: int):
	"""
	The function asks the client for the maximum desired cost of the hotel and checks the user's response
	:param message: object of type Message of class telebot
					message.text contains the desired maximum hotel price
	:param id_user: unique user number
	:param min_cost: desired minimum hotel price
	:return: None
	"""
	max_cost = message.text
	try:
		float(max_cost)
		msg = bot.send_message(id_user, 'Введите минимальную удаленность отеля от центра в милях')
		bot.register_next_step_handler(msg, get_min_dist, id_user, min_cost, max_cost)
	except ValueError as ex:
		logger.error(f'Ошибка неверный тип данных максимальная стоимость отеля в сутки в $', exc_info=ex)
		msg = bot.send_message(id_user, f'Вы ввели неправильное число, попробуйте еще раз.\n'
										f'Введите максимальную стоимость отеля в сутки')
		bot.register_next_step_handler(msg, get_max_cost, id_user, min_cost)


def get_min_dist(message: Message, id_user: int, min_cost: int, max_cost: int):
	"""
	The function asks the client for the minimum desired distance of the hotel from the center
	 and checks the user's response
	:param message: object of type Message of class telebot
					message.text contains the desired minimum distance of the hotel from the center
	:param id_user: unique user number
	:param min_cost: desired minimum hotel price
	:param max_cost: desired maximum hotel price
	:return: None
	"""
	min_dist = message.text
	try:
		float(min_dist)
		msg = bot.send_message(id_user, 'Введите максимальную удаленность отеля от центра в милях')
		bot.register_next_step_handler(msg, get_max_dist, id_user, min_cost, max_cost, min_dist)
	except ValueError as ex:
		logger.error(f'Ошибка неверный тип данных минимальная удаленность отеля от центра в милях', exc_info=ex)
		msg = bot.send_message(id_user, f'Вы ввели неправильное число, попробуйте еще раз.\n'
										f'Введите минимальную удаленность отеля от центра')
		bot.register_next_step_handler(msg, get_min_dist, id_user, min_cost, max_cost)


def get_max_dist(message: Message, id_user: int, min_cost: int, max_cost: int, min_dist: int):
	"""
	The function asks the client for the maximum desired distance of the hotel from the center
	 and checks the user's response
	:param message: object of type Message of class telebot
					message.text contains the desired maximum distance of the hotel from the center
	:param id_user: unique user number
	:param min_cost: desired minimum hotel price
	:param max_cost: desired maximum hotel price
	:param min_dist: desired minimum distance of the hotel from the center
	:return: None
	"""
	max_dist = message.text
	try:
		float(max_dist)
		bot.send_message(message.chat.id, 'Подождите, пожалуйста, запрашиваю для вас информацию...')
		get_count_hotel(id_user, min_cost, max_cost, min_dist, max_dist)
	except ValueError as ex:
		logger.error(f'Ошибка неверный тип данных максимальная удаленность отеля от центра в милях', exc_info=ex)
		msg = bot.send_message(id_user, f'Вы ввели неправильное число, попробуйте еще раз.\n'
										f'Введите  максимальную удаленность отеля от центра')
		bot.register_next_step_handler(msg, get_max_dist, id_user, min_cost, max_cost, min_dist)


def get_count_hotel(id_user: int, min_cost: int = None, max_cost: int = None, min_dist: int = None,
					max_dist: int = None):
	"""
	The function asks the client for the desired quantity hotels for output and checks the user's response
	or sends a response to the user that nothing was found
	:param id_user: unique user number
	:param min_cost: desired minimum hotel price
	:param max_cost: desired maximum hotel price
	:param min_dist: desired minimum distance of the hotel from the center
	:param max_dist: desired maximum distance of the hotel from the center
	:return: None
	"""
	id_request = get_id_request(id_user)
	date_from, date_to, command, id_destination, name_destination = get_data_history(id_request)[:5]
	order_by = 'PRICE_HIGHEST_FIRST' if command == '/highprice' else 'PRICE'
	if command == '/bestdeal':
		tmp_list_hotels = get_properties(id_destination, date_from, date_to, order_by, min_cost, max_cost)
		list_hotels = list(
			filter(lambda x: int(min_dist) <= float(x['distance'].split()[0]) <= int(max_dist), tmp_list_hotels))
	else:
		list_hotels = get_properties(id_destination, date_from, date_to, order_by)
	response = json.dumps(list_hotels)
	add_response_to_history(id_user, response)
	if len(list_hotels) != 0:
		max_q_hotels = len(list_hotels)
		msg = bot.send_message(id_user, f"Вы выбрали {name_destination}"
										f" c {date_from} по {date_to}\n"
										f"Какое кол-во отелей вывести в диапазоне от 1"
										f" до {max_q_hotels}?")
		bot.register_next_step_handler(msg, need_a_photo, max_q_hotels)
	else:
		bot.send_message(id_user, f"К сожалению по данному запросу ничего не найдено")
		response = 'Ничего не нашлось'
		add_response_to_history(id_user, response)
		bot.send_message(id_user, 'Чем я еще могу вам помочь?')
		bot.send_message(id_user, get_help())


def get_keyboard_photo():
	"""
	The function returns a built-in keyboard with yes or no answer buttons
	:return: inline keyboard а built-in keyboard with yes or no answer buttons
	"""
	keyboard = telebot.types.InlineKeyboardMarkup()
	keyboard.row_width = 1
	keyboard.add(telebot.types.InlineKeyboardButton('ДА', callback_data='да'),
				 telebot.types.InlineKeyboardButton('НЕТ', callback_data='нет'))

	return keyboard


def need_a_photo(message: Message, max_q_hotels: int) -> None:
	"""
	The function checks the possibility of displaying the requested number of hotels
	and requests the need to display photos
	:param message: object of type Message of class telebot
					message.text contains the number of hotels received from the user to be displayed
	:param max_q_hotels: the maximum number of hotels that can be displayed
	:return: None
	"""
	id_user = get_id_user(message)
	if int(message.text) > max_q_hotels or int(message.text) < 1:
		msg = bot.send_message(id_user, f'Вы ввели неправильное число, попробуйте еще раз.\n'
										f'Какое кол-во отелей вывести в диапазоне'
										f' от 1 до {max_q_hotels}?')
		bot.register_next_step_handler(msg, need_a_photo, max_q_hotels)
	else:
		add_q_hotels(id_user, int(message.text))
		bot.send_message(id_user, f'Загрузить фото?', reply_markup=get_keyboard_photo())


def get_photo(message: Message, id_user: int) -> None:
	"""
	The function creates a list of links photos for each hotel
	and passes it to the function to display a response to the user
	:param message: object of type Message of class telebot
					message.text contains the number of photos to display for each hotel
	:param id_user: unique user number
	:return: None
	"""
	if 0 < int(message.text) <= 5:
		msg = bot.send_message(id_user, 'Подождите, пожалуйста, запрашиваю для вас информацию...')
		q_photo = int(message.text)
		list_links_photo = get_photo_hotel(q_photo, id_user)
		get_answer(id_user, list_links_photo, msg)
	else:
		msg = bot.send_message(id_user, f'Вы ввели неправильное число, попробуйте еще раз.\n'
										f'Сколько фотографий для каждого отеля необходимо вывести (не более 5)')
		bot.register_next_step_handler(msg, get_photo, id_user)


def get_answer(id_user: int, list_links_photo: list, msg: Any) -> None:
	"""
	The function sends the generated response to the request to the user
	:param id_user: unique user number
	:param list_links_photo: list of links to photo for each hotel
	:param msg:
	:return:
	"""
	answer = form_message(id_user)
	if msg:
		bot.edit_message_text(answer[0], chat_id=msg.chat.id, message_id=msg.message_id)
	else:
		bot.send_message(id_user, answer[0])
	for i, hotel in enumerate(answer[1:]):
		bot.send_message(id_user, hotel, disable_web_page_preview=True)
		media_group = []
		if list_links_photo:
			try:
				for link in list_links_photo[i]:
					if link != 'нет данных':
						media_group.append(telebot.types.InputMediaPhoto(media=link))
				bot.send_media_group(id_user, media=media_group)
			except:
				logger.error(f'No photo')
				bot.send_message(id_user, 'нет фото')
		time.sleep(0.5)
	logger.info(f'End request')
	bot.send_message(id_user, 'Чем я еще могу вам помочь?')
	bot.send_message(id_user, get_help())


if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO, filename='bot.log', filemode='a',
						format='%(asctime)s - %(levelname)s - %(message)s',
						datefmt='%d-%b-%y %H:%M:%S')
	logger.info(f'Start bot "Choosing_hotels_bot"')
	bot.polling(none_stop=True)
