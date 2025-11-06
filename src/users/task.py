# In src/core/tasks.py

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User
from .utils import AccountActivationTokenGenerator  # Import custom generator


@shared_task
def send_activation_email(user_email):
    user = User.objects.get(email=user_email)
    token_generator = AccountActivationTokenGenerator()  # Custom generator for 24-hour timeout
    uid = urlsafe_base64_encode(force_bytes(user.pk))  # Base64 encode user ID
    token = token_generator.make_token(user)  # Generate secure token
    activation_link = f"{settings.SITE_URL}{reverse('set_password_activate', kwargs={'uidb64': uid, 'token': token})}"  # Full URL

    subject = 'Activate Your Account'
    message = f'Hi {user.first_name},\n\nClick the link to set your password (valid 24 hours):\n{activation_link}\n\nIgnore if not requested.'
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])  # Send email


@shared_task
def cleanup_expired_users():
    # expiration_time = timezone.now() - timedelta(hours=24)  # 24 hours ago
    expiration_time = timezone.now() - timedelta(hours=settings.USER_EXPIRATION_HOURS)  # 24 hours ago
    # expiration_time = timezone.now() - timedelta(seconds=settings.USER_EXPIRATION_SECONDS)
    expired_users = User.objects.filter(
        is_active=False,  # Unactivated
        password__startswith=UNUSABLE_PASSWORD_PREFIX,  # No password set (raw password is unusable before set_password)
        date_joined__lt=expiration_time  # Older than 24 hours
    )

    # Print users for testing
    for u in expired_users:
        subject = 'Activation Link Expired'
        message = (
            f"Hi {u.first_name},\n\n"
            "Your activation link has expired. Please signup again to create a new account.\n\n"
            "Ignore this message if you already activated your account."
        )
        send_mail(subject, message, settings.EMAIL_HOST_USER, [u.email])

        print(f"[CLEANUP] Expired user notified: {u.email}, joined at {u.date_joined}")

    count = expired_users.count()
    expired_users.delete()  # Bulk delete
    print(f"[CLEANUP] Total expired users deleted: {count}")

    return f"Deleted {count} expired unactivated users."  # For logging
