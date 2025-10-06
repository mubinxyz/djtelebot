import telebot
from django.conf import settings
from .models import TelegramUser

bot = telebot.TeleBot(settings.BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    user, created = TelegramUser.objects.get_or_create(
        chat_id=message.chat.id,
        defaults={
            'username': message.from_user.username,
            'first_name': message.from_user.first_name
        }
    )
    text = f"Welcome, {user.first_name or 'friend'}! 👋"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: True)
def echo(message):
    user = TelegramUser.objects.filter(chat_id=message.chat.id).first()
    if user:
        user.last_message = message.text
        user.save()
    bot.send_message(message.chat.id, f"You said: {message.text}")
