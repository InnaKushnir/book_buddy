import telebot
import os
from django.db import models
from django.conf import settings


API_KEY = os.environ.get("API_KEY")


bot = telebot.TeleBot(token=API_KEY)


def new_borrowing(user_id, book_id, title, expected_return_date):
    bot.send_message(417193906, f"New borrowing: user_id - {user_id},\n"
                                      f" book_id {book_id} , {title},\n"
                                f" expected_return_date - {expected_return_date}",
                        parse_mode="html")

def over_(id, book_id, title, expected_return_date):
    bot.send_message(
        417193906, f"Overdue borrowing: id -{id}, \n"
                                f"book_id {book_id} ,{title},\n"
                                f"expected_return_date - {expected_return_date}"
    )

def not_overdue():
    bot.send_message(417193906, "No borrowings overdue today!")
