from django.urls import path

from . import api

app_name = 'api_badges'

urlpatterns = [
    path('', api.BadgeCatalogView.as_view(), name='catalog'),
]
