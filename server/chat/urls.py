from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path('create-chat-room/', views.create_chat_room, name='create_chat_room'),
    path('rooms/<int:room_id>/generate-totp/', views.generate_TOTP, name='generate_TOTP'),
    path('rooms/<str:room_name>/messages/', views.list_messages, name='list_messages'),
]