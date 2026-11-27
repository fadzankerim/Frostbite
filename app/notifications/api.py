"""API obavještenja.

- GET/PUT /api/me/notifications/: postavke prijavljenog korisnika (samo kategorije njegovih uloga).
- POST /api/notifications/unsubscribe/ {"token"}: odjava sa stranice /obavjestenja/odjava (React).
- POST /api/notifications/unsubscribe/<token>/: odjava jednim klikom iz email klijenta (RFC 8058).
  Klijent šalje obični form POST bez CSRF tokena, pa je ovaj view izuzet od CSRF provjere; ovlaštenje
  daje potpisan token (korisnik + kategorija, važi 180 dana). Token ne omogućava prijavu ni ništa
  drugo osim isključivanja te jedne nesigurnosne kategorije.
"""
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from audit.log import audit
from frostbite.api import ApiView

from . import services
from .categories import BY_CODE, MODE_LABELS, OFF, categories_for

INVALID = 'Link za odjavu nije ispravan ili je istekao. Obavještenja možete podesiti u profilu.'


def _payload(user):
    return {'results': [{
        'code': c.code, 'label': c.label, 'description': c.description, 'security': c.security,
        'mode': services.mode_for(user, c.code),
        'modes': [{'code': m, 'label': MODE_LABELS[m]} for m in c.modes],
    } for c in categories_for(user)]}


class PreferencesView(ApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_payload(request.user))

    def put(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        allowed = {c.code: c for c in categories_for(request.user)}
        errors = {}
        for code, mode in data.items():
            if code not in allowed or not isinstance(mode, str) or mode not in allowed[code].modes:
                errors[code] = ['Nedozvoljena vrijednost.']
        if errors or not data:
            return Response({'detail': 'Postavke nisu ispravne.', 'errors': errors}, status=400)
        for code, mode in data.items():
            services.set_mode(request.user, code, mode)
        audit(request._request, 'OBAVJESTENJA_POSTAVKE', 'user', request.user.pk, details=','.join(sorted(data))[:200])
        return Response({**_payload(request.user), 'detail': 'Postavke obavještenja su sačuvane.'})


def _unsubscribe(token, request):
    parsed = services.read_unsubscribe_token(token) if isinstance(token, str) and len(token) < 500 else None
    if parsed is None:
        return None
    user = User.objects.filter(pk=parsed[0]).first()
    if user is None:
        return None
    services.set_mode(user, parsed[1], OFF)
    audit(request, 'OBAVJESTENJA_ODJAVA', 'user', user.pk, user=user, details=f'kategorija={parsed[1]}')
    return BY_CODE[parsed[1]]


class UnsubscribeView(ApiView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token') if isinstance(request.data, dict) else None
        cat = _unsubscribe(token, request._request)
        if cat is None:
            return Response({'detail': INVALID}, status=400)
        return Response({'detail': f'Više nećete dobijati obavještenja: {cat.label.lower()}.', 'category': cat.label})


@csrf_exempt
@require_POST
def one_click_unsubscribe(request, token):
    cat = _unsubscribe(token, request)
    if cat is None:
        return HttpResponseBadRequest('Neispravan link.', content_type='text/plain; charset=utf-8')
    return HttpResponse('Odjavljeni ste.', content_type='text/plain; charset=utf-8')
