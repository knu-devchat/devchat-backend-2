from django.db import models
from chat.models import ChatRoom 

class AiChatSession(models.Model):
    """AI 채팅 세션 모델"""
    base_room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name='ai_sessions',
        help_text="AI 세션이 연결된 기본 채팅방"
    )
    
    session_id = models.CharField(
        max_length=100, 
        unique=True,
        help_text="AI 세션의 고유 식별자 (UUID)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="세션 활성화 여부"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="세션 생성 시간"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="세션 마지막 업데이트 시간"
    )
    
    class Meta:
        db_table = 'llm_ai_chat_session'
        verbose_name = 'AI Chat Session'
        verbose_name_plural = 'AI Chat Sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI Session for {self.base_room.room_name} ({self.session_id})"
    
    def deactivate(self):
        """세션 비활성화"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
