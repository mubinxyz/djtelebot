# bot/bot.py
import telebot
from telebot import types
from django.conf import settings
from ..models import TelegramUser


class DjangoBot:
    def __init__(self):
        self.bot = telebot.TeleBot(settings.BOT_TOKEN, parse_mode="HTML")
        self._register_handlers()

    def _register_handlers(self):
        @self.bot.message_handler(commands=["start"])
        def start(message):
            user, created = TelegramUser.objects.get_or_create(
                chat_id=message.chat.id,
                defaults={
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                },
            )
            self.bot.send_message(
                message.chat.id,
                f"👋 Welcome {user.first_name or 'friend'}! You’re now registered.",
            )

        @self.bot.message_handler(commands=["menu"])
        def menu(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Option 1", "Option 2")
            self.bot.send_message(
                message.chat.id, "Choose an option:", reply_markup=markup
            )

        @self.bot.message_handler(func=lambda m: m.text.lower() == "hi")
        def say_hi(message):
            self.bot.send_message(message.chat.id, "👋 Hi there, welcome!")

        @self.bot.message_handler(func=lambda m: True)
        def echo(message):
            user = TelegramUser.objects.filter(chat_id=message.chat.id).first()
            if user:
                user.last_message = message.text
                user.save()
            self.bot.send_message(message.chat.id, f"You said: {message.text}")

    def process_update(self, json_str: str):
        """Called by Django view when Telegram sends an update"""
        update = telebot.types.Update.de_json(json_str)
        self.bot.process_new_updates([update])

    def set_webhook(self):
        """Helper function if you want to reset webhook manually"""
        self.bot.remove_webhook()
        self.bot.set_webhook(
            url=settings.WEBHOOK_URL,
            drop_pending_updates=True,
        )
        print("✅ Webhook set successfully!")

# create a global instance for import
django_bot = DjangoBot()
