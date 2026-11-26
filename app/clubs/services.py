"""F09 - zahtjev za registraciju društva. Podnosilac postaje admin društva tek kad sistemski admin
odobri društvo (admin_clubs() uzima samo odobrena društva)."""
from django.db import IntegrityError, transaction

from audit.log import audit

from .forms import ClubRequestForm
from .models import Club, ClubAdmin

MAX_PENDING_CLUB_REQUESTS = 1
NAME_TAKEN = 'Ovaj naziv nije dostupan.'


class ClubRequestError(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or {}


def has_pending_request(user):
    return Club.objects.filter(created_by=user, status=Club.Status.PENDING).count() >= MAX_PENDING_CLUB_REQUESTS


def request_club(request, data):
    """Kreira društvo na čekanju sa podnosiocem kao (budućim) adminom. Status, admin i datum postavlja
    server; polja van ClubRequestForm se ignorišu. Zauzet naziv daje generičku poruku."""
    if has_pending_request(request.user):
        raise ClubRequestError('Već imate zahtjev za registraciju društva koji čeka odobrenje.')
    form = ClubRequestForm(data)
    if not form.is_valid():
        raise ClubRequestError('Provjerite označena polja.', {k: [e['message'] for e in v]
                                                              for k, v in form.errors.get_json_data().items()})
    try:
        with transaction.atomic():
            club = form.save(commit=False)
            club.status = Club.Status.PENDING
            club.created_by = request.user
            club.save()
            ClubAdmin.objects.create(club=club, user=request.user)
    except IntegrityError:
        raise ClubRequestError(NAME_TAKEN, {'name': [NAME_TAKEN]})
    audit(request, 'DRUSTVO_ZAHTJEV', 'club', club.pk)
    return club
