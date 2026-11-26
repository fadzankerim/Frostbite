from django.urls import path

from . import api_hiker

app_name = 'api_selection'

urlpatterns = [
    path('', api_hiker.SelectionView.as_view(), name='list'),
    path('confirm/', api_hiker.SelectionConfirmView.as_view(), name='confirm'),
    path('<int:pk>/', api_hiker.SelectionItemView.as_view(), name='item'),
]
