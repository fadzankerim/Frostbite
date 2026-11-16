from django.urls import path

from . import views

app_name = 'clubs'

urlpatterns = [
    path('drustva/', views.club_list, name='list'),
    path('drustva/novo/', views.club_register, name='register'),
    path('drustva/<int:pk>/', views.club_detail, name='detail'),
    path('drustva/<int:pk>/uclanjenje/', views.membership_request, name='membership_request'),
    path('moja-clanstva/', views.my_memberships, name='my_memberships'),
]
