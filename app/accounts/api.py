"""Auth API za React frontend (/api/auth/).

Koristi iste forme i isti backend kao HTML stranice, pa važe ista pravila:
zaključavanje naloga, generička poruka greške, validatori lozinke, audit log,
nova sesija pri prijavi i bez otkrivanja postojećih naloga pri registraciji.

Tok u pregledaču:
  1. GET  /api/auth/csrf/      -> {"csrfToken": ...}; token se šalje u zaglavlju X-CSRFToken
  2. POST /api/auth/login/     -> podaci korisnika + NOVI csrfToken (Django ga mijenja pri prijavi)
  3. GET  /api/auth/me/        -> ko je prijavljen (ili authenticated: false)
  4. POST /api/auth/logout/    -> 204
"""
from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from frostbite.api import ApiView, form_errors

from .forms import LoginForm, RegistrationForm
from .permissions import is_club_admin, is_guide
from .services import register_hiker
from .views import REGISTER_DONE_MSG


def user_payload(user):
    """Podaci o prijavljenom korisniku za frontend. Uloge služe samo za prikaz menija -
    svaki API endpoint provjerava prava ponovo na serveru."""
    if not user.is_authenticated:
        return {'authenticated': False, 'user': None}
    return {
        'authenticated': True,
        'user': {
            'id': user.pk,
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'roles': {
                'systemAdmin': user.is_system_admin,
                'clubAdmin': is_club_admin(user),
                'guide': is_guide(user),
            },
        },
    }


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(ApiView):
    """Vraća CSRF token. Kolačić je HttpOnly, pa frontend token dobija samo ovdje."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class MeView(ApiView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(user_payload(request.user))


class LoginView(ApiView):
    """F06 - prijava emailom i lozinkom."""
    permission_classes = [AllowAny]

    def post(self, request):
        form = LoginForm(request._request, data={
            'username': request.data.get('email', ''),
            'password': request.data.get('password', ''),
        })
        if not form.is_valid():
            errors = form_errors(form)
            # neispravna prijava: samo generička poruka, bez detalja po poljima
            detail = (errors.get('__all__') or [next(iter(errors.values()))[0]])[0]
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
        login(request._request, form.get_user())     # nova sesija + novi CSRF token
        return Response({**user_payload(form.get_user()), 'csrfToken': get_token(request._request)})


class LogoutView(ApiView):
    """F06 - odjava. Sesija se briše na serveru."""
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(ApiView):
    """F05 - registracija planinara. Isti odgovor bez obzira da li email već postoji."""
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            return Response({'detail': 'Već ste prijavljeni.'}, status=status.HTTP_400_BAD_REQUEST)
        d = request.data
        form = RegistrationForm(data={
            'email': d.get('email', ''), 'first_name': d.get('firstName', ''),
            'last_name': d.get('lastName', ''), 'phone': d.get('phone', ''),
            'password1': d.get('password', ''), 'password2': d.get('passwordConfirm', ''),
        })
        if not form.is_valid():
            return Response({'errors': _api_field_names(form_errors(form))},
                            status=status.HTTP_400_BAD_REQUEST)
        register_hiker(request._request, form.cleaned_data)
        return Response({'detail': REGISTER_DONE_MSG}, status=status.HTTP_201_CREATED)


_FIELD_NAMES = {'first_name': 'firstName', 'last_name': 'lastName',
                'password1': 'password', 'password2': 'passwordConfirm'}


def _api_field_names(errors):
    return {_FIELD_NAMES.get(k, k): v for k, v in errors.items()}
