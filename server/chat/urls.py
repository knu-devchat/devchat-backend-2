from django.urls import path
from . import views

app_name = "chat"

# api/chat/
urlpatterns = [
    path('chat-rooms/', views.create_chat_room, name='create_chat_room'),
    path('chat-rooms/<int:room_id>/access-code/', views.generate_TOTP, name='generate_TOTP'),
    path('chat-rooms/<int:room_id>/join/', views.join_room, name='join_room'),
    path('chat-rooms/<int:room_id>/enter/', views.enter_room, name='enter_room'),
    path('chat-rooms/<str:room_name>/messages/', views.list_messages, name='list_messages'),
]