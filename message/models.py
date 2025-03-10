from django.db import models
from django.conf import settings
from .services.message_service import MessageService


class Message(models.Model):
    MESSAGE_METHOD = (
        ('email', 'Email'),
        ('talkpage', 'Talkpage'),
    )
    message = models.CharField(max_length=2000)
    subject = models.CharField(max_length=200)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender')
    receiver = models.CharField(max_length=100)
    method = models.CharField(max_length=10, choices=MESSAGE_METHOD)
    status = models.CharField(max_length=10, default='pending')
    date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.status = 'sending'
            self.save(update_fields=['status'])
            MessageService.send_message(self)

    def __str__(self):
        return f'{self.sender} to {self.receiver} - {self.date.strftime("%d/%m/%Y %H:%M:%S")}'