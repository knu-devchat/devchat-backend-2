from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# Create your models here.
class ChatRoom(models.Model):
    room_id = models.AutoField(primary_key=True)
    room_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chatrooms')
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_chatrooms')

    # 채팅방 타입
    ROOM_TYPES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('direct', 'Direct Message'),
        ('github_repo', 'GitHub Repository'),
    ]
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='public')
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.room_name


class SecureData(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    encrypted_value = models.TextField()  # base64 암호문 저장
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System'),
    ]

    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    created_at = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.username or 'Anonymous'}: {self.content[:20]}"