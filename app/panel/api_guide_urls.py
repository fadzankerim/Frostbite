from django.urls import path

from . import api_guide as api

app_name = 'api_guide'

urlpatterns = [
    path('', api.GuideDashboardView.as_view(), name='dashboard'),
    path('tours/<int:pk>/', api.GuideTourView.as_view(), name='tour'),
    path('tours/<int:pk>/apply/', api.GuideApplyView.as_view(), name='apply'),
    path('tours/<int:pk>/close/', api.GuideCloseView.as_view(), name='close'),
    path('tours/<int:pk>/attendance/', api.GuideAttendanceView.as_view(), name='attendance'),
    path('tours/<int:pk>/report/', api.GuideReportView.as_view(), name='report'),
]
