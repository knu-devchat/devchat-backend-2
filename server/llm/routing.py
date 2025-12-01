from django.urls import path
from . import consumers

# WebSocket URL 패턴
websocket_urlpatterns = [
    path('ws/llm/<str:session_id>/', consumers.AiChatConsumer.as_asgi()),
]
