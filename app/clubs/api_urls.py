from django.urls import path

from . import api

app_name = 'api_clubs'

urlpatterns = [
    path('', api.ClubListView.as_view(), name='list'),
    path('request/', api.ClubRequestView.as_view(), name='request'),
    path('<int:pk>/', api.ClubDetailView.as_view(), name='detail'),
    path('<int:pk>/membership/', api.MembershipRequestView.as_view(), name='membership'),
]
