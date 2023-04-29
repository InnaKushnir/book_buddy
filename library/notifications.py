import telebot
import os
from django.db import models
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods


API_KEY = os.environ.get("API_KEY")
BOT_NUMBER = os.environ.get("BOT_NUMBER")


bot = telebot.TeleBot(token=API_KEY)


def new_borrowing(borrowing_id, user_id, book_id, title, expected_return_date):
    bot.send_message(
        BOT_NUMBER,
        f"New borrowing:{borrowing_id}, user_id - {user_id},\n"
        f" book_id {book_id} , {title},\n"
        f" expected_return_date - {expected_return_date}",
        parse_mode="html",
    )

def overdue_borrowing(id, book_id, title, expected_return_date):
    bot.send_message(
        BOT_NUMBER,
        f"Overdue borrowing: id -{id}, \n"
        f"book_id {book_id} ,{title},\n"
        f"expected_return_date - {expected_return_date}",
    )

def not_overdue():
    bot.send_message(BOT_NUMBER, "No borrowings overdue today!")
