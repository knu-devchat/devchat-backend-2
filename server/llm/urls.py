from django.urls import path
from . import views

app_name = 'llm'

urlpatterns = [
    # AI 세션 생성
    path('start_session/', views.start_ai_session, name='start_ai_session'),
    
    # AI 세션 목록 조회
    path('sessions/', views.get_ai_sessions, name='get_ai_sessions'),
]
