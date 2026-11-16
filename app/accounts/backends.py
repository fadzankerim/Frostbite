"""Prijava emailom i lozinkom uz zaključavanje naloga (politika 4.6).

- Nakon LOCKOUT_MAX_ATTEMPTS uzastopnih neuspjeha nalog je zaključan LOCKOUT_MINUTES minuta.
- Zaključavanje je vezano za nalog, ne za IP adresu (svi korisnici VPN-a dijele istu IP adresu).
- Za nepostojeći, zaključan ili blokiran nalog izvršava se heširanje lozinke, tako da se po
  vremenu odgovora ne može zaključiti da li nalog postoji.
- Pozivalac uvijek dobija istu generičku poruku (vidi accounts.forms.LoginForm).
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import transaction
from django.utils import timezone

from audit.log import audit


def _burn_hash(password):
    get_user_model()().set_password(password)


class LockoutEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = (username or kwargs.get(User.USERNAME_FIELD) or '').strip().lower()
        if not email or password is None:
            return None

        user = User.objects.filter(email=email).first()
        if user is None:
            _burn_hash(password)
            audit(request, 'LOGIN_NEUSPJEH', 'user', details='nepostojeći nalog')
            return None

        now = timezone.now()
        if user.is_locked(now):
            _burn_hash(password)
            audit(request, 'LOGIN_ZAKLJUCAN', 'user', user.pk, user=user)
            return None

        if not self.user_can_authenticate(user):       # blokiran nalog
            _burn_hash(password)
            audit(request, 'LOGIN_BLOKIRAN', 'user', user.pk, user=user)
            return None

        if user.check_password(password):
            if user.failed_login_count or user.locked_until:
                User.objects.filter(pk=user.pk).update(failed_login_count=0, locked_until=None)
                user.failed_login_count, user.locked_until = 0, None
            return user

        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=user.pk)
            locked.failed_login_count += 1
            if locked.failed_login_count >= settings.LOCKOUT_MAX_ATTEMPTS:
                locked.failed_login_count = 0
                locked.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
                action = 'NALOG_ZAKLJUCAN'
            else:
                action = 'LOGIN_NEUSPJEH'
            locked.save(update_fields=['failed_login_count', 'locked_until'])
        audit(request, action, 'user', user.pk, user=user)
        return None
