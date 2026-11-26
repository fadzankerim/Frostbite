"""Zajednička pravila za JSON API (/api/).

Autentikacija je ista kao za HTML stranice: Django sesija u HttpOnly kolačiću.
Nema JWT-a ni tokena u pregledaču, pa XSS ne može ukrasti sesiju, a blokiranje
naloga i promjena lozinke odmah poništavaju postojeće sesije.
CSRF pravila su u frostbite.authentication.
"""
from django.utils.cache import add_never_cache_headers
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView


class ApiView(APIView):
    """Bazni view: odgovori API-ja se nikad ne keširaju (sadrže lične podatke i CSRF token)."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        add_never_cache_headers(response)
        return response


def form_errors(form):
    """Greške Django forme u JSON obliku: {"polje": ["poruka", ...], "__all__": [...]}."""
    return {field: [e['message'] for e in errs] for field, errs in form.errors.get_json_data().items()}


class IsHiker(BasePermission):
    """Funkcionalnosti planinara (F09-F14): prijavljen korisnik koji NIJE sistemski admin.
    Isto pravilo kao accounts.permissions.hiker_required za HTML stranice."""
    message = 'Ova radnja nije dozvoljena.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and not u.is_system_admin)
