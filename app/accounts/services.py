"""Poslovna logika naloga, zajednička za HTML stranice i API."""
from django.db import IntegrityError, transaction

from audit.log import audit

from .models import User


def register_hiker(request, data):
    """F05 - registracija planinara iz validiranih podataka (RegistrationForm.cleaned_data).

    Ako email već postoji, ne radi se ništa, ali pozivalac dobija isti ishod kao za uspjeh
    (politika 4.4 - bez otkrivanja naloga). Vrijeme odgovora se izjednačava heširanjem lozinke.
    """
    try:
        with transaction.atomic():
            if User.objects.filter(email=data['email']).exists():
                raise IntegrityError
            user = User.objects.create_user(
                email=data['email'], password=data['password1'],
                first_name=data['first_name'], last_name=data['last_name'], phone=data['phone'],
            )
        audit(request, 'REGISTRACIJA', 'user', user.pk, user=user)
    except IntegrityError:
        User().set_password(data['password1'])        # izjednačavanje vremena odgovora
        audit(request, 'REGISTRACIJA_DUPLIKAT', 'user', details='email već postoji')
