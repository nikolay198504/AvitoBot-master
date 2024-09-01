from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('logs/', views.log_view, name='log_view'),
]
