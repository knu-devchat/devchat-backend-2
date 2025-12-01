import uuid
from django.db import models
from login.models import UserProfile

# Create your models here.
class ChatRoom(models.Model):
    room_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    admin = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='admin_chatrooms')
    participants = models.ManyToManyField(UserProfile, related_name='chatrooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.room_name} ({self.room_uuid})"
    
class UserChatRoomActivity(models.Model):
    """사용자의 채팅방별 활동 정보"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    
    # 사용자별 채팅방 설정
    is_muted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(blank=True, null=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # 알림 설정
    notifications_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'chatroom']
    
    def __str__(self):
        return f"{self.user.user.username} in {self.chatroom.room_name}"


class SecureData(models.Model):
    room = models.OneToOneField(ChatRoom, on_delete=models.CASCADE)
    encrypted_value = models.TextField()  # base64 암호문 저장
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"SecureData for {self.room.room_name}"

class Message(models.Model):
    id = models.AutoField(primary_key=True)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.user.username or 'Anonymous'}: {self.content[:20]}"