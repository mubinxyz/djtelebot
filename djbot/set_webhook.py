import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djbot.settings")
django.setup()

from djbot.bot.bot.bot import django_bot
django_bot.set_webhook()
