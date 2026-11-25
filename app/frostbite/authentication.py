"""Autentikacija za JSON API (u zasebnom modulu jer je DRF učitava iz postavki pri importu)."""
from rest_framework.authentication import SessionAuthentication


class StrictSessionAuthentication(SessionAuthentication):
    """Sesija + CSRF za SVAKI zahtjev koji mijenja stanje (POST, PUT, PATCH, DELETE).

    Standardna DRF SessionAuthentication provjerava CSRF samo za prijavljene korisnike,
    a DRF view-ovi su inače izuzeti od Django CSRF middlewarea. Bez ove klase bi
    /api/auth/login/ i /api/auth/register/ bili otvoreni za login CSRF (napadač prijavi
    žrtvu u svoj nalog). Sigurne metode (GET, HEAD, OPTIONS) CSRF provjera preskače sama.
    """

    def authenticate(self, request):
        self.enforce_csrf(request)
        user = getattr(request._request, 'user', None)
        if not user or not user.is_active:
            return None
        return (user, None)
