# bot/models.py
from django.db import models
from django.contrib.auth.models import User

class UserCustom(models.Model):
    """
    Store arbitrary custom settings for a user.
    Can store any key-value pairs like chart settings, sl/tp, figsize, colors, etc.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customs")
    data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Customs for {self.user.username}"


class UserAlert(models.Model):
    """
    Store MA alert configurations for a user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alerts")
    alert_id = models.PositiveIntegerField()
    symbol = models.CharField(max_length=20)
    timeframe = models.CharField(max_length=10)
    ma_fast = models.PositiveIntegerField()
    ma_slow = models.PositiveIntegerField()
    ma_type = models.CharField(max_length=10, choices=[("sma", "SMA"), ("ema", "EMA")])

    class Meta:
        unique_together = ("user", "alert_id")  # ensure each alert_id is unique per user

    def __str__(self):
        return f"Alert {self.alert_id} for {self.user.username} ({self.symbol})"
