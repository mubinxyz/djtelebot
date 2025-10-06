import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djbot.settings')
django.setup()

from django.conf import settings
import telebot

bot = telebot.TeleBot(settings.BOT_TOKEN)
bot.remove_webhook()
bot.set_webhook(url=settings.WEBHOOK_URL)

print("✅ Webhook set successfully!")
