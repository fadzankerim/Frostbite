from django.urls import path

from . import api_system as api

app_name = 'api_system'

urlpatterns = [
    path('', api.DashboardView.as_view(), name='dashboard'),
    path('clubs/', api.ClubsView.as_view(), name='clubs'),
    path('clubs/<int:pk>/decide/', api.ClubDecideView.as_view(), name='club_decide'),
    path('users/', api.UsersView.as_view(), name='users'),
    path('users/<int:pk>/toggle/', api.UserToggleView.as_view(), name='user_toggle'),
    path('audit/', api.AuditView.as_view(), name='audit'),
]
