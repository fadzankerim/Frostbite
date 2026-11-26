"""/api/me/ - podaci i radnje prijavljenog korisnika."""
from django.urls import path

from clubs import api as clubs_api
from tours import api_hiker

from . import api

app_name = 'api_me'

urlpatterns = [
    path('profile/', api.ProfileView.as_view(), name='profile'),
    path('password/', api.PasswordChangeView.as_view(), name='password'),
    path('registrations/', api_hiker.MyRegistrationsView.as_view(), name='registrations'),
    path('registrations/<int:pk>/cancel/', api_hiker.CancelRegistrationView.as_view(), name='cancel'),
    path('memberships/', clubs_api.MyMembershipsView.as_view(), name='memberships'),
]
