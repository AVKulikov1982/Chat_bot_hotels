import datetime
import logging
import os
import sqlite3

from telebot.types import Message

logger = logging.getLogger(__name__)

if not os.path.exists('users.db'):
	con = sqlite3.connect('users.db', check_same_thread=False)
	cur = con.cursor()
	cur.execute('''CREATE TABLE if not exists users (id INTEGER PRIMARY KEY NOT NULL,
	 												 id_user INTEGER NOT NULL,
	 												 first_name TEXT NOT NULL,
	 												 last_name TEXT NOT NULL,
	 												 username TEXT NOT NULL)''')
	cur.execute('''CREATE TABLE if not exists history (id_request INTEGER PRIMARY KEY NOT NULL,
	 												   id_user INTEGER NOT NULL,
	 												   date_request DATE,
	 												   command TEXT,
	 												   id_destination INTEGER,
	 												   name_destination TEXT,
	 												   date_from DATE,
	 												   date_to DATE,
	 												   q_days INTEGER,
	 												   q_hotels INTEGER,
	 												   response TEXT)''')
	logger.info(f'Create db users.db')
else:
	con = sqlite3.connect('users.db', check_same_thread=False)
	cur = con.cursor()
	logger.info(f'Create connect with users.db')


def add_new_user(message: Message) -> None:
	"""
	The function adds a new user to the database
	:param message: object of type Message of class telebot
	:return: None
	"""
	try:
		if cur.execute(f"SELECT id_user FROM users"
					   f" WHERE id_user='{message.from_user.id}'").fetchall():
			raise ValueError
		else:
			cur.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?)",
						(message.from_user.id, message.from_user.first_name,
						 message.from_user.last_name, message.from_user.username))
			con.commit()
			logger.info(f'Add into users.db new user')
	except ValueError:
		logger.info(f'restart bot from user {message.from_user.id}')


def create_new_request(message: Message, id_user: int) -> None:
	"""
	The function adds a new query to the database
	:param message: object of type Message of class telebot
					message.text contains the command sent to the bot
	:param id_user: unique user number
	:return: None
	"""
	cur.execute("INSERT INTO history VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
				(id_user, datetime.date.today(), message.text, 0, '', '', '', 1, 0, ''))
	con.commit()
	logger.info("Create new request")


def get_id_user(message: Message) -> int:
	"""
	The function returns a unique user number
	:param message: object of type Message of class telebot
	:return: unique user number
	"""
	return cur.execute(f"SELECT id_user FROM users WHERE id_user='{message.from_user.id}'").fetchall()[0][0]


def get_history(message: Message) -> list:
	"""
	The function returns a list of the user's query history
	:param message: object of type Message of class telebot
	:return: user query history list
	"""
	list_history = cur.execute(f"SELECT date_request, command, name_destination, response "
							   f"FROM history WHERE id_user='{message.from_user.id}' ORDER BY id_request DESC LIMIT 10").fetchall()
	return list_history


def update_history_destination(id_destination: int, name_destination: str, id_user: int) -> None:
	"""
	The function updates the request data
	:param id_destination: unique city number
	:param name_destination: the name of the city in which the user is looking for hotels
	:param id_user: unique user number
	:return: None
	"""
	cur.execute(
		f"UPDATE history SET id_destination='{id_destination}', name_destination='{name_destination}' WHERE id_request="
		f"(SELECT id_request FROM history WHERE id_user='{id_user}' ORDER BY id_request DESC LIMIT 1)")
	con.commit()
	logger.info(f'Update request')


def get_id_request(id_user: int) -> int:
	"""
	The function returns the last user request from the database
	:param id_user: unique user number
	:return: unique request number
	"""
	id_request = cur.execute(
		f"SELECT id_request FROM history WHERE id_user='{id_user}'"
		f" ORDER BY id_request DESC LIMIT 1").fetchall()[0][0]
	return id_request


def get_data_history(id_request: int) -> tuple:
	"""
	The function returns a tuple of values from the database
	:param id_request: unique request number
	:return: tuple of values from the database
	"""
	date_from = cur.execute(f"SELECT date_from FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	date_to = cur.execute(f"SELECT date_to FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	command = cur.execute(f"SELECT command FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	id_destination = \
		cur.execute(f"SELECT id_destination FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	name_destination = \
		cur.execute(f"SELECT name_destination FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	q_days = \
		cur.execute(f"SELECT q_days FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	q_hotels = \
		cur.execute(f"SELECT q_hotels FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	response = \
		cur.execute(f"SELECT response FROM history WHERE id_request='{id_request}'").fetchall()[0][0]

	return date_from, date_to, command, id_destination, name_destination, q_days, q_hotels, response


def get_q_photo(id_request: int) -> int:
	"""
	The function returns the number of photos required for issuance for each hotel
	:param id_request: unique request number
	:return: number of photos required for issuance for each hotel
	"""
	q_photo = cur.execute(f"SELECT q_photo FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	return q_photo


def get_response(id_request: int) -> str:
	"""
	The function returns query result by unique query number
	:param id_request: unique request number
	:return: query result by unique query number
	"""
	response = cur.execute(f"SELECT response FROM history WHERE id_request='{id_request}'").fetchall()[0][0]
	return response


def add_date_from_to_request(id_request: int, date_from) -> None:
	"""
	The function updates the query with the arrival date
	:param id_request: unique request number
	:param date_from: arrival date
	:return: None
	"""
	cur.execute(f"UPDATE history SET date_from='{date_from}' WHERE id_request='{id_request}'")
	con.commit()


def add_date_to_to_request(id_request: int, date_to) -> None:
	"""
	The function updates the query with the departure date
	:param id_request: unique request number
	:param date_to: departure date
	:return: None
	"""
	cur.execute(f"UPDATE history SET date_to='{date_to}' WHERE id_request='{id_request}'")
	con.commit()


def add_q_hotels(id_user: int, q_hotels: int) -> None:
	"""
	The function updates the query with the number of hotels
	:param id_user: unique user number
	:param q_hotels: number of hotels
	:return: None
	"""
	cur.execute(f"UPDATE history SET q_hotels='{q_hotels}' WHERE id_request="
				f"(SELECT id_request FROM history WHERE id_user='{id_user}' ORDER BY id_request DESC LIMIT 1)")
	con.commit()


def update_q_days(q_days: int, id_request: int) -> None:
	"""
	The function updates the query with the number of days
	:param q_days: number of days
	:param id_request: unique request number
	:return: None
	"""
	cur.execute(f"UPDATE history SET q_days='{q_days}' WHERE id_request='{id_request}'")
	con.commit()


def add_response_to_history(id_user: int, response: str) -> None:
	"""
	The function updates the query with the response
	:param id_user: unique user number
	:param response: query result
	:return:
	"""
	response = response.replace("'", "`")
	cur.execute(f"UPDATE history SET response='{response}' WHERE id_request="
				f"(SELECT id_request FROM history WHERE id_user='{id_user}' ORDER BY id_request DESC LIMIT 1)")
	con.commit()
