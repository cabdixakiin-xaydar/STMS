# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def send_status_notification(sender, instance, **kwargs):
    if instance.user_type == 'GUIDE' and 'status' in kwargs.get('update_fields', []):
        subject = f"Your Guide Application Has Been {instance.get_status_display()}"
        context = {
            'guide': instance,
            'status': instance.get_status_display(),
        }
        
        message = render_to_string('accounts/emails/guide_status_notification.txt', context)
        html_message = render_to_string('accounts/emails/guide_status_notification.html', context)
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            html_message=html_message,
            fail_silently=True
        )