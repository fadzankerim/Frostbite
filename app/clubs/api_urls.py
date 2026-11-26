from django.urls import path

from . import api

app_name = 'api_clubs'

urlpatterns = [
    path('', api.ClubListView.as_view(), name='list'),
    path('<int:pk>/', api.ClubDetailView.as_view(), name='detail'),
]
