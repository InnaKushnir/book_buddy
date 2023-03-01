from aiogram import Dispatcher
import telebot
import os


API_KEY = os.environ.get("API_KEY")


bot = telebot.TeleBot(token=API_KEY)


def new_borrowing(user_id, book_id, title, expected_return_date):
    bot.send_message(417193906, f"New borrowing: user_id - {user_id},\n"
                                      f" book_id {book_id} , {title},\n"
                                f" expected_return_date - {expected_return_date}",
                        parse_mode="html")







if __name__ == '__main__':
    pass
