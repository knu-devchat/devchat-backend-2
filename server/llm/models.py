from django.db import models
from chat.models import ChatRoom 

class AiChatSession(models.Model):
    base_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='ai_sessions')
    
    session_id = models.CharField(max_length=100, unique=True) 
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"AI Session for {self.base_room.room_name} ({self.session_id})"