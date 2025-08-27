from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Bug

@receiver(post_save, sender=Bug)
def send_bug_report_email(sender, instance, created, **kwargs):
    if created:
        subject = f"New Bug Report: {instance.title}"
        message = f"A new bug has been reported by {instance.user} (ID: {instance.user.id}):\n\nTitle: {instance.title}\nDescription: {instance.description}\nType: {instance.bug_type}\nStatus: {instance.status}\nCreated at: {instance.created_at}"
        admins = getattr(settings, 'ADMINS', [])
        if admins:
            admin_emails = [admin[1] for admin in admins]
            send_mail(
                subject,
                message,
                settings.SERVER_EMAIL,
                admin_emails,
                fail_silently=False,
            )
