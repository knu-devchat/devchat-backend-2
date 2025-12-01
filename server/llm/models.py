from django.db import models
from chat.models import ChatRoom 
from login.models import UserProfile

class AiChatMessage(models.Model):
    """AI 채팅 전용 메시지 모델 - 일반 채팅과 완전 분리"""
    session = models.ForeignKey(
        'AiChatSession',
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="AI 세션별 메시지 그룹화"
    )
    
    sender = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        help_text="메시지 발신자 (사용자 또는 AI)"
    )
    
    content = models.TextField(help_text="메시지 내용")
    
    is_ai_message = models.BooleanField(
        default=False,
        help_text="AI가 생성한 메시지인지 여부"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="메시지 생성 시간"
    )
    
    class Meta:
        db_table = 'llm_ai_chat_message'
        verbose_name = 'AI Chat Message'
        verbose_name_plural = 'AI Chat Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        sender_type = "AI" if self.is_ai_message else "User"
        return f"[{sender_type}] {self.sender.user.username}: {self.content[:30]}..."

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
