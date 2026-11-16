from django.urls import path

from . import views

app_name = 'tours'

urlpatterns = [
    path('ture/', views.tour_list, name='list'),
    path('ture/<int:pk>/', views.tour_detail, name='detail'),
    path('ture/<int:pk>/prijava/', views.register_single, name='register'),
    path('ture/<int:pk>/ruta.gpx', views.tour_gpx, name='gpx'),
    path('odabir/', views.selection, name='selection'),
    path('odabir/dodaj/<int:pk>/', views.selection_add, name='selection_add'),
    path('odabir/ukloni/<int:pk>/', views.selection_remove, name='selection_remove'),
    path('odabir/potvrdi/', views.selection_confirm, name='selection_confirm'),
    path('moje-prijave/', views.my_registrations, name='my_registrations'),
    path('moje-prijave/<int:pk>/odjava/', views.cancel_registration, name='cancel'),
]
