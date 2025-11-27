from django.urls import path
from . import views

urlpatterns = [
    # AI 채팅을 시작하기 위해 누르는 버튼이 호출할 API
    path('start_session/', views.start_ai_session, name='start_ai_session'),
]