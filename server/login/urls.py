from django.urls import path
from . import views

app_name = "login"

# endpoint: ''
urlpatterns = [
    path('', views.home, name='home'),
    path('api/user/me/', views.current_user, name='current_user'),
]