# bot/views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .bot.bot import django_bot

@csrf_exempt
def webhook(request):
    if request.method == "POST":
        json_str = request.body.decode("utf-8")
        django_bot.process_update(json_str)
        return JsonResponse({"ok": True})
    return JsonResponse({"status": "running"})
