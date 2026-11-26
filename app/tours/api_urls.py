from django.urls import path

from . import api, api_hiker

app_name = 'api_tours'

urlpatterns = [
    path('', api.TourListView.as_view(), name='list'),
    path('filters/', api.TourFiltersView.as_view(), name='filters'),
    path('stats/', api.TourStatsView.as_view(), name='stats'),
    path('<int:pk>/', api.TourDetailView.as_view(), name='detail'),
    path('<int:pk>/register/', api_hiker.TourRegisterView.as_view(), name='register'),
]
