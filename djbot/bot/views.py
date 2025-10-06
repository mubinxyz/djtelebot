from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import telebot
from .bot import bot

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        json_str = request.body.decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return JsonResponse({'ok': True})
    return JsonResponse({'status': 'running'})
