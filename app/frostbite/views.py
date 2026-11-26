"""Odgovori na greške u JSON obliku (aplikacija nema HTML stranica).
Poruke su generičke: bez internih detalja, putanja i tragova izvršavanja."""
from django.http import JsonResponse


def _json(detail, status):
    resp = JsonResponse({'detail': detail}, status=status, json_dumps_params={'ensure_ascii': False})
    resp['Cache-Control'] = 'no-store'
    return resp


def bad_request(request, exception=None):
    return _json('Neispravan zahtjev.', 400)


def permission_denied(request, exception=None):
    return _json('Ova radnja nije dozvoljena.', 403)


def not_found(request, exception=None):
    return _json('Nije pronađeno.', 404)


def server_error(request):
    return _json('Greška na serveru.', 500)


def csrf_failure(request, reason=''):
    # Razlog se ne prikazuje korisniku (bez otkrivanja internih detalja).
    return _json('CSRF provjera nije uspjela. Osvježite stranicu i pokušajte ponovo.', 403)
