from django.db import models

class TelegramUser(models.Model):
    chat_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.username or str(self.chat_id)
