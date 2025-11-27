from django.db import models
from django.conf import settings


class Message(models.Model):
    MESSAGE_METHOD = (
        ('email', 'Email'),
        ('talkpage', 'Talkpage'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender')
    receiver = models.CharField(max_length=100)
    method = models.CharField(max_length=10, choices=MESSAGE_METHOD)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender} to {self.receiver} - {self.date.strftime("%d/%m/%Y %H:%M:%S")}'