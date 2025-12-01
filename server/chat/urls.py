from django.urls import path
from . import views

app_name = "chat"

# api/chat/
urlpatterns = [
    path('my-rooms/', views.get_my_rooms, name='get_my_rooms'), # 내 방 목록 (UUID 포함해서 반환)
    path('rooms/', views.create_chat_room, name='create_chat_room'), # 방 생성
    path('delete-room/', views.delete_room, name='delete_room'), # 방 삭제
    path('access-code/', views.generate_totp, name='generate_totp'), # 현재 선택된 방의 TOTP 생성
    path('join/', views.join_room, name='join_room'), # TOTP로 방 참가
    path('select-room/', views.select_room, name='select_room'), # 방 선택
    path('current-room/', views.get_current_room_info, name='get_current_room_info'), # 현재 선택된 방 정보 조회
    path('rooms/<str:room_uuid>/messages/', views.get_room_messages, name='get_room_messages'), # 메세지 조회
]