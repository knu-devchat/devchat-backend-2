from django.urls import path
from . import views

app_name = "chat"

# api/chat/
urlpatterns = [
    path('rooms/', views.get_user_rooms, name='get_user_rooms'),
    path('chat-rooms/', views.create_chat_room, name='create_chat_room'), # 채팅방 생성
    path('chat-rooms/<uuid:room_uuid>/access-code/', views.generate_TOTP, name='generate_TOTP'), # TOTP 생성
    path('chat-rooms/<uuid:room_uuid>/join/', views.join_room, name='join_room'), # 채팅방 참가
    path('chat-rooms/<uuid:room_uuid>/enter/', views.enter_room, name='enter_room'), # 채팅방 조회
    path('chat-rooms/<str:room_name>/messages/', views.list_messages, name='list_messages'), # 메세지 조회
]