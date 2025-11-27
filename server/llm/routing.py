from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/llm/<str:session_id>/', consumers.AiChatConsumer.as_asgi()), 
]