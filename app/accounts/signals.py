"""Evidencija prijava i odjava (politika 4.8)."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from audit.log import audit


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    audit(request, 'LOGIN_USPJEH', 'user', user.pk, user=user)


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user is not None:
        audit(request, 'ODJAVA', 'user', user.pk, user=user)
