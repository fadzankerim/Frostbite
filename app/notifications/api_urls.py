from django.urls import path

from . import api

app_name = 'api_notifications'

urlpatterns = [
    path('unsubscribe/', api.UnsubscribeView.as_view(), name='unsubscribe'),
    path('unsubscribe/<str:token>/', api.one_click_unsubscribe, name='one_click'),
]
