import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djbot.settings")
django.setup()

from bot.bot import django_bot
django_bot.set_webhook()
