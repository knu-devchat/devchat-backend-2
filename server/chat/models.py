from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class ChatRoom(models.Model):
    room_id = models.AutoField(primary_key=True)
    room_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


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