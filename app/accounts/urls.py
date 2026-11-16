from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('registracija/', views.register, name='register'),
    path('prijava/', views.LoginView.as_view(), name='login'),
    path('odjava/', views.LogoutView.as_view(), name='logout'),
    path('profil/', views.profile, name='profile'),
    path('lozinka/', views.PasswordChangeView.as_view(), name='password_change'),
]
