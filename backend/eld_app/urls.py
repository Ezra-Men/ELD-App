
from django.urls import path
from . import views

urlpatterns = [
    path('trips/', views.create_trip, name='create_trip'),
]